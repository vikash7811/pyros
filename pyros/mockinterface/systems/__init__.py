# -*- coding: utf-8 -*-
# This python package is keeping together all pyros systems
#
from __future__ import absolute_import
from __future__ import print_function


from .excess import Excess

# Because currently everything is designed around these 3 concepts, we define them right here
# this "central app" will help defining systems and other interactions with our entities
service_excess = Excess("name")
topic_excess = Excess("name")
param_excess = Excess("name")
# TODO : merge to only one

# simplistic bwcompat enum implementation
def enum(**enums):
    return type('Enum', (), enums)

Changed = enum(UNKNOWN=0, APPEARED=1, GONE=2)


from .add_filter import service_add_filter, topic_add_filter, param_add_filter
from .appeared_detector import service_appeared_detector, topic_appeared_detector, param_appeared_detector
from .gone_detector import service_gone_detector, topic_gone_detector, param_gone_detector
from .interface_adder import service_interface_adder, topic_interface_adder, param_interface_adder
from .interface_remover import service_interface_remover, topic_interface_remover, param_interface_remover
from .remove_filter import service_remove_filter, topic_remove_filter, param_remove_filter
from .type_resolver import service_type_resolver, topic_type_resolver, param_type_resolver

__all__ = [
    'service_add_filter',
    'service_appeared_detector',
    'service_gone_detector',
    'service_interface_adder',
    'service_interface_remover',
    'service_remove_filter',
    'service_type_resolver'
]
