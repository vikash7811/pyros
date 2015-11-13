# -*- coding: utf-8 -*-
# This python package is implementing a very simple multiprocess framework
# The point of it is to be able to fully tests the multiprocess behavior,
#     in pure python, without having to run a ROS system.
from __future__ import absolute_import

import multiprocessing, multiprocessing.reduction
import time
from collections import namedtuple
import zmq
import  pickle  # TODO : json, protobuf


### IMPORTANT : COMPOSITION -> A SET OF NODE SHOULD ALSO 'BE' A NODE ###
### IMPORTANT : IDENTITY
### Category Theory https://en.wikipedia.org/wiki/Category_theory

### Data Flow with topic :
#
# object : message
# arrow : topic_listener
# binary op - associativity : listener l1, l2, l3 <= (l1 . l2) .l3 == l1. (l2. l3)
# binary op - identity : noop on listener => msg transfer as is
# -> Expressed in programming language (functional programming follows category theory) :
# msg3 = topic2_listener(topic1_listener(msg1))

# -> Expressed in graph :
# msg3 <--topic2_listener-- msg2 <--topic1_listener-- msg1

### RPC with services :
#
# object : (req, resp)
# arrow : service_call
# binary op - associativity : service s1, s2, s3 <= (s1 . s2) .s3 == s1. (s2. s3)
# binary op - identity : noop on service => (req, resp) transfer as is ( two ways comm )
# -> Expressed in programming language (functional programming follows category theory) :
#  (req3, resp3) = service2_call(service1_call((req1, resp1)))

# -> Expressed in graph :
# msg1 --service1_call--> msg2 --service2_call--> msg3

###### higher level for execution graph to be represented by a category ######

### Service is a first class citizen. node is abstracted in that perspective : implementation requires some discovery mechanism.
# object : service
# arrow : call
# binary op - associativity : call c1, c2, c3 <= (c1 . c2) .c3 == c1 . (c2 . c3)
# binary op - identity : ??? TODO
# -> Expressed in programming language (functional programming follows category theory) :
#  svc1 = lambda x: return ( lambda y: return svc3(y) )( x )  <= currying/partial => svc1 = lambda x, y : return svc23(x,y)

# -> Expressed in graph :
# svc1 --call--> svc2 --call--> svc3

### Node is a first class citizen
# object : node
# arrow : topic_listener / callback
# binary op - associativity : callback cb1. cb2. cb3 <= (cb1 . cb2) . cb3 == cb1 . (cb2 . cb3)
# binary op - identity : ??? TODO
# -> Expressed in programming language (functional programming follows category theory) :
#  node1.cb = lambda x: return ( lambda y: return node3.cb(y) )(x) <= currying/partial => node1.cb = lambda x, y : return node23(x,y)

# -> Expressed in graph :
# node3 <--topic_cb-- node2 <--topic_cb-- node1


from . import services
from .service import Request, Response

current_node = multiprocessing.current_process


class UnknownServiceException(Exception):
    pass


class UnknownRequestTypeException(Exception):
    pass


class Node(multiprocessing.Process):

    def __init__(self, name='node'):
        # TODO check name unicity
        super(Node, self).__init__(name=name)
        self.exit = multiprocessing.Event()
        self.listeners = {}
        self._providers_endpoint = {}
        self._svc_address = "tcp://127.0.0.1:%s" % 4242

    def provides(self, svc_name, svc_callback):
        # TODO : multiple endpoint for one service ( can help in some specific cases )
        self._providers_endpoint[svc_name] = svc_callback

    def run(self):
        print 'Starting %s' % self.name

        zcontext = zmq.Context()  # check creating context in init ( compatilibty with multiple rpocesses )
        svc_socket = zcontext.socket(zmq.REP)
        svc_socket.bind(self._svc_address)

        poller = zmq.Poller()
        poller.register(svc_socket, zmq.POLLIN)

        # advertising services
        for svc_name, svc_callback in self._providers_endpoint.iteritems():
            print '-> Providing {0} with {1}'.format(svc_name, svc_callback)
            globalsvcs = services
            if svc_name in globalsvcs:
                globalsvcs[svc_name].append((self.name, self._svc_address))
            else:
                globalsvcs[svc_name] = [(self.name, self._svc_address)]


        # loop listening to connection
        while not self.exit.is_set():
            try:
                socks = dict(poller.poll(timeout=10))  # Note this timeout only determines the shutdown speed. messages are received ASAP.
                if svc_socket in socks and socks[svc_socket] == zmq.POLLIN:
                    req = pickle.loads(svc_socket.recv())
                    if isinstance(req, Request):
                        if req.service in self._providers_endpoint:
                            resp = self._providers_endpoint[req.service](req.request)
                            svc_socket.send(pickle.dumps(Response(service=req.service, response=resp)))
                        else:
                            raise UnknownServiceException("Unknown Service {0}".format())
                    else:
                        raise UnknownRequestTypeException("Unknown Request Type {0}".format(type(req)))

            except Exception, e:
                raise e
            time.sleep(0.1)  # avoid spinning too fast

        # deadvertising services
        for svc_name, svc_callback in self._providers_endpoint.iteritems():
             services[svc_name] = [(n, a) for (n, a) in services[svc_name] if n != self.name]

        print "You exited!"

    def shutdown(self, join=True):
        """
        Clean shutdown of the node.
        :param join: optionally wait for the process to end (default : True)
        :return: None
        """
        if self._popen is not None:  # check if process started
            print "Shutdown initiated"
            self.exit.set()
            if join:
                self.join()
            # TODO : timeout before forcing terminate (SIGTERM)
        pass

    def listen(self, topic, callback):

        # TODO actually open comm channels

        # find topic sender

        # build a pipe with sender

        # register the listener
        self.listeners[topic] = callback
        pass

    def unlisten(self, topic):
        #TODO : inverse of listen
        pass


