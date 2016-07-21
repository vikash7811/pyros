from __future__ import absolute_import
from __future__ import print_function

import copy
import logging

import six
from . import service_excess, topic_excess, param_excess, Changed


@service_excess.register_system(set(), {"changed"})  # this is an entity source
def service_appeared_detector(entities, services_available_remote):  # we pass entity but we wont use it anyway
    transient_detected = copy.copy(services_available_remote)  # local copy from proxy

    for t in transient_detected:
        if not t in [e for e in service_excess.entities.keys()]:
            #####self.detected_appeared(entity_mgr, t)
            # TODO : if available we already want the type here.
            # If not the resolver will deal with it later...
            service_excess.entities.create(name=t, changed=Changed.APPEARED, desc="service")
            # TODO : think more about the case of a transient that is detected both appeared and gone...


@topic_excess.register_system(set(), {"changed"})  # this is an entity source
def topic_appeared_detector(entities, topics_available_remote):  # we pass entity but we wont use it anyway
    transient_detected = copy.copy(topics_available_remote)  # local copy from proxy

    for t in transient_detected:
        if not t in [e.get("name") for e in topic_excess.filter_by_component("name")]:
            #####self.detected_appeared(entity_mgr, t)
            # TODO : if available we already want the type here.
            # If not the resolver will deal with it later...
            topic_excess.create(name=t, changed=Changed.APPEARED, desc="topic")
            # TODO : think more about the case of a transient that is detected both appeared and gone...


@param_excess.register_system(set(), {"changed"})  # this is an entity source
def param_appeared_detector(entities, params_available_remote):  # we pass entity but we wont use it anyway
    transient_detected = copy.copy(params_available_remote)  # local copy from proxy

    for t in transient_detected:
        if not t in [e.get("name") for e in param_excess.filter_by_component("name")]:
            #####self.detected_appeared(entity_mgr, t)
            # TODO : if available we already want the type here.
            # If not the resolver will deal with it later...
            param_excess.create(name=t, changed=Changed.APPEARED, desc="param")
            # TODO : think more about the case of a transient that is detected both appeared and gone...


# class AppearedDetector(System):
#     """
#     This systems detect if any change happened on the system
#     ChangeDetector -> ChangeFilter -> InterfaceUpdater
#     """
#
#     def __init__(self):
#         super(AppearedDetector, self).__init__()
#
#     def component_spec(self):
#         """
#         :return: tuple of the set of component names that are manipulated by this system. input -> output
#
#         Note this is an entity source since we do not rely on any existing component, but instead we create the entity
#         """
#
#         return set(), {"changed"}
#
#     def configure(self, entity_mgr, get_transient_list, transient_desc):
#         # TODO : make sure this is referenced and can be dynamically updated
#         self.get_transient_list = get_transient_list
#         self.transient_desc = transient_desc
#
#     def loop(self, entity_mgr, time_delta):
#         transients_known = [e.get("name") for e in entity_mgr.filter_by_component("name")]
#
#         transient_detected = self.get_transient_list()
#
#         for t in transient_detected:
#             if not t in transients_known:
#                 self.detected_appeared(entity_mgr, t)
#
#         # TODO : think more about the case of a transient that is detected both appeared and gone...
#
#     # These are useful to test this system effects on the entities
#     # TODO : if available we already want the type here.
#     # If not the resolver will deal with it later...
#     def detected_appeared(self, entity_mgr, tst_name):
#         return entity_mgr.create(name=tst_name, changed=Changed.APPEARED, desc=self.transient_desc)
#
# System.register(AppearedDetector)