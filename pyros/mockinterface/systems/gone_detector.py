from __future__ import absolute_import
from __future__ import print_function

import copy
import logging

from . import service_excess, topic_excess, param_excess, Changed


@service_excess.register_system({"name"}, {"changed"})
def service_gone_detector(entities, services_available_remote):
    transient_detected = copy.copy(services_available_remote)

    for t, v in entities.items():
        if not t in transient_detected:
            ####self.detected_gone(entity_mgr, t)
            v["changed"] = Changed.GONE
            # TODO : find a solution for cleaning up...

            # TODO : think more about the case of a transient that is detected both appeared and gone


@topic_excess.register_system({"name"}, {"changed"})
def topic_gone_detector(entities, topics_available_remote):
    transient_detected = copy.copy(topics_available_remote)

    for t in entities:
        if not t.get("name") in transient_detected:
            ####self.detected_gone(entity_mgr, t)
            t["changed"] = Changed.GONE
            # TODO : find a solution for cleaning up...

            # TODO : think more about the case of a transient that is detected both appeared and gone


@param_excess.register_system({"name"}, {"changed"})
def param_gone_detector(entities, params_available_remote):
    transient_detected = copy.copy(params_available_remote)

    for t in entities:
        if not t.get("name") in transient_detected:
            ####self.detected_gone(entity_mgr, t)
            t["changed"] = Changed.GONE
            # TODO : find a solution for cleaning up...

            # TODO : think more about the case of a transient that is detected both appeared and gone

# class GoneDetector(System):
#     """
#     This systems detect if any change happened on the system
#     ChangeDetector -> ChangeFilter -> InterfaceUpdater
#     """
#
#     def __init__(self):
#         super(GoneDetector, self).__init__()
#
#     def component_spec(self):
#         """
#         :return: tuple of the set of component names that are manipulated by this system. input -> output
#
#         Note this is an entity source since we do not rely on any existing component, but instead we create the entity
#         """
#
#         return {"name"}, {"changed"}
#
#     def configure(self, entity_mgr, get_transient_list, transient_desc):
#         # TODO : make sure this is referenced and can be dynamically updated
#         self.get_transient_list = get_transient_list
#         self.transient_desc = transient_desc
#
#     def loop(self, entity_mgr, time_delta):
#         transients_known = entity_mgr.filter_by_component("name")
#
#         transient_detected = self.get_transient_list()
#
#         for t in transients_known:
#             if not t.get("name") in transient_detected:
#                 self.detected_gone(entity_mgr, t)
#
#         # TODO : think more about the case of a transient that is detected both appeared and gone
#
#     # These are useful to test this system effects on the entities
#     def detected_gone(self, entity_mgr, tst):
#         tst["changed"] = Changed.GONE
#         #TODO : find a solution for cleaning up...
#         return tst.get("name")
#
# System.register(GoneDetector)