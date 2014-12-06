#!/usr/bin/env python

import socket
import threading
import logging
from tvhc import *

    
class HtspClient(object):
    
    # flags & member
    _user = None
    _passwd = None
    _version = "1.0"
    _challenge = b''    
    _initialized = False
    _socket = None
    _initcv = threading.Condition()
    
    
    # data properties
    records = {}    
    channels = {}
    tags = {}
        
    
    def __init__(self, name='pyhtsp'):
        self.name = name
        self._socket = HtspSocket()
        self._socket.set_received_handler(self._received)
        


    def try_open(self, host='localhost', user=None, passwd=None, port=9982):
        try:
            self.open(host, user, passwd, port)
            return True
        except:
            return False
    
    
    def open(self, host='localhost', user=None, passwd=None, port=9982):

        # set member variables
        self.host = host
        self.port = port
        
        # connect & init routine
        self._socket.open(host, port)
        self.hello()
            
        self.authenticate(user, passwd)
        self.enable_async_metadata()
        
        # wait for init
        with self._initcv:
            if not self._initialized:
                self._initcv.wait(5)
                if not self._initialized:
                    raise Exception("could not initialize :-(")
        

    def _received(self, msg):
        mkey = 'method'        
        if mkey in msg:
            method = msg.pop(mkey)
        
            if hasattr(self, method):
                self.__getattribute__(method)(msg)
            else:
                logging.warning("method %s not found." % method)

        else:
            print("unkown message received: %s" % msg)


    def channelAdd(self, msg):
        id = msg['channelId']
        self.channels[id] = msg


    def channelUpdate(self, msg):
        id = msg['channelId']
        self.channels[id] = msg
    
    
    def dvrEntryAdd(self, msg):
        id = msg['id']
        self.records[id] = msg



    def dvrEntryDelete(self, msg):
        id = msg['id']
        if id in self.records:
            del self.records[id]
        

    def tagAdd(self, msg):
        id = msg['tagId']
        self.tags[id] = msg


    def tagUpdate(self, msg):
        id = msg['tagId']
        for k, v in msg.items():
            self.tags[id][k] = v


    def initialSyncCompleted(self, msg):
        with self._initcv:
            self._initialized = True
            self._initcv.notify()



    def get_clientname(self):
        return "%s-%s" % (socket.gethostname(), self.name)
    
    
    
    def get_version(self):
        return self._version
    
    
    
    def send_recv(self, method, args):
        if not isinstance(args, dict):
            args = {}
    
        args['method'] = method
        return self._socket.send_recv(args)
    


    def hello(self):
        args = {
            'htspversion': self._socket.protocol.HTSP_VERSION,
            'clientname': self.get_clientname(),
            'clientversion': self.get_version()
        }        
        result = self.send_recv('hello', args)
        
        self._challenge = result['challenge']
        self.servername = result['servername']
        self.serverversion = result['serverversion']
        self.capabilities = result['servercapability']
        return result
    


    def authenticate(self, user=None, passwd=None):
        if user:
            self._user = user
        
        if passwd:
            self._passwd = self.protocol.htsp_digest(self._user, self._passwd, self._challenge)
        
        return self.send_recv('authenticate', {})
    
    
    
    def get_disk_space(self):
        return self.send_recv('getDiskSpace', {})
    
    
    
    def get_sys_time(self):
        return self.send_recv('getSysTime', {})

    
    
    def enable_async_metadata(self):
        return self.send_recv('enableAsyncMetadata', {})



    def delete_record(self, recordId):
        return self.send_recv('deleteDvrEntry', {
            'id': recordId
        })
        

    def close(self):
        if self._socket != None:
            self._socket.close()
        
        self.records.clear()
        self.channels.clear()

    
    # enter & exit for 'whith <type> as <var> syntax
    # ===================================================
    
    def __enter__(self):
        return self

    
    def __exit__(self, type, value, traceback):
        self._socket.close()
        
