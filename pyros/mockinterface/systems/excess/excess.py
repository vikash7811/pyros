from __future__ import absolute_import
from __future__ import print_function

import abc
import collections
import hashlib
import logging

import time
from functools import wraps
import six

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
# we need the mapping (dict) to act like "types for systems" and components should be simplest data type.
Entity = dict


# TODO : Defining components to enforce strong typing where possible
# Goal : avoid deep unexpected behavior
# TODO : think about enforcing component immutability (namedtuple/frozendict)
#        to make concurrency much harder to get wrong,
#        and to make DB storage much easier
# TODO : or maybe slots ?

import collections

class EntityDict(collections.MutableMapping):

    """
    A dictionary that stores entities.
    Index entities using one defined component (auto index if needed)
    Allow extraction of sub-dict by filtering entities in/out based on the components they contain
    """
    def __init__(self, _entitydict_index="key", _entitydict_autoindex=True, *args, **kwargs):
        """
        :param _entitydict_index: the component that will be the index for the entities storage
        :param _entitydict_autoindex: whether we allow
        :param args:
        :param kwargs:
        """
        self.store = dict()
        self._entitydict_index_component = _entitydict_index
        self._entitydict_autoindex = _entitydict_autoindex
        self.update(dict(*args, **kwargs))  # use the free update to set keys

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value=None):
        """
        Adds an entity to this entity storage
        :param value: the object to store
        :return:
        >>> entities = EntityDict()
        >>> entities.__setitem__('unique_key', {'c1': 'ceeone', 'c3': 'c3'})
        """
        value = value or dict()
        assert isinstance(value, Entity)  # early assert to avoid mistakes. TODO : better API ?

        # If key it not correct, this will except the same way that original dict.__setitem__ would
        self.store[key] = value

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __repr__(self):
        return self.store.__repr__()

    # Enforcing python3 interface even on python 2
    def keys(self):
        return six.viewkeys(self.store)

    # Enforcing python3 interface even on python 2
    def values(self):
        return six.viewvalues(self.store)

    # Enforcing python3 interface even on python 2
    def items(self):
        return six.viewitems(self.store)

    def filter_by_component(self, filter_in, filter_out=None):
        """
        Return a "view" of the entities currently managed here.
        :param filter_in: list of component names to allow pass
        :param filter_out : list of component names to block
        :return:
        >>> entities = EntityDict("c1")
        >>> entities.__createitem__({'c1': 'ceeone', 'c2': 'ceetwo', 'c3': 'c3'})
        {'c3': 'c3', 'c2': 'ceetwo', 'c1': 'ceeone'}
        >>> entities.__createitem__({'c1': 'c1', 'c5': 'cfive', 'c2': 'c2'})
        {'c2': 'c2', 'c1': 'c1', 'c5': 'cfive'}
        >>> entities.filter_by_component(['c1', 'c2'])
        {'c1': {'c2': 'c2', 'c1': 'c1', 'c5': 'cfive'}, 'ceeone': {'c3': 'c3', 'c2': 'ceetwo', 'c1': 'ceeone'}}
        >>> entities.filter_by_component('c5')
        {'c1': {'c2': 'c2', 'c1': 'c1', 'c5': 'cfive'}}
        >>> entities.filter_by_component(['c5', 'c7'])
        {}
        >>> entities.filter_by_component([])
        {'c1': {'c2': 'c2', 'c1': 'c1', 'c5': 'cfive'}, 'ceeone': {'c3': 'c3', 'c2': 'ceetwo', 'c1': 'ceeone'}}
        >>> entities.filter_by_component([], 'c5')
        {'ceeone': {'c3': 'c3', 'c2': 'ceetwo', 'c1': 'ceeone'}}
        """

        if type(filter_in) is not set:
            if type(filter_in) is list:
                filter_in = set(filter_in)
            else:  # usually string type
                filter_in = {filter_in}

        if type(filter_out) is not set:
            if type(filter_out) is list:
                filter_out = set(filter_out)
            else:  # usually string type
                filter_out = {filter_out}

        subdict={
            i: e for i, e in self.items() if
            set(e).intersection(filter_in) == filter_in and set(e).intersection(filter_out) == set()
        }

        return EntityDict(
            self._entitydict_index_component,
            self._entitydict_autoindex,
            subdict
        )

    @staticmethod
    def __generate_index_for_entity(entity_value):
        # build a string from items ( should be serializable )
        unique_str = ''.join(["'%s':'%s';" % (key, val) for (key, val) in sorted(entity_value.items())])
        return hashlib.sha1(unique_str).hexdigest()  # signature

    # TODO : follow dict API better here
    def __createitem__(self, value):
        """
        Creates an Entity and adds it to this manager
        :param value: the object to store
        :return:
        >>> entities = EntityDict()
        >>> entities.__createitem__({'c1': 'ceeone', 'c2': 'ceetwo', 'c3': 'c3'})
        {'c3': 'c3', 'c2': 'ceetwo', 'c1': 'ceeone', 'key': '69402c9e9460a2077163dbc80d79fb7b0cc41101'}
        >>> entities.__createitem__({'c1': 'ceeone', 'key': 'the_unique_key', 'c3': 'c3'})
        {'c3': 'c3', 'c1': 'ceeone', 'key': 'the_unique_key'}

        """

        if self._entitydict_index_component not in value and self._entitydict_autoindex:
            index = self.__generate_index_for_entity(value)
            value[self._entitydict_index_component] = index  # TODO : this duplicates data and might not be needed ?
        else:
            index = value[self._entitydict_index_component]

        self.__setitem__(index, value)
        return value

    def create(self, iterable=None, **kwargs):
        """
        Creates an Entity and adds it to this manager
        If the key is contained in the Entity, it will be used to index it in the storage.
        :param iterable:
        :param kwargs:
        :return:
        >>> entities = EntityDict()
        >>> entities.create(c1='ceeone', c2='ceetwo', c3='c3')
        {'c3': 'c3', 'c2': 'ceetwo', 'c1': 'ceeone', 'key': '69402c9e9460a2077163dbc80d79fb7b0cc41101'}
        >>> entities.create({'c1': 'c1', 'c2': 'ceetwo', 'c5': 'c5'})
        {'c2': 'ceetwo', 'c1': 'c1', 'key': '44e281a1dfd5210b59bbe1107d4622850abd479d', 'c5': 'c5'}
        """
        if iterable:
            return self.__createitem__(dict(iterable))
        else:
            return self.__createitem__(dict(**kwargs))

    def destroy(self, entity_key):
        return self.pop(entity_key)


class Excess(object):
    """
    This class manages Entity Comoponent System Application.
    It is more than a storage of Entity, It centralizes all Entity / System structure.
    So it provides a central "App" ( check flask python code design )
    """

    def __init__(self, index="key"):
        """
        :param index: the component that will be the index for the entities storage
        """
        #: entities : storage of all entities for this Excess app.
        self.entities = EntityDict(_entitydict_index=index)

    def register_system(self, input=set(), output=None, *args, **kwargs):
        """
        System decorator for the system function that return the entities that have been changed
        The function decorated needs to accept entities set as input, and have no return (it will be ignored).
        :param input: a set of accepted components as input
        :param output: a set of created components by this system
        :param args: extra args
        :param kwargs: extra kwargs
        :return: A decorated function
        """
        def decorator(fn):
            @wraps(fn)
            def system_decorated(*args, **kwargs):

                before = self.entities.filter_by_component(output)

                fn(self.entities.filter_by_component(input, output), *args, **kwargs)

                if output == set():  # This is an entity sink
                    changed = {k: e for k, e in six.iteritems(before) if k not in self.entities.filter_by_component(output)}  # this is actually everything (before) minus everything (now)
                else:
                    changed = {k: e for k, e in six.iteritems(self.entities.filter_by_component(output)) if k not in before.keys()}

                return changed
            # TODO : store all systems here, and this could manage the overall update of systems
            # => merge entityManager and systemManager into one App => KISS.
            #self.systems = (self.systems or []) + system_decorated
            return system_decorated

        return decorator


#
# Systems behave on components like functors behave on types
# => Lets make system a glorified functor
#
# if system is class
# TODO : system can inherits from one another, and dynamically determine the output compspec
# => composing functors statically, ie (f.g)(x) instead of f(g(x))
#
# but maybe we can make system out of functions (decorators) ?
#
class System(object):

    def __init__(self, input=set(), output=None):
        """
        Initializes a System, with input and output specification
        :param input: None means not set (this system is an entity source). empty set means set to nothing.
        :param output: None means not set (this system is an entity sink). empty set means set to nothing(can still be set dynamically).
        """
        self._compspec = (input, output)
        self._entity_mgr = None
        return

    def configure(self, entity_manager, *args, **kwargs):
        """
        We can pass the entity_manager once, reference will be kept here
        :param entity_manager:
        :param args:
        :param kwargs:
        :return:
        """
        self._entity_mgr = entity_manager
        # TODO : maybe it is enough to store all args here ?
        return

    # TODO : time this https://www.codementor.io/python/tutorial/advanced-use-python-decorators-class-function
    def update(self, time_delta):
        before = {e for e in self._entity_mgr.filter_by_component(self.adder.component_spec()[1])}
        self.__call__({e for e in self._entity_mgr.filter_by_component(self.adder.component_spec()[0])}, time_delta)
        if self._compspec[1] is None:  # This is an entity sink
            changed = before - {e for e in self._entity_mgr.filter_by_component(self.adder.component_spec()[1])}
        else:
            changed = {e for e in self._entity_mgr.filter_by_component(self.adder.component_spec()[1])} - before

        return changed

    def __call__(self, entities):
        return





def system(input=set(), output=None):
    def system_decorator(Cls):
        class NewCls(object):
            def __init__(self, *args, **kwargs):
                self.oInstance = Cls(*args, **kwargs)
                self._compspec = (input, output)
                self._entity_mgr = None

            def __getattribute__(self, s):
                """
                this is called whenever any attribute of a NewCls object is accessed. This function first tries to
                get the attribute off NewCls. If it fails then it tries to fetch the attribute from self.oInstance (an
                instance of the decorated class). If it manages to fetch the attribute from self.oInstance, and
                the attribute is an instance method then `time_this` is applied.
                """
                try:
                    x = super(NewCls, self).__getattribute__(s)
                except AttributeError:
                    pass
                else:
                    return x
                x = self.oInstance.__getattribute__(s)
                if type(x) == type(self.__init__):  # it is an instance method
                    return time_this(x)  # this is equivalent of just decorating the method with time_this
                else:
                    return x


        return NewCls



def update_transients(self):
    before = {e.get("name") for e in self.transients_if.filter_by_component(self.adder.component_spec()[1])}
    self.adder.loop(self.transients_if, 0)
    added = {e.get("name") for e in self.transients_if.filter_by_component(self.adder.component_spec()[1])} - before
    before = {e.get("name") for e in self.transients_if.filter_by_component(self.remover.component_spec()[1])}
    self.remover.loop(self.transients_if, 0)
    # CAREFUL : Special case for sinks : what we removed is what is now missing.
    removed = before - {e.get("name") for e in self.transients_if.filter_by_component(self.remover.component_spec()[1])}
    return DiffTuple(added=added, removed=removed)


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
            try:
                s.configure(self.__entity_mgr)
            except:
                logging.exception("calling configure on {s} FAILED !".format(**locals()))


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
            try:
                s.loop(self.__entity_mgr, time_delta)
            except:
                logging.exception("calling loop on {s} FAILED !".format(**locals()))

        return time_delta
