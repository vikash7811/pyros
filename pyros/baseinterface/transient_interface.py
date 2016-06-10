from __future__ import absolute_import
from __future__ import print_function

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


class InterfaceUpdater(System):

    def __init__(self):
        super(InterfaceUpdater, self).__init__()

    def loop(self, entity_mgr, time_delta):

        # only for testing/reporting purpose on what was changed
        added = []
        removed = []

        entities_toadd = entity_mgr.filter_by_component(["name", "type", "desc", "tif_maker"])

        for e in entities_toadd:
            try:
                e["tif"] = e.get("tif_maker")(e.get("name"), e.get("type"), e.get("class_build_args"), e.get("class_build_kwargs"))
                added += [e.get("name")]
                logging.info(
                    "[{name}] Interfacing with {desc} {transient}".format(
                        name=__name__, desc=e.get("desc"), transient=e.get("name"))
                )
            except Exception as exc:
                logging.warn("[{name}] Cannot interface with {desc} {transient} : {exc}".format(
                    name=__name__, desc=e.get("desc"), transient=e.get("name"), exc=exc)
                )
                exc_info = sys.exc_info()
                six.reraise(exc_info[0], exc_info[1], exc_info[2])

        # TODO : move into another system ? or collapse into same component (to keep diff localized) ?
        entities_todel = entity_mgr.filter_by_component(["name", "desc", "tif_cleaner"])

        for e in entities_todel:
            # because we might have modified resolved_dict after building the list to loop on
            logging.info("[{name}] Removing {desc} {transient}".format(name=__name__, desc=e.desc,
                                                                       transient=e.get("name")))
            e.tif_cleaner(e.name)  # calling the cleanup function in case we need to do something
            e.destroy()
            removed += [e.name]

System.register(InterfaceUpdater)


class ChangeFilter(System):
    """
    this system determines which change of the system should actually trigger transient interface creation/deletion
    ChangeFilter -> InterfaceUpdater
    """

    def __init__(self):
        """
        Initializes this System
        """
        super(ChangeFilter, self).__init__()

    def configure(self, entity_mgr, regex_args, tif_maker, tif_cleaner):
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
        self.tif_cleaner = tif_cleaner

    def loop(self, entity_mgr, time_delta):
        """
        Add constructor/destructor functions to be called for each added/gone entity
        :param entity_mgr: the entity manager we work with
        :param time_delta: the time_delta since the last update
        :return: None
        >>> entities= EntityManager()
        >>> entities.create(name="test_added_entity", changed=Changed.ADDED, desc="filterable_entity")
        >>> entities.create(name="test_gone_entity", changed=Changed.GONE, desc="filterable_entity")
        >>> s = ChangeFilter()
        >>> s.configure(regex_args=["test_.*"], tif_maker=(lambda n, t: print("maker({0},{1}".format(n,t))), tif_cleaner=(lambda n, t: print("cleaner({0},{1}".format(n,t))))
        >>> s.loop(1)
        >>> entities.filter_by_component(["changed"], lambda e: e.get("changed") == ADDED)
        []
        >>> entities.filter_by_component(["changed"], lambda e: e.get("changed") == GONE)
        []
        """
        transients_changed = entity_mgr.filter_by_component(["name", "changed", "desc"])

        transients_appeared = [t for t in transients_changed if t.get("changed") == Changed.ADDED]
        to_add = [m for m in regexes_match_sublist(self.regex_args, transients_appeared)]

        for t in to_add:
            self.filtered_toadd(t)

        transients_gone = [t for t in transients_changed if t.get("changed") == Changed.GONE]
        lost_matches = [n for n in entity_mgr.filter_by_component("name") if find_first_regex_match(n.get("name"), self.regex_args) is None]
        to_remove = transients_gone + lost_matches  # we stop interfacing with lost transient OR lost matches

        for t in to_remove:
            self.filtered_toremove(t)


    # These are useful to test this system effects on the entities
    def filtered_toadd(self, t):
        t["tif_maker"] = self.tif_maker

    def filtered_toremove(self, t):
        t["tif_cleaner"] = self.tif_cleaner

    @contextmanager
    def filter(self, entity_mgr, e):  # TODO used passed type
        print(" -> Simulate {self.transient_desc} {svc_name} toadd".format(**locals()))
        # Service appears
        self.filtered_toadd(entity_mgr, e)
        yield e
        # Service disappear
        self.filtered_toremove(e)
        print(" -> Mock {self.transient_desc} {svc_name} disappear".format(**locals()))

System.register(ChangeFilter)


class ChangeDetector(System):
    """
    This systems detect if any change happened on the system
    ChangeDetector -> ChangeFilter -> InterfaceUpdater
    """

    def __init__(self):
        super(ChangeDetector, self).__init__()

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

        for t in transients_known:
            if not t in transient_detected:
                self.detected_gone(entity_mgr, t)

        # TODO : think more about the case of a transient that is detected both appeared and gone,
        # maybe via two different systems ?

    # These are useful to test this system effects on the entities
    # TODO : if available we already want the type here.
    # If not the resolver will deal with it later...
    def detected_appeared(self, entity_mgr, tst_name):
        return entity_mgr.create(name=tst_name, changed=Changed.APPEARED, desc=self.transient_desc)

    def detected_gone(self, entity_mgr, tst):
        tst["changed"] = Changed.GONE
        #TODO : find a solution for cleaning up...
        return tst.get("name")

    @contextmanager
    def detection(self, entity_mgr, svc_name, svc_type = None):  # TODO used passed type
        print(" -> Simulate {self.transient_desc} {svc_name} appear".format(**locals()))
        # Service appears
        e = self.detected_appeared(entity_mgr, svc_name)
        yield e
        # Service disappear
        self.detected_gone(e)
        print(" -> Mock {self.transient_desc} {svc_name} disappear".format(**locals()))


System.register(ChangeDetector)


#TODO Entity Component System design for interface loop. cf https://pypi.python.org/pypi/esper (py3 + py2 in fork)
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
        self.updater = InterfaceUpdater()
        self.change_detector = ChangeDetector()
        self.change_filter = ChangeFilter()

        # configuring all systems, ready to go
        self.resolver.configure(self.transients_if, self.transient_type_resolver)
        self.updater.configure(self.transients_if)
        self.change_detector.configure(self.transients_if, get_transient_list, transient_desc)
        self.change_filter.configure(self.transients_if, self.transients_args, tif_maker, tif_cleaner)

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

## BW COMPAT BGIN

    def update_transients(self):
        before = {e.get("name") for e in self.transients_if.filter_by_component("name")}
        self.updater.loop(self.transients_if, 0)
        after = {e.get("name") for e in self.transients_if.filter_by_component("name")}
        return DiffTuple(added=after - before, removed=before - after)

    def transients_change_detect(self):
        before = {e.get("name") for e in self.transients_if.filter_by_component("name")}
        self.change_detector.loop(self.transients_if, 0)
        after = {e.get("name") for e in self.transients_if.filter_by_component("name")}
        return DiffTuple(added=after - before, removed=before - after)

    def transients_change_diff(self):
        before = {e.get("name") for e in self.transients_if.filter_by_component("name")}
        self.change_filter.loop(self.transients_if, 0)
        after = {e.get("name") for e in self.transients_if.filter_by_component("name")}
        return DiffTuple(added=after - before, removed=before - after)

## BW COMPAT END


    def update_on_diff(self, transients_dt):

        # Preparing to compute difference to report later
        before_expose = {e.name for e in self.transients_if.filter_by_component("name")}

        #TODO time delta here
        self.updater.loop(self.transients_if, 0)

        after_expose = {e.name for e in self.transients_if.filter_by_component("name")}

        return DiffTuple(added=after_expose - before_expose, removed=before_expose - after_expose)

    def update(self):
        """
        :return: the difference between the transients recently added/removed
        """

        # Preparing to compute difference to report later
        before_expose = {e.get("name") for e in self.transients_if.filter_by_component("name")}

        # TODO time delta here
        self.change_detector.loop(self.transients_if, 0)
        self.change_filter.loop(self.transients_if, 0)
        self.resolver.loop(self.transients_if, 0)
        self.updater.loop(self.transients_if, 0)

        after_expose = {e.get("name") for e in self.transients_if.filter_by_component("name")}

        return DiffTuple(added=after_expose - before_expose, removed=before_expose - after_expose)




    # TODO : "wait_for_it" methods that waits for hte detection of a topic/service on the system
    # TODO : Should return a future so use can decide to wait on it or not
    # TODO : Maybe similar to a async_detect ( hooked up to the detected transient, not the exposed ones )
    # TODO : Exposed interface is for direct control flow => async not really needed
    # TODO : Detect/Update interface is inversed control flow ( from update loop ) => Needed
