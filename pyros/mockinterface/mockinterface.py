from __future__ import absolute_import

import collections
import copy
import logging
import threading
from contextlib import contextmanager

from .systems import service_excess, topic_excess, param_excess

from .systems import (
    service_interface_adder, service_interface_remover,
    service_type_resolver,
    service_appeared_detector, service_gone_detector,
    service_add_filter, service_remove_filter,

    topic_interface_adder, topic_interface_remover,
    topic_type_resolver,
    topic_appeared_detector, topic_gone_detector,
    topic_add_filter, topic_remove_filter,

    param_interface_adder, param_interface_remover,
    param_type_resolver,
    param_appeared_detector, param_gone_detector,
    param_add_filter, param_remove_filter,

)

from .mocksystem import (
    services_available_remote, services_available_type_remote,
    topics_available_remote, topics_available_type_remote,
    params_available_remote, params_available_type_remote,
)

from .mockservice import MockService
from .mocktopic import MockTopic
from .mockparam import MockParam

# module wide to be pickleable
DiffTuple = collections.namedtuple("DiffTuple", " added removed ")


class MockInterface(object):

    """
    MockInterface.
    """
    def __init__(self, services=None, topics=None, params=None):
        """
        Initializes the interface instance, to expose services, topics, and params
        """
        # Current services topics and actions interfaces, i.e. those which are
        # active in the system.
        # TODO : collapse this into one (need just one more component)
        self.services_if = service_excess
        self.topics_if = topic_excess
        self.params_if = param_excess

        # TMP assigning the only instance variables to class variables
        services_if_lock = threading.Lock()  # writer lock (because we have subscribers on another thread)
        topics_if_lock = threading.Lock()
        params_if_lock = threading.Lock()

        # Last requested services topics and actions to be exposed, received
        # from a reconfigure request. Topics which match topics containing
        # wildcards go in here after they are added, but when a new reconfigure
        # request is received, they disappear. The value of the topic and action
        # dicts is the number of instances that that that item has, i.e. how
        # many times the add function has been called for the given key.
        self.services_args = set()
        self.params_args = set()
        self.topics_args = set()

        # BWCOMPAT
        self.expose_params(params)
        self.expose_services(services)
        self.expose_topics(topics)

    def expose_services(self, regexes, *class_build_args, **class_build_kwargs):
        """
        Exposes a list of transients regexes. resolved transients not matching the regexes will be removed.
        expose_transients_regex -> transients_change_detect -> transients_change_diff -> update_transients
        :param regexes: the list of regex to filter the transient to add.
               Note: regexes = [] remove all registered regexes.
        :return: a DiffTuple containing the list of transient interfaces (tif) added and removed
        """
        # Important : no effect if names is empty list, only return empty DiffTuple (null element, functional style).

        regexes = regexes or []  # forcing empty list (tofollow normal process) if passed None

        # look through the new service names received by reconfigure, and add
        # those services which are not in the existing service args
        for tst_regex in [r for r in regexes if not r in self.services_args]:
            self.services_args.add(tst_regex)
            logging.info('[{name}] Exposing {desc} regex : {regex}'.format(
                name=__name__, desc="service", regex=tst_regex
            ))
            # TODO : check here for bugs & add test : what if we add multiple regexes ? wont we miss some add_names ?

        # look through the current service args and delete those values which
        # will not be valid when the args are replaced with the new ones. run on
        # a copy so that we will remove from the original without crashing
        for tst_regex in [r for r in self.services_args if not r in regexes]:
            logging.info('[{name}] Withholding {desc} regex : {regex}'.format(
                name=__name__, desc="service", regex=tst_regex
            ))
            self.services_args.remove(tst_regex)

        # forcing immediate update
        return self.update()


    def expose_topics(self, regexes, *class_build_args, **class_build_kwargs):
        """
        Exposes a list of transients regexes. resolved transients not matching the regexes will be removed.
        expose_transients_regex -> transients_change_detect -> transients_change_diff -> update_transients
        :param regexes: the list of regex to filter the transient to add.
               Note: regexes = [] remove all registered regexes.
        :return: a DiffTuple containing the list of transient interfaces (tif) added and removed
        """
        # Important : no effect if names is empty list, only return empty DiffTuple (null element, functional style).

        regexes = regexes or []  # forcing empty list (tofollow normal process) if passed None

        # look through the new service names received by reconfigure, and add
        # those services which are not in the existing service args
        for tst_regex in [r for r in regexes if not r in self.topics_args]:
            self.topics_args.add(tst_regex)
            logging.info('[{name}] Exposing {desc} regex : {regex}'.format(
                name=__name__, desc="topic", regex=tst_regex
            ))
            # TODO : check here for bugs & add test : what if we add multiple regexes ? wont we miss some add_names ?

        # look through the current service args and delete those values which
        # will not be valid when the args are replaced with the new ones. run on
        # a copy so that we will remove from the original without crashing
        for tst_regex in [r for r in self.topics_args if not r in regexes]:
            logging.info('[{name}] Withholding {desc} regex : {regex}'.format(
                name=__name__, desc="topic", regex=tst_regex
            ))
            self.topics_args.remove(tst_regex)

        # forcing immediate update
        return self.update()


    def expose_params(self, regexes, *class_build_args, **class_build_kwargs):
        """
        Exposes a list of transients regexes. resolved transients not matching the regexes will be removed.
        expose_transients_regex -> transients_change_detect -> transients_change_diff -> update_transients
        :param regexes: the list of regex to filter the transient to add.
               Note: regexes = [] remove all registered regexes.
        :return: a DiffTuple containing the list of transient interfaces (tif) added and removed
        """
        # Important : no effect if names is empty list, only return empty DiffTuple (null element, functional style).

        regexes = regexes or []  # forcing empty list (tofollow normal process) if passed None

        # look through the new service names received by reconfigure, and add
        # those services which are not in the existing service args
        for tst_regex in [r for r in regexes if not r in self.params_args]:
            self.params_args.add(tst_regex)
            logging.info('[{name}] Exposing {desc} regex : {regex}'.format(
                name=__name__, desc="param", regex=tst_regex
            ))
            # TODO : check here for bugs & add test : what if we add multiple regexes ? wont we miss some add_names ?

        # look through the current service args and delete those values which
        # will not be valid when the args are replaced with the new ones. run on
        # a copy so that we will remove from the original without crashing
        for tst_regex in [r for r in self.params_args if not r in regexes]:
            logging.info('[{name}] Withholding {desc} regex : {regex}'.format(
                name=__name__, desc="param", regex=tst_regex
            ))
            self.params_args.remove(tst_regex)

        # forcing immediate update
        return self.update()

    ## BW COMPAT BEGIN

    def update_services(self):
        added = service_interface_adder()

        removed = service_interface_remover()

        return DiffTuple(added=added, removed=removed)

    def resolve_services(self):
        resolved = service_type_resolver(services_available_type_remote)
        return resolved

    def services_change_detect(self):
        appeared = service_appeared_detector(services_available_remote)

        gone = service_gone_detector(services_available_remote)

        return DiffTuple(added=appeared, removed=gone)

    def services_change_diff(self):
        added = service_add_filter(self.services_args, MockService)

        removed = service_remove_filter(self.services_args)

        return DiffTuple(added=added, removed=removed)

    ## BW COMPAT END

    def update_on_diff(self, services_dt, topics_dt, params_dt):

        sdt = self.services_if.update_on_diff(services_dt)
        tdt = self.topics_if.update_on_diff(topics_dt)
        pdt = self.params_if.update_on_diff(params_dt)

        return DiffTuple(
            added=sdt.added + tdt.added + pdt.added,
            removed=sdt.removed + tdt.removed + pdt.removed
        )

    def update(self):
        """
        :return: the difference between the transients recently added/removed
        """

        # TODO time delta here
        appeared = service_appeared_detector(services_available_remote)
        added_filter = service_add_filter(self.services_args, MockService)
        resolved = service_type_resolver(services_available_type_remote)
        service_interface_added = service_interface_adder()

        gone = service_gone_detector(services_available_remote)
        removed_filter = service_remove_filter(self.services_args)
        service_interface_removed = service_interface_remover()

        # This is the only thing that matters here
        # => Does this mean that it would be easier to chain the systems :
        #    - by inheritance ??
        #    - by function call ??
        #    - by result_parameter (chaining API) ??
        sdt = DiffTuple(added=service_interface_added.keys(), removed=service_interface_removed.keys())

        appeared = topic_appeared_detector(topics_available_remote)
        added_filter = topic_add_filter(self.topics_args, MockTopic)
        resolved = topic_type_resolver(topics_available_type_remote)
        topic_interface_added = topic_interface_adder()

        gone = topic_gone_detector(topics_available_remote)
        removed_filter = topic_remove_filter(self.services_args)
        topic_interface_removed = topic_interface_remover()


        tdt = DiffTuple(added=topic_interface_added.keys(), removed=topic_interface_removed.keys())

        appeared = param_appeared_detector(params_available_remote)
        added_filter = param_add_filter(self.params_args, MockParam)
        resolved = param_type_resolver(params_available_type_remote)
        param_interface_added = param_interface_adder()

        gone = param_gone_detector(params_available_remote)
        removed_filter = param_remove_filter(self.params_args)
        param_interface_removed = param_interface_remover()

        pdt = DiffTuple(added=param_interface_added.keys(), removed=param_interface_removed.keys())

        return DiffTuple(
            added=sdt.added + tdt.added + pdt.added,
            removed=sdt.removed + tdt.removed + pdt.removed
        )

