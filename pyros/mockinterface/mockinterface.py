from __future__ import absolute_import

import copy
from contextlib import contextmanager

from ..baseinterface import BaseInterface, TransientInterface
from .mocksystem import (
    services_available_remote, services_available_type_remote,
    topics_available_remote, topics_available_type_remote,
    params_available_remote, params_available_type_remote,
)


from .mockservice import MockService
from .mocktopic import MockTopic
from .mockparam import MockParam


class MockInterface():

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
        self.services_if = TransientInterface("service",
                                              self.get_svc_list,
                                              self.service_type_resolver,
                                              self.ServiceMaker,
                                              self.ServiceCleaner)
        self.topics_if = TransientInterface("topic",
                                            self.get_topic_list,
                                            self.topic_type_resolver,
                                            self.TopicMaker,
                                            self.TopicCleaner)
        self.params_if = TransientInterface("param",
                                            self.get_param_list,
                                            self.param_type_resolver,
                                            self.ParamMaker,
                                            self.ParamCleaner)

        # TMP assigning the only instance variables to class variables
        BaseInterface.services_if_lock = self.services_if.transients_if_lock  # writer lock (because we have subscribers on another thread)
        BaseInterface.topics_if_lock = self.topics_if.transients_if_lock
        BaseInterface.params_if_lock = self.params_if.transients_if_lock

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
        self.resolve_services = self.services_if.resolve_transients

        # self.update_topics = self.topics_if.update_transients
        self.expose_topics = self.topics_if.expose_transients_regex
        # self.topics_change_detect = self.topics_if.transients_change_detect
        # self.topics_change_diff = self.topics_if.transients_change_diff

        # self.update_params = self.params_if.update_transients
        self.expose_params = self.params_if.expose_transients_regex
        # self.params_change_detect = self.params_if.transients_change_detect
        # self.params_change_diff = self.params_if.transients_change_diff

        # BWCOMPAT
        self.expose_params(params)
        self.expose_services(services)
        self.expose_topics(topics)

    # mock functions that simulate/mock similar interface than what is found on multiprocess framework supported
    # We should try our best to go for the lowest common denominator here
    # SERVICES

    def get_svc_list(self):
        svc_list = copy.copy(services_available_remote)  # local copy from proxy
        return svc_list

    def service_type_resolver(self, service_name):  # function resolving the type of a service
        svc_type = services_available_type_remote.get(service_name)
        return svc_type  # None is returned if not found

    def ServiceMaker(self, service_name, service_type, *args, **kwargs):  # the service class implementation
        return MockService(service_name, service_type, *args, **kwargs)

    def ServiceCleaner(self, service):  # the service class cleanup implementation
        return service.cleanup()


    # TOPICS

    def get_topic_list(self):
        topics_list = copy.copy(topics_available_remote)  # local copy from proxy
        return topics_list

    def topic_type_resolver(self, topic_name):  # function resolving the type of a topic
        tpc = topics_available_type_remote.get(topic_name)
        return tpc  # None is returned if not found

    def TopicMaker(self, topic_name, topic_type, *args, **kwargs):  # the topic class implementation
        return MockTopic(topic_name, topic_type, *args, **kwargs)

    def TopicCleaner(self, topic):  # the topic class implementation
        return topic.cleanup()

    # PARAMS

    def get_param_list(self):
        params_list = copy.copy(params_available_remote)
        return params_list

    def param_type_resolver(self, param_name):  # function resolving the type of a param
        prm = params_available_type_remote.get(param_name)
        return prm  # None is returned if not found

    def ParamMaker(self, param_name, param_type, *args, **kwargs):  # the param class implementation
        return MockParam(param_name, param_type, *args, **kwargs)

    def ParamCleaner(self, param):  # the param class implementation
        return param.cleanup()



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
        sdt = self.services_if.update()
        tdt = self.topics_if.update()
        pdt = self.params_if.update()

        return DiffTuple(
            added=sdt.added + tdt.added + pdt.added,
            removed=sdt.removed + tdt.removed + pdt.removed
        )



    def update(self):
        with self.topics_available_lock:
            for t in topics_available_remote:
                self.topics_available[t] = topics_available_type_remote.get(t)

        with self.services_available_lock:
            for s in services_available_remote:
                self.services_available[s] = services_available_type_remote.get(s)

        with self.params_available_lock:
            for p in params_available_remote:
                self.params_available[p] = params_available_type_remote.get(p)

        return super(MockInterface, self).update()



BaseInterface.register(MockInterface)
