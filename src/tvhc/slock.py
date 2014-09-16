#!/usr/bin/env python

import sys
import threading

class SLock(object):
    
    _condition = threading.Condition()
    _timeout = None
    _locks = 0
    _thread_id = 0 
    
    def __init__(self, timeout = None):
        self._timeout = timeout
        self._locks = 0
        pass        


    def acquire(self):
        
        with self._condition:
            tid = threading.current_thread().ident
            
            if self._locks > 0 and tid != self._thread_id:
                self.waitfor()            
            
            self._thread_id = tid
            self._locks += 1
            
        
    
    def release(self):
        self._locks -= 1
        
        if(self._locks < 0):
            raise Exception("more releases than acquires??!")

        if self._locks == 0:
            with self._condition:
                self._condition.notify()        
        
    
    
    def __enter__(self):
        self.acquire()
        return self    

    
    def __exit__(self, type, value, traceback):
        self.release()        
        pass
    
    
    def waitfor(self, timeout = None):
        timeout = timeout if timeout != None else self._timeout
        
        with self._condition:
            while self._locks > 0:
                self._condition.wait(timeout)
                if self._locks > 0:
                    print(self._locks)
                    raise Exception("lock timeout")

