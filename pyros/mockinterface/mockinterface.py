from __future__ import absolute_import

from contextlib import contextmanager

from ..baseinterface import BaseInterface
from .mocksystem import (
    services_available_remote, services_available_type_remote,
    topics_available_remote, topics_available_type_remote,
    params_available_remote, params_available_type_remote,
)


from .mockservice import MockService
from .mocktopic import MockTopic
from .mockparam import MockParam


class MockInterface(BaseInterface):

    """
    MockInterface.
    """
    def __init__(self, services=None, topics=None, params=None):

        # This base constructor assumes the system to interface with is already available ( can do a get_svc_list() )
        super(MockInterface, self).__init__(services, topics, params)

        # BWCOmpat
        # Mock functions to force changes in interface local cache.
        self.mock_service = self.services.simulate_transient
        self.mock_topic = self.topics.simulate_transient
        self.mock_param = self.params.simulate_transient

    # mock functions that simulate/mock similar interface than what is found on multiprocess framework supported
    # We should try our best to go for the lowest common denominator here
    # SERVICES

    def service_type_resolver(self, service_name):  # function resolving the type of a service
        svc = self.services_available.get(service_name)
        return svc  # None is returned if not found

    def ServiceMaker(self, service_name, service_type, *args, **kwargs):  # the service class implementation
        return MockService(service_name, service_type, *args, **kwargs)

    def ServiceCleaner(self, service):  # the service class cleanup implementation
        return service.cleanup()


    # TOPICS

    def topic_type_resolver(self, topic_name):  # function resolving the type of a topic
        tpc = self.topics_available.get(topic_name)
        return tpc  # None is returned if not found

    def TopicMaker(self, topic_name, topic_type, *args, **kwargs):  # the topic class implementation
        return MockTopic(topic_name, topic_type, *args, **kwargs)

    def TopicCleaner(self, topic):  # the topic class implementation
        return topic.cleanup()

    # PARAMS

    def param_type_resolver(self, param_name):  # function resolving the type of a param
        prm = self.params_available.get(param_name)
        return prm  # None is returned if not found

    def ParamMaker(self, param_name, param_type, *args, **kwargs):  # the param class implementation
        return MockParam(param_name, param_type, *args, **kwargs)

    def ParamCleaner(self, param):  # the param class implementation
        return param.cleanup()

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
