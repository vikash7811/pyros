from __future__ import absolute_import
from __future__ import print_function

import logging

import sys

import six

from . import service_excess, topic_excess, param_excess


@service_excess.register_system({"name"}, {"type"})
def service_type_resolver(entities, services_available_type_remote):
    for e, v in six.iteritems(entities):
        try:
            v["type"] = services_available_type_remote.get(e)
        except Exception as exc:
            logging.warn("[{name}] Cannot resolve type of {desc} {transient} : {exc}".format(
                name=__name__, desc=v.get("desc"), transient=e, exc=exc)
            )
            exc_info = sys.exc_info()
            six.reraise(exc_info[0], exc_info[1], exc_info[2])


@topic_excess.register_system({"name"}, {"type"})
def topic_type_resolver(entities, topics_available_type_remote):
    for e in entities:
        try:
            e["type"] = topics_available_type_remote.get(e.get("name"))
        except Exception as exc:
            logging.warn("[{name}] Cannot resolve type of {desc} {transient} : {exc}".format(
                name=__name__, desc=e.get("desc"), transient=e.get("name"), exc=exc)
            )
            exc_info = sys.exc_info()
            six.reraise(exc_info[0], exc_info[1], exc_info[2])


@param_excess.register_system({"name"}, {"type"})
def param_type_resolver(entities, params_available_type_remote):
    for e in entities:
        try:
            e["type"] = params_available_type_remote.get(e.get("name"))
        except Exception as exc:
            logging.warn("[{name}] Cannot resolve type of {desc} {transient} : {exc}".format(
                name=__name__, desc=e.get("desc"), transient=e.get("name"), exc=exc)
            )
            exc_info = sys.exc_info()
            six.reraise(exc_info[0], exc_info[1], exc_info[2])

# class TypeResolver(System):
#
#     def __init__(self):
#         super(TypeResolver, self).__init__()
#
#     def configure(self, entity_mgr, type_resolver):
#         # TODO : make sure this is referenced and can be dynamically updated
#         self.type_resolver = type_resolver
#
#     def component_spec(self):
#         """
#         :return: tuple of the component names that are required, and created
#         """
#         return {"name"}, {"type"}
#
#     def loop(self, entity_mgr, time_delta):
#
#         # only for testing/reporting purpose on what was changed
#         added = []
#         removed = []
#
#         entities_toresolve = entity_mgr.filter_by_component(["name"], filter=lambda e: "type" not in e)
#
#         for e in entities_toresolve:
#             try:
#                 e["type"] = self.type_resolver(e.get("name"))
#             except Exception as exc:
#                 logging.warn("[{name}] Cannot resolve type of {desc} {transient} : {exc}".format(
#                     name=__name__, desc=e.get("desc"), transient=e.get("name"), exc=exc)
#                 )
#                 exc_info = sys.exc_info()
#                 six.reraise(exc_info[0], exc_info[1], exc_info[2])
#
# System.register(TypeResolver)