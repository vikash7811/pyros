from __future__ import absolute_import
from __future__ import print_function

import logging
import re

import six
from . import service_excess, topic_excess, param_excess, Changed


def regex_match_sublist(regex, match_candidates):
    """
    Filter the match_candidates list to return only the candidate that match the regex
    We also attach beginning of line and end of line characters to the given key.
    This, ensures that raw topics like /test do not match other topics containing
    the same string (e.g. /items/test would result in a regex match at char 7)
    :param regex: a regex used to filter the list of candidates
    :param match_candidates: the list of candidates
    :return: the filtered list of only the candidates that match the regex
    >>> regex_match_sublist("/long/.*",["something_else"])
    []
    >>> regex_match_sublist("/long/.*",["something_else", "/long/name"])
    ['/long/name']
    >>> regex_match_sublist("/long/.*",["something_else", "/another/long/name"])
    []
    """
    matches = []
    try:
        pattern = re.compile('^' + regex + '$')
        matches = [cand for cand in match_candidates if pattern.match(cand)]
    except:
        logging.warn('[ros_interface] Ignoring invalid regex string "{0!s}"!'.format(regex))
    return matches


def regexes_match_sublist(regexes, match_candidates):
    """
    Filter the match_candidates list to return only the candidate that match the regex
    :param regexes: a list of regex used to filter the list of candidates
    :param match_candidates: the list of candidates
    :return: the filtered list of only the candidates that match the regexes
    >>> regexes_match_sublist(["/long/.*"],["something_else"])
    []
    >>> regexes_match_sublist(["/long/.*"],["something_else", "/long/name"])
    ['/long/name']
    >>> regexes_match_sublist(["/long/.*",".*_we_want"],["something_else", "/long/name", "what_we_want"])
    ['/long/name', 'what_we_want']
    """

    #TODO : we should be able to improve this with iterators.
    return [match for sublist in [regex_match_sublist(rgx, match_candidates) for rgx in regexes] for match in sublist]



@service_excess.register_system({"name", "changed", "desc"}, {"tif_maker"})
def service_add_filter(entities, regex_args, tif_maker):
    """
    Add constructor/destructor functions to be called for each added/gone entity
    :param entities: the entities we work with
    :return: None
    >>> entities= EntityManager()
    >>> entities.create(name="test_added_entity", changed=Changed.APPEARED, desc="filterable_entity")
    {'changed': 1, 'name': 'test_added_entity', 'desc': 'filterable_entity'}
    >>> add_filter(entities, regex_args=["test_.*"]))
    >>> entities.filter_by_component(["tif_maker"]) # doctest: +ELLIPSIS
    [{'tif_maker': <function <lambda> at 0x...>, 'name': 'test_added_entity', 'desc': 'filterable_entity'}]
    """

    transients_appeared = {t: v for t, v in six.iteritems(entities) if v.get("changed") == Changed.APPEARED}
    to_add = {t: v for t, v in six.iteritems(transients_appeared) if
              t in regexes_match_sublist(regex_args, transients_appeared.keys())}

    # TODO : simplify : have tif created early (but what about type resolver ?)
    for t, v in six.iteritems(to_add):
        #### def filtered_toadd(self, t):
        v["tif_maker"] = tif_maker
        # we consume the changed indicator here to avoid confusion later on...
        v.pop("changed")


@topic_excess.register_system({"name", "changed", "desc"}, {"tif_maker"}, )
def topic_add_filter(entities, regex_args, tif_maker):
    """
    Add constructor/destructor functions to be called for each added/gone entity
    :param entities: the entities we work with
    :return: None
    >>> entities= EntityManager()
    >>> entities.create(name="test_added_entity", changed=Changed.APPEARED, desc="filterable_entity")
    {'changed': 1, 'name': 'test_added_entity', 'desc': 'filterable_entity'}
    >>> add_filter(entities, regex_args=["test_.*"])
    >>> entities.filter_by_component(["tif_maker"]) # doctest: +ELLIPSIS
    [{'tif_maker': <function <lambda> at 0x...>, 'name': 'test_added_entity', 'desc': 'filterable_entity'}]
    """

    transients_appeared = [t for t in entities if t.get("changed") == Changed.APPEARED]
    to_add = [t for t in transients_appeared if
              t.get("name") in regexes_match_sublist(regex_args, [t.get("name") for t in transients_appeared])]

    # TODO : simplify : have tif created early (but what about type resolver ?)
    for t in to_add:
        #### def filtered_toadd(self, t):
        t["tif_maker"] = tif_maker
        # we consume the changed indicator here to avoid confusion later on...
        t.pop("changed")


@param_excess.register_system({"name", "changed", "desc"}, {"tif_maker"}, )
def param_add_filter(entities, regex_args, tif_maker):
    """
    Add constructor/destructor functions to be called for each added/gone entity
    :param entities: the entities we work with
    :return: None
    >>> entities= EntityManager()
    >>> entities.create(name="test_added_entity", changed=Changed.APPEARED, desc="filterable_entity")
    {'changed': 1, 'name': 'test_added_entity', 'desc': 'filterable_entity'}
    >>> add_filter(entities, regex_args=["test_.*"]))
    >>> entities.filter_by_component(["tif_maker"]) # doctest: +ELLIPSIS
    [{'tif_maker': <function <lambda> at 0x...>, 'name': 'test_added_entity', 'desc': 'filterable_entity'}]
    """

    transients_appeared = [t for t in entities if t.get("changed") == Changed.APPEARED]
    to_add = [t for t in transients_appeared if
              t.get("name") in regexes_match_sublist(regex_args, [t.get("name") for t in transients_appeared])]

    # TODO : simplify : have tif created early (but what about type resolver ?)
    for t in to_add:
        #### def filtered_toadd(self, t):
        t["tif_maker"] = tif_maker
        # we consume the changed indicator here to avoid confusion later on...
        t.pop("changed")


#
# class AddFilter(System):
#     """
#     this system determines which change of the system should actually trigger transient interface creation/deletion
#     ChangeFilter -> InterfaceAdder|InterfaceRemover
#     """
#
#     def __init__(self):
#         """
#         Initializes this System
#         """
#         super(AddFilter, self).__init__()
#
#     def component_spec(self):
#         """
#         :return: tuple of the set of component names that are manipulated by this system. input -> output
#         """
#         return {"name", "changed", "desc"}, {"name", "desc", "tif_maker"}
#
#     def configure(self, entity_mgr, regex_args, tif_maker):
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
#         self.tif_maker = tif_maker
#
#     def loop(self, entity_mgr, time_delta):
#         """
#         Add constructor/destructor functions to be called for each added/gone entity
#         :param entity_mgr: the entity manager we work with
#         :param time_delta: the time_delta since the last update
#         :return: None
#         >>> entities= EntityManager()
#         >>> entities.create(name="test_added_entity", changed=Changed.APPEARED, desc="filterable_entity")
#         {'changed': 1, 'name': 'test_added_entity', 'desc': 'filterable_entity'}
#         >>> s = AddFilter()
#         >>> s.configure(entities, regex_args=["test_.*"], tif_maker=(lambda n, t: print("maker({0},{1}".format(n,t))))
#         >>> s.loop(entities, 1)
#         >>> entities.filter_by_component(["tif_maker"]) # doctest: +ELLIPSIS
#         [{'tif_maker': <function <lambda> at 0x...>, 'name': 'test_added_entity', 'desc': 'filterable_entity'}]
#         """
#         transients_changed = entity_mgr.filter_by_component(["name", "changed", "desc"])
#
#         transients_appeared = [t for t in transients_changed if t.get("changed") == Changed.APPEARED]
#         to_add = [t for t in transients_appeared if t.get("name") in regexes_match_sublist(self.regex_args, [t.get("name") for t in transients_appeared])]
#
#         # TODO : simplify : have tif created early (but what about type resolver ?)
#         for t in to_add:
#             self.filtered_toadd(t)
#
#     # These are useful to test this system effects on the entities
#     def filtered_toadd(self, t):
#         t["tif_maker"] = self.tif_maker
#         # we consume the changed indicator here to avoid confusion later on...
#         t.pop("changed")
#
#
# System.register(AddFilter)
