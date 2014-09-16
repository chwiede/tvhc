#!/usr/bin/env python

import sys
import asyncore
import socket
import threading
import time
from .htspprotocol import HtspProtocol
from .slock import SLock
    
class HtspSocket(asyncore.dispatcher):

    _received_handler = None
    
    messages = None
    protocol = None
    
    def __init__(self):
        asyncore.dispatcher.__init__(self)
        self.messages = []
        self.create_protocol()
        self._received_handler = self.received
    
    
    def set_received_handler(self, handler):
        self._received_handler = handler
    
    
    def create_protocol(self):
        self.protocol = HtspProtocol()

    
    def open(self, host, port):
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))
        self._asyncore_run()
    
    
    def close(self):
        self._asyncore_stop()
        
        
    def received(self, message):
        pass
    
    
    _msg_condition = threading.Condition()
    _send_lock1 = SLock(5.0)
    _recv_lock1 = SLock(5.0)
    
    
    def send_recv(self, message):
        # just wait for recv-actions ready...
        with self._recv_lock1:
            pass
        
        # send data
        cv = threading.Condition()
        with self._send_lock1:
            self._asyncore_buffer = self.protocol.serialize(message)
            
            with self._msg_condition:
                while not self.messages:
                    if not self._msg_condition.wait(5):
                        raise RuntimeError("Did not receive any answer in 5 seconds. Giving up.")
        
        return self.messages.pop(0)

   
    
    # asyncore implementation
    # ===================================================

    _asyncore_buffer = ''
    _asyncore_thread = None
    
    
    def _asyncore_run(self):
        self._asyncore_thread = threading.Thread(target=asyncore.loop, kwargs = {'timeout':0.01})
        self._asyncore_thread.setDaemon(True)
        self._asyncore_thread.start()
    
    
    def _asyncore_stop(self):
        super(HtspSocket, self).close()
    
    
    def handle_connect(self):
        pass
    
    
    def handle_error(self):
        # close socket due to error
        self.close()
        pass


    def handle_close(self):
        pass
    

    _srvcallbacks = ['channelAdd',
                     'channelUpdate',
                     'channelDelete',
                     'tagAdd',
                     'tagUpdate',
                     'tagDelete',
                     'dvrEntryAdd',
                     'dvrEntryUpdate',
                     'dvrEntryDelete',
                     'eventAdd',
                     'eventUpdate',
                     'eventDelete',
                     'initialSyncCompleted',
                     'subscriptionStart',
                     'subscriptionStop',
                     'subscriptionSkip',
                     'subscriptionSpeed',
                     'subscriptionStatus',
                     'queueStatus',
                     'signalStatus',
                     'timeshiftStatus',
                     'muxpkt']
     
    
    def handle_read(self):
        with self._recv_lock1:
            data = self.protocol.recv(self)
            
            # callback message?
            if 'method' in data and data['method'] in self._srvcallbacks:
                self._received_handler(data)
            else:
                with self._msg_condition:
                    self.messages.append(data)
                    self._msg_condition.notify_all()
            
        

    def writable(self):
        return self._asyncore_buffer and len(self._asyncore_buffer) > 0


    def handle_write(self):
        #print("handle_write")
        sent = super(HtspSocket, self).send(self._asyncore_buffer)
        self._asyncore_buffer = self._asyncore_buffer[sent:]
            

        