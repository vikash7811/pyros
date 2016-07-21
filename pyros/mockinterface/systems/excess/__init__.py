# -*- coding: utf-8 -*-
# Experimental Component Entity System Simplified
# This python package is implementing Entity Component System design in python
# Main use case focus :
# - use in a "process manager" ( to simulate process isolation, but in one thread )
# - use in game engine (as a validation step, like most already existing Entity Components Systems)
# - use in "functional language-like" programmation style,
#   enforcing function isolation, with only explicit data sharing (entities)
# - use as a way of coding that can be distributed easily.
#
#
from __future__ import absolute_import
from __future__ import print_function


from .excess import Excess, EntityDict

__all__ = [
    'Entitydict',
    'Excess',
]
