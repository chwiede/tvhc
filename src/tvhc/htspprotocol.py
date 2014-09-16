#!/usr/bin/env python

import struct
import hashlib

class HtspProtocol(object):

    HTSP_VERSION = 6
    
    HTSP_FIELD_MAP = 1
    HTSP_FIELD_S64 = 2
    HTSP_FIELD_STR = 3
    HTSP_FIELD_BIN = 4
    HTSP_FIELD_LST = 5



    def htsp_digest(self, user, passwd, challenge):
        result = hashlib.sha1(passwd + challenge).digest()
        return result        
  
        
    
    def int_to_s64(self, value):
        if value < 0:
            return value.to_bytes(8, byteorder='little', signed=True)
        
        
        for i in range(1,8):
            if value < 2**(8*i):
                return value.to_bytes(i, byteorder='little')    
    
    
    def s64_to_int(self, value):
        return int.from_bytes(value, byteorder='little', signed=True)
    
    
    
    def guess_fieldtype(self, value):
        if type(value) == int:
            return self.HTSP_FIELD_S64
        
        elif type(value) == str:
            return self.HTSP_FIELD_STR       
            
        elif type(value) == bin:
            raise Exception('invalid type')
            return self.HTSP_FIELD_BIN
        
        elif type(value) == list:
            raise Exception('invalid type')
            return self.HTSP_FIELD_MAP
        
        elif type(value) == dict:
            raise Exception('invalid type')
            return self.HTSP_FIELD_LIST
        
        else:
            raise Exception('invalid type')
    
    
    
    def serialize_value(self, value):
        if type(value) == int:
            return self.int_to_s64(value)
    
        if type(value) == str:
            return value.encode('utf8')
        
        else:
            raise Exception('invalid type')    
    
    
    
    def serialize_field(self, name, value):
        fieldtype = self.guess_fieldtype(value)
        binary = self.serialize_value(value)
        
        result = b''
        result += struct.pack('>b', fieldtype)
        result += struct.pack('>b', len(name))
        result += struct.pack('>i', len(binary))
        result += name.encode('utf8')
        result += binary
    
        return result
    
    
    
    def serialize(self, message):
        binary = b''
        for key in message:
            binary += self.serialize_field(key, message[key])
            
        result = struct.pack('>i', len(binary)) + binary
        return result
    
    
    
    def recv(self, socket):
        # read header - it defines total count of chars to read
        header = socket.recv(4)
        msglen = struct.unpack('>i', header)[0]
        
        # read this amount of chars
        message = socket.recv(msglen)
        
        # return    
        return self.deserialize(message)
    
    
    
    def deserialize_field(self, message, offset):
        data_type = struct.unpack_from('>b', message, offset + 0)[0]
        name_len = struct.unpack_from('>b', message, offset + 1)[0]
        data_len = struct.unpack_from('>i', message, offset + 2)[0]
        
        name_start = offset + 6
        data_start = offset + 6 + name_len
        
        name = message[name_start:name_start + name_len].decode("utf8")
        data = message[data_start:data_start + data_len]
        
        if data_type == self.HTSP_FIELD_MAP:
            data = self.deserialize(data, False)
    
        elif data_type == self.HTSP_FIELD_S64:
            data = self.s64_to_int(data)
    
        elif data_type == self.HTSP_FIELD_STR:
            data = data.decode("utf8")
    
        elif data_type == self.HTSP_FIELD_BIN:
            pass
    
        elif data_type == self.HTSP_FIELD_LST:
            data = self.deserialize(data, True)
    
        else:
            raise Exception('invalid type')
        
        return (name, data, 6 + name_len + data_len)
            
            
    
    def deserialize(self, message, as_list = False):
        result = {} if not as_list else []
        offset = 0
        
        while offset < len(message):
            field = self.deserialize_field(message, offset)
            offset = offset + field[2]
            
            if as_list:
                result.append(field[1])
            else:
                result[field[0]] = field[1]
    
        return result

