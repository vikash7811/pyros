from __future__ import absolute_import
from __future__ import print_function

import logging
import re

import six
from . import service_excess, topic_excess, param_excess, Changed


def find_first_regex_match(key, regex_candidates):
    """
    Find the first regex that match with the key
    We also attach beginning of line and end of line characters to the given key.
    This, ensures that raw topics like /test do not match other topics containing
    the same string (e.g. /items/test would result in a regex match at char 7)
    :param key: a key to try to match against multiple regex
    :param match_candidates: a list of regexes to check if they match the key
    :return: the first candidate found
    >>> find_first_regex_match("/long/name",["something_else"])
    >>> find_first_regex_match("/long/name",["something_else", "/long/.*"])
    '/long/.*'
    >>> find_first_regex_match("/another/long/name",["something_else", "/long/.*"])
    """
    for cand in regex_candidates:
        try:
            pattern = re.compile('^' + cand + '$')
            if pattern.match(key):
                return cand
        except:
            logging.warn('[ros_interface] Ignoring invalid regex string "{0!s}"!'.format(cand))

    return None


@service_excess.register_system({"name", "changed", "desc"}, {"tif_cleaner"})
def service_remove_filter(entities, regex_args):
    """
    Add constructor/destructor functions to be called for each added/gone entity
    :param entity_mgr: the entity manager we work with
    :param time_delta: the time_delta since the last update
    :return: None
    >>> entities= EntityManager()
    >>> entities.create(name="test_gone_entity", changed=Changed.GONE, desc="filterable_entity")
    {'changed': 2, 'name': 'test_gone_entity', 'desc': 'filterable_entity'}
    >>> remove_filter(entities, regex_args=["test_.*"]))
    >>> entities.filter_by_component(["tif_cleaner"]) # doctest: +ELLIPSIS
    [{'tif_cleaner': <function <lambda> at 0x...>, 'name': 'test_gone_entity', 'desc': 'filterable_entity'}]
    """
    transients_gone = {e: v for e, v in entities.items() if v.get("changed") == Changed.GONE}

    lost_matches = {n: v for n, v in service_excess.entities.items() if find_first_regex_match(n, regex_args) is None}

    transients_gone.update(lost_matches)  # we stop interfacing with lost transient OR lost matches

    for t, v in six.iteritems(transients_gone):
        ###self.filtered_toremove(t)
        v["tif_cleaner"] = lambda tst: tst.cleanup()
        # we consume the changed indicator here to avoid confusion later on...
        v.pop("changed", None)  # optional : maybe nothing changed on that transient, but we just want to remove it.


@topic_excess.register_system({"name", "changed", "desc"}, {"tif_cleaner"})
def topic_remove_filter(entities, regex_args):
    """
    Add constructor/destructor functions to be called for each added/gone entity
    :param entity_mgr: the entity manager we work with
    :param time_delta: the time_delta since the last update
    :return: None
    >>> entities= EntityManager()
    >>> entities.create(name="test_gone_entity", changed=Changed.GONE, desc="filterable_entity")
    {'changed': 2, 'name': 'test_gone_entity', 'desc': 'filterable_entity'}
    >>> remove_filter(entities, regex_args=["test_.*"]))
    >>> entities.filter_by_component(["tif_cleaner"]) # doctest: +ELLIPSIS
    [{'tif_cleaner': <function <lambda> at 0x...>, 'name': 'test_gone_entity', 'desc': 'filterable_entity'}]
    """
    transients_gone = [e for e in entities if e.get("changed") == Changed.GONE]

    lost_matches = [n for n in topic_excess.entities.filter_by_component("name") if
                    find_first_regex_match(n.get("name"), regex_args) is None]
    to_remove = transients_gone + lost_matches  # we stop interfacing with lost transient OR lost matches

    for t in to_remove:
        ###self.filtered_toremove(t)
        t["tif_cleaner"] = lambda tst: tst.cleanup()
        # we consume the changed indicator here to avoid confusion later on...
        t.pop("changed",
              None)  # optional : maybe nothing changed on that transient, but we just want to remove it.


@param_excess.register_system({"name", "changed", "desc"}, {"tif_cleaner"})
def param_remove_filter(entities, regex_args):
    """
    Add constructor/destructor functions to be called for each added/gone entity
    :param entity_mgr: the entity manager we work with
    :param time_delta: the time_delta since the last update
    :return: None
    >>> entities= EntityManager()
    >>> entities.create(name="test_gone_entity", changed=Changed.GONE, desc="filterable_entity")
    {'changed': 2, 'name': 'test_gone_entity', 'desc': 'filterable_entity'}
    >>> remove_filter(entities, regex_args=["test_.*"]))
    >>> entities.filter_by_component(["tif_cleaner"]) # doctest: +ELLIPSIS
    [{'tif_cleaner': <function <lambda> at 0x...>, 'name': 'test_gone_entity', 'desc': 'filterable_entity'}]
    """
    transients_gone = [e for e in entities if e.get("changed") == Changed.GONE]

    lost_matches = [n for n in param_excess.entities.filter_by_component("name") if
                    find_first_regex_match(n.get("name"), regex_args) is None]
    to_remove = transients_gone + lost_matches  # we stop interfacing with lost transient OR lost matches

    for t in to_remove:
        ###self.filtered_toremove(t)
        t["tif_cleaner"] = lambda tst: tst.cleanup()
        # we consume the changed indicator here to avoid confusion later on...
        t.pop("changed",
              None)  # optional : maybe nothing changed on that transient, but we just want to remove it.


# class RemoveFilter(System):
#     """
#     this system determines which change of the system should actually trigger transient interface creation/deletion
#     ChangeFilter -> InterfaceAdder|InterfaceRemover
#     """
#
#     def __init__(self):
#         """
#         Initializes this System
#         """
#         super(RemoveFilter, self).__init__()
#
#     def component_spec(self):
#         """
#         :return: tuple of the set of component names that are manipulated by this system. input -> output
#         """
#         return {"name", "changed", "desc"}, {"name", "desc", "tif_cleaner"}
#
#     def configure(self, entity_mgr, regex_args, tif_cleaner):
#         """
#         Configure this System
#         :param entity_mgr: the entity manager we work with
#         :param regex_args: the regex arguments
#         :param tif_maker: the transient interface builder function
#         :param tif_cleaner: the transient interface cleaner function
#         :return: None
#         """
#         # TODO : make sure this is referenced and can be dynamically updated
#         self.regex_args = regex_args
#         self.tif_cleaner = tif_cleaner
#
#     def loop(self, entity_mgr, time_delta):
#         """
#         Add constructor/destructor functions to be called for each added/gone entity
#         :param entity_mgr: the entity manager we work with
#         :param time_delta: the time_delta since the last update
#         :return: None
#         >>> entities= EntityManager()
#         >>> entities.create(name="test_gone_entity", changed=Changed.GONE, desc="filterable_entity")
#         {'changed': 2, 'name': 'test_gone_entity', 'desc': 'filterable_entity'}
#         >>> s = RemoveFilter()
#         >>> s.configure(entities, regex_args=["test_.*"], tif_cleaner=(lambda n, t: print("cleaner({0},{1}".format(n,t))))
#         >>> s.loop(entities, 1)
#         >>> entities.filter_by_component(["tif_cleaner"]) # doctest: +ELLIPSIS
#         [{'tif_cleaner': <function <lambda> at 0x...>, 'name': 'test_gone_entity', 'desc': 'filterable_entity'}]
#         """
#         transients_gone = entity_mgr.filter_by_component(["name", "changed", "desc"], lambda t: t.get("changed") == Changed.GONE)
#
#         lost_matches = [n for n in entity_mgr.filter_by_component("name") if find_first_regex_match(n.get("name"), self.regex_args) is None]
#         to_remove = transients_gone + lost_matches  # we stop interfacing with lost transient OR lost matches
#
#         for t in to_remove:
#             self.filtered_toremove(t)
#
#     # TODO : simplify : have tif_cleaner stored early ( in case a transient is dropped without warning, because of error, etc.)
#     # These are useful to test this system effects on the entities
#     def filtered_toremove(self, t):
#         t["tif_cleaner"] = self.tif_cleaner
#         # we consume the changed indicator here to avoid confusion later on...
#         t.pop("changed", None)  # optional : maybe nothing changed on that transient, but we just want to remove it.
#
# System.register(RemoveFilter)