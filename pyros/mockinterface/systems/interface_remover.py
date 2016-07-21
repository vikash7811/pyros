from __future__ import absolute_import
from __future__ import print_function

import logging

from . import service_excess, topic_excess, param_excess


@service_excess.register_system({"name", "type", "desc", "tif_cleaner", "tif"}, set())  # this is an entity sink
def service_interface_remover(entities):
        # TODO : move into another system ? or collapse into same component (to keep diff localized) ?

        for n, e in entities.items():
            # because we might have modified resolved_dict after building the list to loop on
            logging.info("[{name}] Removing {desc} {transient}".format(name=__name__, desc=e.get("desc"),
                                                                       transient=n))
            e.get("tif_cleaner")(e.get("tif"))  # calling the cleanup function in case we need to do something
            service_excess.entities.destroy(n)


@topic_excess.register_system({"name", "type", "desc", "tif_cleaner", "tif"}, set())  # this is an entity sink
def topic_interface_remover(entities):
    # TODO : move into another system ? or collapse into same component (to keep diff localized) ?

    for e in entities:
        # because we might have modified resolved_dict after building the list to loop on
        logging.info("[{name}] Removing {desc} {transient}".format(name=__name__, desc=e.get("desc"),
                                                                   transient=e.get("name")))
        e.get("tif_cleaner")(e.get("tif"))  # calling the cleanup function in case we need to do something
        topic_excess.destroy(e)


@param_excess.register_system({"name", "type", "desc", "tif_cleaner", "tif"}, set())  # this is an entity sink
def param_interface_remover(entities):
    # TODO : move into another system ? or collapse into same component (to keep diff localized) ?

    for e in entities:
        # because we might have modified resolved_dict after building the list to loop on
        logging.info(
            "[{name}] Removing {desc} {transient}".format(name=__name__, desc=e.get("desc"),
                                                          transient=e.get("name")))
        e.get("tif_cleaner")(
            e.get("tif"))  # calling the cleanup function in case we need to do something
        param_excess.destroy(e)

# class InterfaceRemover(System):
#
#     def __init__(self):
#         super(InterfaceRemover, self).__init__()
#
#     def component_spec(self):
#         """
#         :return: tuple of the set of component names that are manipulated by this system. input -> output
#
#         Note this is an entity sink since we do not add any component, but instead we remove the entity
#         """
#         return {"name", "type", "desc", "tif_cleaner", "tif"}, set()
#
#     def loop(self, entity_mgr, time_delta):
#
#         # TODO : move into another system ? or collapse into same component (to keep diff localized) ?
#         entities_todel = entity_mgr.filter_by_component(["name", "desc", "tif_cleaner", "tif"])
#
#         for e in entities_todel:
#             # because we might have modified resolved_dict after building the list to loop on
#             logging.info("[{name}] Removing {desc} {transient}".format(name=__name__, desc=e.get("desc"),
#                                                                        transient=e.get("name")))
#             e.get("tif_cleaner")(e.get("tif"))  # calling the cleanup function in case we need to do something
#             entity_mgr.destroy(e)
#
# System.register(InterfaceRemover)