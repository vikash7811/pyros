from __future__ import absolute_import

import logging
import six
import sys
import threading
import collections
import re
import abc
from functools import partial

from . import transient_interface

# module wide to be pickleable
DiffTuple = collections.namedtuple("DiffTuple", " added removed ")


#TODO Entity Component System design for interface loop. cf https://pypi.python.org/pypi/esper (py3 + py2 in fork)
# Entities are transients (ex : for ROS : pubs, subs, svcs, params, and more can be added),
# Systems store logic about when/how a transient should be represented in the interface.
# GOALS : clarity, testability and flexibility
class BaseInterface(object):

    """
    BaseInterface.
    Assumption : we only deal with absolute names here. The users should resolve them
    """
    __metaclass__ = abc.ABCMeta

    def get_svc_list(self):  # function returning all services available on the system
        return self.services_if.get_transient_list()

    @abc.abstractmethod
    def service_type_resolver(self, service_name):  # function resolving the type of a service
        """
        :param service_name: the name of the service
        :return: returns None if the type cannot be found. Properly except in all other unexpected events.
        """
        return

    @abc.abstractmethod
    def ServiceMaker(self, service_name, service_type, *args, **kwargs):  # the service class implementation
        return

    @abc.abstractmethod
    def ServiceCleaner(self, service):  # the service class implementation
        return

    def get_topic_list(self):  # function returning all topics available on the system
        return self.topics_if.get_transient_list()

    @abc.abstractmethod
    def topic_type_resolver(self, topic_name):  # function resolving the type of a topic
        """
        :param topic_name: the name of the topic
        :return: returns None if the topic cannot be found. Properly except in all other unexpected events.
        """
        return

    @abc.abstractmethod
    def TopicMaker(self, topic_name, topic_type, *args, **kwargs):  # the topic class implementation
        return

    @abc.abstractmethod
    def TopicCleaner(self, topic):  # the topic class implementation
        return

    def get_param_list(self):  # function returning all topics available on the system
        return self.params_if.get_transient_list()

    @abc.abstractmethod
    def param_type_resolver(self, param_name):  # function resolving the type of a topic
        return

    @abc.abstractmethod
    def ParamMaker(self, param_name, param_type, *args, **kwargs):  # the topic class implementation
        return

    @abc.abstractmethod
    def ParamCleaner(self, param):  # the topic class implementation
        return

    def __init__(self, services, topics, params):
        """
        Initializes the interface instance, to expose services, topics, and params
        """
        # Current services topics and actions interfaces, i.e. those which are
        # active in the system.
        self.services_if = transient_interface.TransientInterface("service", self.get_svc_list, self.ServiceMaker, self.ServiceCleaner)
        self.topics_if = transient_interface.TransientInterface("topic", self.get_topic_list, self.TopicMaker, self.TopicCleaner)
        self.params_if = transient_interface.TransientInterface("param", self.get_param_list, self.ParamMaker, self.ParamCleaner)

        # TMP assigning the only instance variables to class variables
        BaseInterface.services_if_lock = self.services_if.transients_if_lock  # writer lock (because we have subscribers on another thread)
        BaseInterface.topics_if_lock = self.topics_if.transients_if_lock
        BaseInterface.params_if_lock = self.params_if.transients_if_lock

        # dict style access for bwcompat
        self.services = {e.name: e for e in self.services_if.transients_if.filter_by_component("name")}
        self.topics = {e.name: e for e in self.topics_if.transients_if.filter_by_component("name")}
        self.params = {e.name: e for e in self.params_if.transients_if.filter_by_component("name")}

        # Last requested services topics and actions to be exposed, received
        # from a reconfigure request. Topics which match topics containing
        # wildcards go in here after they are added, but when a new reconfigure
        # request is received, they disappear. The value of the topic and action
        # dicts is the number of instances that that that item has, i.e. how
        # many times the add function has been called for the given key.
        self.services_args = self.services_if.transients_args
        self.params_args = self.params_if.transients_args
        self.topics_args = self.topics_if.transients_args

        # Building an interface dynamically based on the generic functional implementation
        # use is mostly internal ( and child classes )
        self.update_services = self.services_if.update_transients
        self.expose_services = self.services_if.expose_transients_regex
        self.services_change_detect = self.services_if.transients_change_detect
        self.services_change_diff = self.services_if.transients_change_diff

        #self.update_topics = self.topics_if.update_transients
        self.expose_topics = self.topics_if.expose_transients_regex
        #self.topics_change_detect = self.topics_if.transients_change_detect
        #self.topics_change_diff = self.topics_if.transients_change_diff

        #self.update_params = self.params_if.update_transients
        self.expose_params = self.params_if.expose_transients_regex
        #self.params_change_detect = self.params_if.transients_change_detect
        #self.params_change_diff = self.params_if.transients_change_diff

        # BWCOMPAT
        self.expose_params(params)
        self.expose_services(services)
        self.expose_topics(topics)


    def update_on_diff(self, services_dt, topics_dt, params_dt):

        sdt = self.services_if.update_on_diff(services_dt)
        tdt = self.topics_if.update_on_diff(topics_dt)
        pdt = self.params_if.update_on_diff(params_dt)

        return DiffTuple(
            added=sdt.added+tdt.added+pdt.added,
            removed=sdt.removed+tdt.removed+pdt.removed
        )

    def update(self):
        """
        :return: the difference between the transients recently added/removed
        """
        sdt = self.services_if.update()
        tdt = self.topics_if.update()
        pdt = self.params_if.update()

        return DiffTuple(
            added=sdt.added+tdt.added+pdt.added,
            removed=sdt.removed+tdt.removed+pdt.removed
        )

    # TODO : "wait_for_it" methods that waits for hte detection of a topic/service on the system
    # TODO : Should return a future so use can decide to wait on it or not
    # TODO : Maybe similar to a async_detect ( hooked up to the detected transient, not the exposed ones )
    # TODO : Exposed interface is for direct control flow => async not really needed
    # TODO : Detect/Update interface is inversed control flow ( from update loop ) => Needed
