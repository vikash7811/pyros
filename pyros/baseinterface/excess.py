from __future__ import absolute_import
from __future__ import print_function

import abc
import collections

import time

"""
Moving slowly towards entity component system design:

ExCESS : Experimental Component Entity System Simplified
Components as the building blocks of the transients we need to interface (Entity)
Note : we need two loops, one (fast diff state update) nested in the other (slow full state update)

KISS first, using python dynamic nature:
An Entity is just a list of components
A Component is a data type as simple as possible
Systems are usual Python class instances, dealing with a minimum set of components.

Following naming and conventions from https://github.com/alecthomas/entityx
No Events here. Communicate between system synchronously, via components added to entities.
If you need communication between systems, feel free to implement what fits your use-case somewhere else.

The goals are, highest priority first :
 1. be as simple as possible (in python)
 2. be as efficient as possible in a python interpreter.
=> When possible we should leverage already existing python optimizations,
   while keeping a pure python (but low level) coding style
   Therefore, pypy would be our best intepreter for benchmarking.
"""



#: Entity is a dict of components and nothing else.
Entity = dict


class EntityManager(list):
    """
    This class manages Entities.
    It is simply a list that provide extra functionality
    """

    def filter_by_component(self, component_list):
        """
        Return a "view" of the entities currently managed here.
        :param component_list: list of component to filter by
        :return:
        """
        entities_subset = []
        for c in component_list:
            entities_subset += [e for e in self if hasattr(e, c)]
        return entities_subset

    def create(self, iterable=None, **kwargs):
        """
        Creates an Entity and adds it to this manager
        :param iterable:
        :param kwargs:
        :return:
        """
        new_entity = dict(iterable=iterable, **kwargs)
        self.append(new_entity)
        return new_entity

    def destroy(self, entity):
        self.remove(entity)


class System(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        return

    def configure(self, entity_manager):
        return

    def loop(self, entity_mgr, time_delta):
        return time_delta


class SystemManager(list):
    """
    Just a collection of systems
    """

    def __init__(self, entity_mgr, use_wallclock_time = True, iterable=None):
        self.__entity_mgr = entity_mgr
        self.__use_wallclock = use_wallclock_time  #TODO review that, maybe one option is useless for us
        self.__time_counter = time.time() if self.__use_wallclock else time.clock()
        super(SystemManager, self).__init__(iterable=iterable)

    def configure(self):
        for s in self:
            s.configure(self.__entity_mgr)

    def loop(self, time_delta=None, systems=None):

        # Not specifying a system list here trigger update on all systems
        systems = systems or self

        time_delta = time_delta
        # Not specifying a time_delta here trigger a time counter here
        if not time_delta:
            if self.__use_wallclock:
                time_delta = time.time() - self.__time_counter
            else:
                time_delta = time.clock() - self.__time_counter

        for s in systems:
            s.loop(self.__entity_mgr, time_delta)

        return time_delta
