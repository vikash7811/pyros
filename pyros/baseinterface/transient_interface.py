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


# # In case we launch this as a module, we want to be able to resolve relative import and run doctests
# if __package__ is None:
#     import sys
#     from os import path
#     sys.path.append(path.dirname(path.abspath(__file__)))
#     from excess import EntityManager, System, SystemManager
# else:
#     from .excess import EntityManager, System, SystemManager
#



#
#
# WIP : TransientInterface to use as a delegate instead of base interface
#


Name = str  #(unicode ?)
Desc = unicode




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

    def __init__(self, transient_mgr, transient_desc=None, get_transient_list=None, transient_type_resolver=None, tif_maker=None, tif_cleaner=None):
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
        self.transients_if = transient_mgr
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
        # CAREFUL : Special case for sinks : what we removed is what is now missing.
        removed = before - {e.get("name") for e in self.transients_if.filter_by_component(self.remover.component_spec()[1])}
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
