from __future__ import absolute_import

import time

import roslib
import rospy

from importlib import import_module
from collections import deque, OrderedDict


from .message_conversion import get_msg, get_msg_dict, populate_instance, extract_values, FieldTypeMismatchException


def get_topic_msg(topic):
    return get_msg(topic.rostype)


def get_topic_msg_dict(topic):
    return get_msg_dict(topic.rostype)


class TopicBase(object):
    """
    TopicBase is the class implementing common behavior between Subscriber and Publisher.
    It should be used to manipulate Topics.
    """

    # We need some kind of instance count here since system state returns only one node instance
    # as publisher for multiple publisher in this process.
    #
    # This is used in ros_interface update for added puba/subs to determine
    # if we previously started publishing / subscribing to this topic
    # usually the count will be just 1, but more is possible during tests
    #
    # This is also used in ros_interface update for removed pubs/subs to determine
    # if we previously stopped publishing / subscribing to this topic
    # usually the count will be just 1, but more is possible during tests

    def __init__(self, topic_name, topic_type, *args, **kwargs):

        topic_name = rospy.resolve_name(topic_name)
        # TODO : simplify this, since we have normalized topic_name in pub and sub interface classes
        self.name = topic_name

        topic_type_module, topic_type_name = tuple(topic_type.split('/'))
        roslib.load_manifest(topic_type_module)
        msg_module = import_module(topic_type_module + '.msg')

        self.rostype_name = topic_type
        self.rostype = getattr(msg_module, topic_type_name)

        self.msgtype = get_topic_msg_dict(self)

    def cleanup(self):
        """
        Launched when we want to whithhold this interface instance
        :return:
        """
        pass

    def asdict(self):
        """
        Here we provide a dictionary suitable for a representation of the Topic instance
        the main point here is to make it possible to transfer this to remote processes.
        We are not interested in pickleing the whole class with Subscriber and Publisher
        :return:
        """
        return {
            'name': self.name,
            'msgtype': self.msgtype,
            'rostype_name': self.rostype_name,
        }



