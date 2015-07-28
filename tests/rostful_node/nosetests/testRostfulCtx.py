from __future__ import absolute_import

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from rostful_node.rostful_ctx import RostfulCtx
from rostful_node.rostful_mock import RostfulMock
from rostful_node.rostful_client import RostfulClient

def testRostfulCtx():
    with RostfulCtx() as ctx:
        assert isinstance(ctx.node, RostfulMock) and isinstance(ctx.client, RostfulClient)

    # TODO : assert the context manager does his job ( HOW ? )
