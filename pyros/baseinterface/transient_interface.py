from __future__ import absolute_import
from __future__ import print_function

import copy
import logging
from contextlib import contextmanager

import six
import sys
import threading
import collections
import re


# In case we launch this as a module, we want to be able to resolve relative import and run doctests
if __package__ is None:
    import sys
    from os import path
    sys.path.append(path.dirname(path.abspath(__file__)))
    from excess import EntityManager, System, SystemManager
else:
    from .excess import EntityManager, System, SystemManager


# module wide to be pickleable
DiffTuple = collections.namedtuple("DiffTuple", " added removed ")


def cap_match_string(match):
    """
    Attach beginning of line and end of line characters to the given string.
    Ensures that raw topics like /test do not match other topics containing
    the same string (e.g. /items/test would result in a regex match at char 7)
    regex goes through each position in the string to find matches - this
    forces it to consider only the first position
    :param match: a regex
    :return:
    """
    return '^' + match + '$'


def find_first_regex_match(key, regex_candidates):
    """
    find the first regex that match with the key
    :param key: a key to try to match against multiple regex
    :param match_candidates: a list of regexes to check if they match the key
    :return: the first candidate found
    >>> find_first_regex_match("/long/name",["something_else"])
    >>> find_first_regex_match("/long/name",["something_else", "/long/.*"])
    '/long/.*'
    """
    for cand in regex_candidates:
        try:
            pattern = re.compile(cap_match_string(cand))
            if pattern.match(key):
                return cand
        except:
            logging.warn('[ros_interface] Ignoring invalid regex string "{0!s}"!'.format(cand))

    return None


def regex_match_sublist(regex, match_candidates):
    """
    Filter the match_candidates list to return only the candidate that match the regex
    :param regex: a regex used to filter the list of candidates
    :param match_candidates: the list of candidates
    :return: the filtered list of only the candidates that match the regex
    >>> regex_match_sublist("/long/.*",["something_else"])
    []
    >>> regex_match_sublist("/long/.*",["something_else", "/long/name"])
    ['/long/name']
    """
    matches = []
    try:
        pattern = re.compile(cap_match_string(regex))
        matches = [cand for cand in match_candidates if pattern.match(cand)]
    except:
        logging.warn('[ros_interface] Ignoring invalid regex string "{0!s}"!'.format(regex))
    return matches


def regexes_match_sublist(regexes, match_candidates):
    """
    Filter the match_candidates list to return only the candidate that match the regex
    :param regexes: a list of regex used to filter the list of candidates
    :param match_candidates: the list of candidates
    :return: the filtered list of only the candidates that match the regexes
    >>> regexes_match_sublist(["/long/.*"],["something_else"])
    []
    >>> regexes_match_sublist(["/long/.*"],["something_else", "/long/name"])
    ['/long/name']
    >>> regexes_match_sublist(["/long/.*",".*_we_want"],["something_else", "/long/name", "what_we_want"])
    ['/long/name', 'what_we_want']
    """

    #TODO : we should be able to improve this with iterators.
    return [match for sublist in [regex_match_sublist(rgx, match_candidates) for rgx in regexes] for match in sublist]

#
#
# WIP : TransientInterface to use as a delegate instead of base interface
#

# TODO : Defining components to enforce strong typing where possible
# Goal : avoid deep unexpected behavior

# simplistic bwcompat enum implementation
def enum(**enums):
    return type('Enum', (), enums)

Name = str  #(unicode ?)
Desc = unicode
Changed = enum(UNKNOWN=0, APPEARED=1, GONE=2)


# Defining Systems

class TypeResolver(System):

    def __init__(self):
        super(TypeResolver, self).__init__()

    def configure(self, entity_mgr, type_resolver):
        # TODO : make sure this is referenced and can be dynamically updated
        self.type_resolver = type_resolver

    def component_spec(self):
        """
        :return: tuple of the component names that are required, and created
        """
        return {"name"}, {"type"}

    def loop(self, entity_mgr, time_delta):

        # only for testing/reporting purpose on what was changed
        added = []
        removed = []

        entities_toresolve = entity_mgr.filter_by_component(["name"], filter=lambda e: "type" not in e)

        for e in entities_toresolve:
            try:
                e["type"] = self.type_resolver(e.get("name"))
            except Exception as exc:
                logging.warn("[{name}] Cannot resolve type of {desc} {transient} : {exc}".format(
                    name=__name__, desc=e.get("desc"), transient=e.get("name"), exc=exc)
                )
                exc_info = sys.exc_info()
                six.reraise(exc_info[0], exc_info[1], exc_info[2])

System.register(TypeResolver)


class InterfaceAdder(System):

    def __init__(self):
        super(InterfaceAdder, self).__init__()

    def component_spec(self):
        """
        :return: tuple of the set of component names that are manipulated by this system. input -> output
        """
        return {"name", "type", "desc", "tif_maker"}, {"name", "type", "desc", "tif_maker", "tif"}

    def loop(self, entity_mgr, time_delta):

        entities_toadd = entity_mgr.filter_by_component(["name", "type", "desc", "tif_maker"], filter=lambda e: "tif" not in e)

        for ent in entities_toadd:
            try:
                ent["tif"] = ent.get("tif_maker")(ent.get("name"), ent.get("type"))
                logging.info(
                    "[{name}] Interfacing with {desc} {transient}".format(
                        name=__name__, desc=ent.get("desc"), transient=ent.get("name"))
                )
            except Exception as exc:
                logging.warn("[{name}] Cannot interface with {desc} {transient} : {exc}".format(
                    name=__name__, desc=ent.get("desc"), transient=ent.get("name"), exc=exc)
                )
                exc_info = sys.exc_info()
                six.reraise(exc_info[0], exc_info[1], exc_info[2])

System.register(InterfaceAdder)


class InterfaceRemover(System):

    def __init__(self):
        super(InterfaceRemover, self).__init__()

    def component_spec(self):
        """
        :return: tuple of the set of component names that are manipulated by this system. input -> output

        Note this is an entity sink since we do not add any component, but instead we remove the entity
        """
        return {"name", "type", "desc", "tif_cleaner", "tif"}, set()

    def loop(self, entity_mgr, time_delta):

        # TODO : move into another system ? or collapse into same component (to keep diff localized) ?
        entities_todel = entity_mgr.filter_by_component(["name", "desc", "tif_cleaner", "tif"])

        for e in entities_todel:
            # because we might have modified resolved_dict after building the list to loop on
            logging.info("[{name}] Removing {desc} {transient}".format(name=__name__, desc=e.get("desc"),
                                                                       transient=e.get("name")))
            e.get("tif_cleaner")(e.get("tif"))  # calling the cleanup function in case we need to do something
            entity_mgr.destroy(e)

System.register(InterfaceRemover)


class AddFilter(System):
    """
    this system determines which change of the system should actually trigger transient interface creation/deletion
    ChangeFilter -> InterfaceAdder|InterfaceRemover
    """

    def __init__(self):
        """
        Initializes this System
        """
        super(AddFilter, self).__init__()

    def component_spec(self):
        """
        :return: tuple of the set of component names that are manipulated by this system. input -> output
        """
        return {"name", "changed", "desc"}, {"name", "desc", "tif_maker"}

    def configure(self, entity_mgr, regex_args, tif_maker):
        """
        Configure this System
        :param entity_mgr: the entity manager we work with
        :param regex_args: the regex arguments
        :param tif_maker: the transient interface builder function
        :param tif_cleaner: the transient interface cleaner function
        :return: None
        """
        # TODO : make sure this is referenced and can be dynamically updated
        self.regex_args = regex_args
        self.tif_maker = tif_maker

    def loop(self, entity_mgr, time_delta):
        """
        Add constructor/destructor functions to be called for each added/gone entity
        :param entity_mgr: the entity manager we work with
        :param time_delta: the time_delta since the last update
        :return: None
        >>> entities= EntityManager()
        >>> entities.create(name="test_added_entity", changed=Changed.APPEARED, desc="filterable_entity")
        {'changed': 1, 'name': 'test_added_entity', 'desc': 'filterable_entity'}
        >>> s = AddFilter()
        >>> s.configure(entities, regex_args=["test_.*"], tif_maker=(lambda n, t: print("maker({0},{1}".format(n,t))))
        >>> s.loop(entities, 1)
        >>> entities.filter_by_component(["tif_maker"]) # doctest: +ELLIPSIS
        [{'tif_maker': <function <lambda> at 0x...>, 'name': 'test_added_entity', 'desc': 'filterable_entity'}]
        """
        transients_changed = entity_mgr.filter_by_component(["name", "changed", "desc"])

        transients_appeared = [t for t in transients_changed if t.get("changed") == Changed.APPEARED]
        to_add = [t for t in transients_appeared if t.get("name") in regexes_match_sublist(self.regex_args, [t.get("name") for t in transients_appeared])]

        # TODO : simplify : have tif created early (but what about type resolver ?)
        for t in to_add:
            self.filtered_toadd(t)

    # These are useful to test this system effects on the entities
    def filtered_toadd(self, t):
        t["tif_maker"] = self.tif_maker
        # we consume the changed indicator here to avoid confusion later on...
        t.pop("changed")


System.register(AddFilter)


class RemoveFilter(System):
    """
    this system determines which change of the system should actually trigger transient interface creation/deletion
    ChangeFilter -> InterfaceAdder|InterfaceRemover
    """

    def __init__(self):
        """
        Initializes this System
        """
        super(RemoveFilter, self).__init__()

    def component_spec(self):
        """
        :return: tuple of the set of component names that are manipulated by this system. input -> output
        """
        return {"name", "changed", "desc"}, {"name", "desc", "tif_cleaner"}

    def configure(self, entity_mgr, regex_args, tif_cleaner):
        """
        Configure this System
        :param entity_mgr: the entity manager we work with
        :param regex_args: the regex arguments
        :param tif_maker: the transient interface builder function
        :param tif_cleaner: the transient interface cleaner function
        :return: None
        """
        # TODO : make sure this is referenced and can be dynamically updated
        self.regex_args = regex_args
        self.tif_cleaner = tif_cleaner

    def loop(self, entity_mgr, time_delta):
        """
        Add constructor/destructor functions to be called for each added/gone entity
        :param entity_mgr: the entity manager we work with
        :param time_delta: the time_delta since the last update
        :return: None
        >>> entities= EntityManager()
        >>> entities.create(name="test_gone_entity", changed=Changed.GONE, desc="filterable_entity")
        {'changed': 2, 'name': 'test_gone_entity', 'desc': 'filterable_entity'}
        >>> s = RemoveFilter()
        >>> s.configure(entities, regex_args=["test_.*"], tif_cleaner=(lambda n, t: print("cleaner({0},{1}".format(n,t))))
        >>> s.loop(entities, 1)
        >>> entities.filter_by_component(["tif_cleaner"]) # doctest: +ELLIPSIS
        [{'tif_cleaner': <function <lambda> at 0x...>, 'name': 'test_gone_entity', 'desc': 'filterable_entity'}]
        """
        transients_gone = entity_mgr.filter_by_component(["name", "changed", "desc"], lambda t: t.get("changed") == Changed.GONE)

        lost_matches = [n for n in entity_mgr.filter_by_component("name") if find_first_regex_match(n.get("name"), self.regex_args) is None]
        to_remove = transients_gone + lost_matches  # we stop interfacing with lost transient OR lost matches

        for t in to_remove:
            self.filtered_toremove(t)

    # TODO : simplify : have tif_cleaner stored early ( in case a transient is dropped without warning, because of error, etc.)
    # These are useful to test this system effects on the entities
    def filtered_toremove(self, t):
        t["tif_cleaner"] = self.tif_cleaner
        # we consume the changed indicator here to avoid confusion later on...
        t.pop("changed")

System.register(RemoveFilter)


class AppearedDetector(System):
    """
    This systems detect if any change happened on the system
    ChangeDetector -> ChangeFilter -> InterfaceUpdater
    """

    def __init__(self):
        super(AppearedDetector, self).__init__()

    def component_spec(self):
        """
        :return: tuple of the set of component names that are manipulated by this system. input -> output

        Note this is an entity source since we do not rely on any existing component, but instead we create the entity
        """

        return set(), {"changed"}

    def configure(self, entity_mgr, get_transient_list, transient_desc):
        # TODO : make sure this is referenced and can be dynamically updated
        self.get_transient_list = get_transient_list
        self.transient_desc = transient_desc

    def loop(self, entity_mgr, time_delta):
        transients_known = entity_mgr.filter_by_component("name")

        transient_detected = self.get_transient_list()

        for t in transient_detected:
            if not t is transients_known:
                self.detected_appeared(entity_mgr, t)

        # TODO : think more about the case of a transient that is detected both appeared and gone...

    # These are useful to test this system effects on the entities
    # TODO : if available we already want the type here.
    # If not the resolver will deal with it later...
    def detected_appeared(self, entity_mgr, tst_name):
        return entity_mgr.create(name=tst_name, changed=Changed.APPEARED, desc=self.transient_desc)

System.register(AppearedDetector)


class GoneDetector(System):
    """
    This systems detect if any change happened on the system
    ChangeDetector -> ChangeFilter -> InterfaceUpdater
    """

    def __init__(self):
        super(GoneDetector, self).__init__()

    def component_spec(self):
        """
        :return: tuple of the set of component names that are manipulated by this system. input -> output

        Note this is an entity source since we do not rely on any existing component, but instead we create the entity
        """

        return {"name"}, {"changed"}

    def configure(self, entity_mgr, get_transient_list, transient_desc):
        # TODO : make sure this is referenced and can be dynamically updated
        self.get_transient_list = get_transient_list
        self.transient_desc = transient_desc

    def loop(self, entity_mgr, time_delta):
        transients_known = entity_mgr.filter_by_component("name")

        transient_detected = self.get_transient_list()

        for t in transients_known:
            if not t.get("name") in transient_detected:
                self.detected_gone(entity_mgr, t)

        # TODO : think more about the case of a transient that is detected both appeared and gone

    # These are useful to test this system effects on the entities
    def detected_gone(self, entity_mgr, tst):
        tst["changed"] = Changed.GONE
        #TODO : find a solution for cleaning up...
        return tst.get("name")

System.register(GoneDetector)

# Design Entity Component System design for interface loop.
# cf https://pypi.python.org/pypi/esper (py3 + py2 in fork)
# Or EXperimental Component Entity System Simplified
# Entities are transients (ex : for ROS : pubs, subs, svcs, params, and more can be added),
# Systems store logic about when/how a transient should be represented in the interface.
# GOALS : clarity, testability and flexibility
class TransientInterface(object):

    """
    TransientInterface.
    Assumption : we only deal with absolute names here. The users should resolve them
    """

    def get_transient_list(self):  # function returning all transients available on the system
        return [t.get("name") for t in self.transients_if.filter_by_component("name")]

    def __init__(self, transient_desc=None, get_transient_list=None, transient_type_resolver=None, tif_maker=None, tif_cleaner=None):
        """
        Initializes the interface instance, to expose transients
        :param transient_desc: transients descriptive string, ie "service" or "publisher"
        :param tif_maker: function that adds an interface for a transient
        :param tif_cleaner: function that removes an interface for a transient
        """

        #: Current interfaced transients, i.e. those which are currently exposed.
        #: Also used for comparison with previously detected transients and build a diff
        #:
        #: This stays always in sync with the system (via interface update call)
        #: but the transient interface itself is managed in the Entity, inside a Component
        self.transients_if = EntityManager()
        self.transients_if_lock = threading.Lock()  # writer lock (because we have subscribers on another thread)
        # TODO: find a way to make interface development easier by allowing developer to compare and worry only about local state representation versus interface
        # NOT about how to synchronize remote state with local state...

        #: Last requested transients to be exposed, received from a request.
        self.transients_args = set()

        #: How we can describe our transients
        self.transient_desc = transient_desc or "transient"

        #: can resolve the type of a transient if needed
        self.transient_type_resolver = transient_type_resolver

        #: To be able to create and destroy transients
        self.tif_maker = tif_maker or (lambda name, type, args, kwargs: (name, type, args, kwargs))
        self.tif_cleaner = tif_cleaner or (lambda name: () )

        # Adding Systems one by one

        self.resolver = TypeResolver()
        self.adder = InterfaceAdder()
        self.remover = InterfaceRemover()
        self.appeared_detector = AppearedDetector()
        self.gone_detector = GoneDetector()
        self.add_filter = AddFilter()
        self.remove_filter = RemoveFilter()

        # configuring all systems, ready to go
        self.resolver.configure(self.transients_if, self.transient_type_resolver)
        self.adder.configure(self.transients_if)
        self.remover.configure(self.transients_if)
        self.appeared_detector.configure(self.transients_if, get_transient_list, transient_desc)
        self.gone_detector.configure(self.transients_if, get_transient_list, transient_desc)
        self.add_filter.configure(self.transients_if, self.transients_args, tif_maker)
        self.remove_filter.configure(self.transients_if, self.transients_args, tif_cleaner)

    def expose_transients_regex(self, regexes, *class_build_args, **class_build_kwargs):
        """
        Exposes a list of transients regexes. resolved transients not matching the regexes will be removed.
        expose_transients_regex -> transients_change_detect -> transients_change_diff -> update_transients
        :param regexes: the list of regex to filter the transient to add.
               Note: regexes = [] remove all registered regexes.
        :return: a DiffTuple containing the list of transient interfaces (tif) added and removed
        """
        # Important : no effect if names is empty list, only return empty DiffTuple (null element, functional style).

        regexes = regexes or []  # forcing empty list (tofollow normal process) if passed None

        add_names = []
        rem_names = []
        # look through the new service names received by reconfigure, and add
        # those services which are not in the existing service args
        for tst_regex in [r for r in regexes if not r in self.transients_args]:
            self.transients_args.add(tst_regex)
            logging.info('[{name}] Exposing {desc} regex : {regex}'.format(
                    name=__name__, desc=self.transient_desc, regex=tst_regex
            ))
            # TODO : check here for bugs & add test : what if we add multiple regexes ? wont we miss some add_names ?

        # look through the current service args and delete those values which
        # will not be valid when the args are replaced with the new ones. run on
        # a copy so that we will remove from the original without crashing
        for tst_regex in [r for r in self.transients_args if not r in regexes]:
            logging.info('[{name}] Withholding {desc} regex : {regex}'.format(
                name=__name__, desc=self.transient_desc, regex=tst_regex
            ))
            self.transients_args.remove(tst_regex)

        # forcing immediate update
        return self.update()

## BW COMPAT BEGIN

    def update_transients(self):
        before = {e.get("name") for e in self.transients_if.filter_by_component(self.adder.component_spec()[1])}
        self.adder.loop(self.transients_if, 0)
        added = {e.get("name") for e in self.transients_if.filter_by_component(self.adder.component_spec()[1])} - before
        before = {e.get("name") for e in self.transients_if.filter_by_component(self.remover.component_spec()[1])}
        self.remover.loop(self.transients_if, 0)
        # CAREFUL : Special case for sinks
        removed = {ename for ename in before - set(self.transients_if.index_by_component(self.remover.component_spec()[1]))}
        return DiffTuple(added=added, removed=removed)

    def resolve_transients(self):
        before = {e.get("name") for e in self.transients_if.filter_by_component(self.resolver.component_spec()[1])}
        self.resolver.loop(self.transients_if, 0)
        resolved = {e.get("name") for e in self.transients_if.filter_by_component(self.resolver.component_spec()[1])} - before
        return resolved

    def transients_change_detect(self):
        before = {e.get("name") for e in self.transients_if.filter_by_component(self.appeared_detector.component_spec()[1])}
        self.appeared_detector.loop(self.transients_if, 0)
        appeared = {e.get("name") for e in self.transients_if.filter_by_component(self.appeared_detector.component_spec()[1])} - before
        before = {e.get("name") for e in self.transients_if.filter_by_component(self.gone_detector.component_spec()[1])}
        self.gone_detector.loop(self.transients_if, 0)
        gone = {e.get("name") for e in self.transients_if.filter_by_component(self.gone_detector.component_spec()[1])} - before
        return DiffTuple(added=appeared, removed=gone)

    def transients_change_diff(self):
        before = {e.get("name") for e in self.transients_if.filter_by_component(self.add_filter.component_spec()[1])}
        self.add_filter.loop(self.transients_if, 0)
        added = {e.get("name") for e in self.transients_if.filter_by_component(self.add_filter.component_spec()[1])} - before
        before = {e.get("name") for e in self.transients_if.filter_by_component(self.remove_filter.component_spec()[1])}
        self.remove_filter.loop(self.transients_if, 0)
        removed = {e.get("name") for e in self.transients_if.filter_by_component(self.remove_filter.component_spec()[1])} - before
        return DiffTuple(added=added, removed=removed)

## BW COMPAT END

    @contextmanager
    def mock_detection(self, entity_mgr, svc_name, svc_type = None):
        print(" -> Simulate {self.transient_desc} {svc_name} appear".format(**locals()))
        # Service appears
        e = self.appeared_detector.detected_appeared(entity_mgr, svc_name)
        e["type"] = svc_type  # TODO : use method of TypeResolver (similar structure as other systems)
        yield e
        # Service disappear
        self.gone_detector.detected_gone(e)
        print(" -> Mock {self.transient_desc} {svc_name} disappear".format(**locals()))


    @contextmanager
    def mock_filter(self, entity_mgr, e):
        print(" -> Simulate {self.transient_desc} {svc_name} toadd".format(**locals()))
        # Service appears
        self.add_filter.filtered_toadd(entity_mgr, e)
        yield e
        # Service disappear
        self.remove_filter.filtered_toremove(e)
        print(" -> Mock {self.transient_desc} {svc_name} disappear".format(**locals()))

    # TODO : double check : VERY similar to update_transients
    def update_on_diff(self, transients_dt):
        before = {e.get("name") for e in self.transients_if.filter_by_component(self.adder.component_spec()[1])}
        self.adder.loop(self.transients_if, 0)
        added = {e.get("name") for e in self.transients_if.filter_by_component(self.adder.component_spec()[1])} - before
        before = {e.get("name") for e in self.transients_if.filter_by_component(self.remover.component_spec()[1])}
        self.remover.loop(self.transients_if, 0)
        removed = {e.get("name") for e in self.transients_if.filter_by_component(self.remover.component_spec()[1])} - before
        return DiffTuple(added=added, removed=removed)

    def update(self):
        """
        :return: the difference between the transients recently added/removed
        """

        # Preparing to compute difference to report later
        before_all = {e.get("name") for e in self.transients_if.filter_by_component("name")}

        # TODO time delta here
        self.appeared_detector.loop(self.transients_if, 0)
        self.add_filter.loop(self.transients_if, 0)
        self.resolver.loop(self.transients_if, 0)
        self.adder.loop(self.transients_if, 0)
        self.gone_detector.loop(self.transients_if, 0)
        self.remove_filter.loop(self.transients_if, 0)
        self.remover.loop(self.transients_if, 0)

        after_all = {e.get("name") for e in self.transients_if.filter_by_component("name")}

        return DiffTuple(added=after_all - before_all, removed=before_all - after_all)




    # TODO : "wait_for_it" methods that waits for hte detection of a topic/service on the system
    # TODO : Should return a future so use can decide to wait on it or not
    # TODO : Maybe similar to a async_detect ( hooked up to the detected transient, not the exposed ones )
    # TODO : Exposed interface is for direct control flow => async not really needed
    # TODO : Detect/Update interface is inversed control flow ( from update loop ) => Needed
