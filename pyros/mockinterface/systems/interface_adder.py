from __future__ import absolute_import
from __future__ import print_function

import logging

import sys

import six

from . import service_excess, topic_excess, param_excess, Changed


@service_excess.register_system({"name", "type", "desc", "tif_maker"}, {"tif"})
def service_interface_adder(entities):
    for name, ent in entities.items():
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


@topic_excess.register_system({"name", "type", "desc", "tif_maker"}, {"tif"})
def topic_interface_adder(entities):
    for ent in entities:
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


@param_excess.register_system({"name", "type", "desc", "tif_maker"}, {"tif"})
def param_interface_adder(entities):
    for ent in entities:
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


# class InterfaceAdder(System):
#
#     def __init__(self):
#         super(InterfaceAdder, self).__init__()
#
#     def component_spec(self):
#         """
#         :return: tuple of the set of component names that are manipulated by this system. input -> output
#         """
#         return {"name", "type", "desc", "tif_maker"}, {"name", "type", "desc", "tif_maker", "tif"}
#
#     def loop(self, entity_mgr, time_delta):
#
#         entities_toadd = entity_mgr.filter_by_component(["name", "type", "desc", "tif_maker"], filter=lambda e: "tif" not in e)
#
#         for ent in entities_toadd:
#             try:
#                 ent["tif"] = ent.get("tif_maker")(ent.get("name"), ent.get("type"))
#                 logging.info(
#                     "[{name}] Interfacing with {desc} {transient}".format(
#                         name=__name__, desc=ent.get("desc"), transient=ent.get("name"))
#                 )
#             except Exception as exc:
#                 logging.warn("[{name}] Cannot interface with {desc} {transient} : {exc}".format(
#                     name=__name__, desc=ent.get("desc"), transient=ent.get("name"), exc=exc)
#                 )
#                 exc_info = sys.exc_info()
#                 six.reraise(exc_info[0], exc_info[1], exc_info[2])
#
# System.register(InterfaceAdder)