from __future__ import absolute_import
from __future__ import print_function

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from pyros.mockinterface import MockInterface
from pyros.mockinterface.mockservice import statusecho_service, MockService
from pyros.mockinterface.mocksystem import mock_service_remote, mock_topic_remote, mock_param_remote


import nose
from nose.tools import timed, assert_true, assert_false, assert_equal, assert_raises


# @nose.SkipTest  # to help debugging ( FIXME : how to programmatically start only one test - maybe in fixture - ? )
@timed(5)  # this doesnt break if  hanging forever. need to replace with a breaking version
def test_mockinterface_update_services_c1():
    svc_name = '/awesome_service'
    mockif = MockInterface()

    assert_true(len(mockif.services_if.transients_if.index_by_component("name")) == 0)  # service not exposed yet
    diffupdate = mockif.update_services()
    assert_false(diffupdate.added)  # service not detected cannot be added
    assert_false(diffupdate.removed)

    diffupdate = mockif.update_services()
    assert_false(diffupdate.added)
    assert_false(diffupdate.removed)  # service not added cannot be removed

    with mock_service_remote(svc_name, statusecho_service):  # service appearing on mock system (another python process)
        mockif.services_args.add(svc_name)  # adding it to regex list to allow it to be exposed

        # TODO : change this to use context managers...
        # detect what changed
        detected = mockif.services_change_detect()
        assert_true(len(detected.added) == 1 and svc_name in detected.added)
        assert_true(len(detected.removed) == 0)

        # compute diff of what we need to update
        diff = mockif.services_change_diff()
        assert_true(len(diff.added) == 1 and svc_name in diff.added)
        assert_true(len(diff.removed) == 0)

        mockif.resolve_services()

        # do the update
        diffupdate = mockif.update_services()
        assert_false(diffupdate.removed)
        assert_true(diffupdate.added)  # service exposed can be added

        indexed_services = mockif.services_if.transients_if.index_by_component("name")
        assert_true(svc_name in indexed_services)
        assert_true(isinstance(indexed_services[svc_name].get("tif"), MockService))  # service type is MockService

    # detect what changed
    detected = mockif.services_change_detect()
    assert_true(len(detected.removed) == 1 and svc_name in detected.removed)
    assert_true(len(detected.added) == 0)

    # compute diff of what we need to update
    diff = mockif.services_change_diff()
    assert_true(len(diff.removed) == 1 and svc_name in diff.removed)
    assert_true(len(diff.added) == 0)

    diffupdate = mockif.update_services()
    assert_false(diffupdate.added)
    assert_true(diffupdate.removed)  # service exposed can be deleted

    assert_true(mockif.services.get(svc_name) is None)  # service not exposed anymore


# @nose.SkipTest  # to help debugging ( FIXME : how to programmatically start only one test - maybe in fixture - ? )
@timed(5)
def test_mockinterface_update_services_c2():
    svc_name = '/awesome_service'
    mockif = MockInterface()

    assert_true(len(mockif.services_if.transients_if.index_by_component("name")) == 0)  # service not exposed yet
    diffupdate = mockif.update_services()
    assert_false(diffupdate.added)  # service not detected cannot be added
    assert_false(diffupdate.removed)

    diffupdate = mockif.update_services()
    assert_false(diffupdate.added)
    assert_false(diffupdate.removed)  # service not added cannot be removed

    with mockif.services_if.mock_detection(mockif.services_if.transients_if, svc_name, statusecho_service):  # simulating service appearing
        mockif.services_args.add(svc_name)  # adding it to regex list to allow it to be exposed

        diffupdate = mockif.update_services()
        assert_false(diffupdate.removed)
        assert_true(diffupdate.added)  # service exposed can be added

        svc = mockif.services.get(svc_name)
        assert_true(svc is not None)  # service exposed now
        assert_true(isinstance(svc, MockService))  # service type is MockService

    svc = mockif.services.get(svc_name)
    assert_true(svc is not None)  # service is still exposed even though it s gone from the system we interface to
    # WARNING : Using the service in this state will trigger errors.
    # These should be handled by the service class.
    # TODO : assert this

    diffupdate = mockif.update_services()
    assert_false(diffupdate.added)
    assert_true(diffupdate.removed)  # service non available (but added) can be deleted

    assert_true(mockif.services.get(svc_name) is None)  # service not exposed


# @nose.SkipTest  # to help debugging ( FIXME : how to programmatically start only one test - maybe in fixture - ? )
@timed(5)
def test_mockinterface_expose_update_services_fullname():
    svc_name = '/awesome_service'
    mockif = MockInterface()

    assert_true(len(mockif.services_if.transients_if.index_by_component("name")) == 0)  # service not exposed yet
    diffupdate = mockif.expose_services([svc_name])
    assert_false(diffupdate.added)  # service not detected cannot be added
    assert_false(diffupdate.removed)

    with mockif.services_if.mock_detection(mockif.services_if.transients_if, svc_name, statusecho_service):

        diffupdate = mockif.expose_services([svc_name])
        assert_false(diffupdate.removed)
        assert_true(diffupdate.added)  # service available can be detected and be added

        svc = mockif.services.get(svc_name)
        assert_true(svc is not None)  # service exposed now
        assert_true(isinstance(svc, MockService))  # service type is MockService

    svc = mockif.services.get(svc_name)
    assert_true(svc is not None)  # service exposed now
    assert_true(isinstance(svc, MockService))  # service type is MockService

    # WARNING : Using the service in this state will trigger errors.
    # These should be handled by the service class.
    # TODO : assert this

    diffupdate = mockif.services_change_detect()
    assert_false(diffupdate.added)
    assert_true(diffupdate.removed)  # service lost can be detected and be removed

    assert_true(mockif.services.get(svc_name) is None)  # service not exposed anymore

    diffupdate = mockif.expose_services([svc_name])
    assert_false(diffupdate.removed)
    assert_false(diffupdate.added)  # new expose call doesn't change anything

    assert_true(mockif.services.get(svc_name) is None)  # service not exposed anymore


# @nose.SkipTest  # to help debugging ( FIXME : how to programmatically start only one test - maybe in fixture - ? )
@timed(5)
def test_mockinterface_update_expose_services_fullname():
    svc_name = '/awesome_service'
    mockif = MockInterface()

    diffupdate = mockif.services_change_detect()
    assert_false(diffupdate.added)  # service not available is not detected and not added
    assert_false(diffupdate.removed)  # service not added previously is not removed

    with mockif.services_if.mock_detection(mockif.services_if.transients_if, svc_name) as s:

        diffupdate = mockif.services_change_detect()
        assert_false(diffupdate.removed)
        assert_false(diffupdate.added)  # service available is not detected and added without previous expose call

        assert_true(len(mockif.services_if.transients_if.index_by_component("name")) == 0)  # service not exposed yet

        diffupdate = mockif.expose_services([svc_name])
        assert_false(diffupdate.removed)
        assert_true(diffupdate.added)  # new expose call add the service because it is already available

        svc = mockif.services.get(svc_name)
        assert_true(svc is not None)  # service exposed now
        assert_true(isinstance(svc, MockService))  # service type is MockService

        diffupdate = mockif.services_change_detect()
        assert_false(diffupdate.removed)
        assert_false(diffupdate.added)  # new detection call doesnt change anything

        svc = mockif.services.get(svc_name)
        assert_true(svc is not None)  # service still exposed
        assert_true(isinstance(svc, MockService))  # service type is still MockService

        diffupdate = mockif.expose_services([])
        assert_false(diffupdate.added)
        assert_true(diffupdate.removed)  # new expose call can remove the service even if it is still available

        assert_true(mockif.services.get(svc_name) is None)  # service not exposed anymore

        diffupdate = mockif.expose_services([svc_name])
        assert_false(diffupdate.removed)
        assert_true(diffupdate.added)  # new expose call can readd if it is still available

    svc = mockif.services.get(svc_name)
    assert_true(svc is not None)  # service exposed now
    assert_true(isinstance(svc, MockService))  # service type is MockService

    # WARNING : Using the service in this state will trigger errors.
    # These should be handled by the service class.
    # TODO : assert this

    diffupdate = mockif.expose_services([])
    assert_false(diffupdate.added)
    assert_true(diffupdate.removed)  # new expose call can remove the service even if it is not available

    assert_true(mockif.services.get(svc_name) is None)  # service not exposed anymore

    diffupdate = mockif.services_change_detect()
    assert_false(diffupdate.added)  # no appeared service : nothing is added
    assert_false(diffupdate.removed)  # disappeared service was already removed

    assert_true(mockif.services.get(svc_name) is None)  # service not exposed anymore


# @nose.SkipTest  # to help debugging ( FIXME : how to programmatically start only one test - maybe in fixture - ? )
@timed(5)
def test_mockinterface_expose_services_regex():
    svc_name = '/awesome_service'
    svc_regex = '/.*'
    mockif = MockInterface()

    assert_true(len(mockif.services_if.transients_if.index_by_component("name")) == 0)  # service not exposed yet
    diffupdate = mockif.expose_services([svc_regex])
    assert_false(diffupdate.added)  # service not detected cannot be added
    assert_false(diffupdate.removed)

    with mockif.services_if.mock_detection(mockif.services_if.transients_if, svc_name, statusecho_service):

        diffupdate = mockif.services_change_detect()
        assert_false(diffupdate.removed)
        assert_true(diffupdate.added)  # new detection call finds the service and adds it

        svc = mockif.services.get(svc_name)
        assert_true(svc is not None)  # service exposed
        assert_true(isinstance(svc, MockService))  # service type is MockService

    diffupdate = mockif.services_change_detect()
    assert_false(diffupdate.added)
    assert_true(diffupdate.removed)  # new detection call finds the service and removes it

    assert_true(mockif.services.get(svc_name) is None)  # service not exposed anymore


# @nose.SkipTest  # to help debugging ( FIXME : how to programmatically start only one test - maybe in fixture - ? )
@timed(5)
def test_mockinterface_update_expose_services_fullname_diff():
    svc_name = '/awesome_service'
    mockif = MockInterface()

    diffupdate = mockif.services_change_diff()
    assert_false(diffupdate.added)  # service not passed in diff is not detected and not added
    assert_false(diffupdate.removed)  # service not added previously is not removed

    with mockif.services_if.mock_detection(mockif.services_if.transients_if, svc_name, statusecho_service):

        diffupdate = mockif.services_change_diff()
        assert_false(diffupdate.removed)
        assert_false(diffupdate.added)  # service available is not detected and added without previous expose call

        assert_true(len(mockif.services_if.transients_if.index_by_component("name")) == 0)  # service not exposed yet

        diffupdate = mockif.expose_services([svc_name])
        assert_false(diffupdate.removed)
        assert_true(diffupdate.added)  # new expose call add the service because it is already available

        svc = mockif.services.get(svc_name)
        assert_true(svc is not None)  # service exposed now
        assert_true(isinstance(svc, MockService))  # service type is MockService

        diffupdate = mockif.services_change_diff()
        assert_false(diffupdate.removed)
        assert_false(diffupdate.added)  # empty diff call doesnt change anything

        svc = mockif.services.get(svc_name)
        assert_true(svc is not None)  # service still exposed
        assert_true(isinstance(svc, MockService))  # service type is still MockService

        diffupdate = mockif.expose_services([])
        assert_false(diffupdate.added)
        assert_true(diffupdate.removed)  # new expose call can remove the service even if it is still available

        assert_true(mockif.services.get(svc_name) is None)  # service not exposed anymore

        diffupdate = mockif.expose_services([svc_name])
        assert_false(diffupdate.removed)
        assert_true(diffupdate.added)  # new expose call can readd if it is still available

    svc = mockif.services.get(svc_name)
    assert_true(svc is not None)  # service exposed now
    assert_true(isinstance(svc, MockService))  # service type is MockService

    # WARNING : Using the service in this state will trigger errors.
    # These should be handled by the service class.
    # TODO : assert this

    diffupdate = mockif.expose_services([])
    assert_false(diffupdate.added)
    assert_true(diffupdate.removed)  # new expose call can remove the service even if it is not available

    assert_true(mockif.services.get(svc_name) is None)  # service not exposed anymore

    diffupdate = mockif.services_change_diff()
    assert_false(diffupdate.added)  # no service passed in diff : nothing is added
    assert_false(diffupdate.removed)  # disappeared service was already removed

    assert_true(mockif.services.get(svc_name) is None)  # service not exposed anymore


# @nose.SkipTest  # to help debugging ( FIXME : how to programmatically start only one test - maybe in fixture - ? )
@timed(5)
def test_mockinterface_expose_services_regex_diff():
    svc_name = '/awesome_service'
    svc_regex = '/.*'
    mockif = MockInterface()

    assert_true(len(mockif.services_if.transients_if.index_by_component("name")) == 0)  # service not exposed yet
    diffupdate = mockif.expose_services([svc_regex])
    assert_false(diffupdate.added)  # service not detected cannot be added
    assert_false(diffupdate.removed)

    with mockif.services_if.mock_detection(mockif.services_if.transients_if, svc_name, statusecho_service):

        diffupdate = mockif.services_change_diff()
        assert_false(diffupdate.removed)
        assert_true(diffupdate.added)  # new diff call finds the service and adds it

        indexed_services = mockif.services_if.transients_if.index_by_component("name")
        assert_true(svc_name in indexed_services)
        assert_true(isinstance(indexed_services[svc_name].get("tif"), MockService))  # service type is MockService

    diffupdate = mockif.services_change_diff()
    assert_false(diffupdate.added)
    assert_true(diffupdate.removed)  # new diff call finds the service and removes it

    assert_true(mockif.services.get(svc_name) is None)  # service not exposed anymore

#TODO : test exception raised properly when update transient cannot happen


# TODO : Same for topics and params

if __name__ == '__main__':

    import nose
    nose.runmodule()




