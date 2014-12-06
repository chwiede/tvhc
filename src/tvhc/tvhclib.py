#!/usr/bin/env python

import re
import sys
import time
import argparse
from datetime import datetime, timedelta
from argparse import RawTextHelpFormatter


# define fieldtypes
fieldtypes = {'record': {'id': int,
                         'start': int,
                         'stop': int,
                         'duration': int,
                         'startdate': datetime 
                         }
              }


# define formats
formats = {'record': '{id:>6}: {startdate} {shortstate} {title} ({length})'}


# define short states
shortstates = {'completed': '-',
               'scheduled': '+',
               'recording': '>',
               'missed': 'X',
               'failed': 'X'}


def open_fail(exit):
    print("Could not establish connection...")
    
    if exit:
        sys.exit(1)    



def ask_for_delete(count, type):
    question = '\nDelete %s %s items? Enter "yes" or "no": ' % (count, type)
    return input(question).lower() == 'yes'    

    

def extend_record(client, record):
    rec = record.copy()
    rec['channelname'] = client.channels[rec['channel']]['channelName']
    rec['startdate'] = datetime.fromtimestamp(rec['start'])
    rec['duration'] = rec['stop'] - rec['start']
    rec['length'] = timedelta(seconds=rec['stop'] - rec['start'])
    rec['shortstate'] = shortstates.get(rec['state'], rec['state'])
    return rec
    
    

def get_next_record(client, relatime=time.time()):
    records = client.records.values()
    records = sorted(records, key=lambda rec: rec['start'])    
    for rec in records:
        if float(rec['start']) > time.time():
            return rec
    
    return None
    

def get_active_records(client):
    records = client.records.values()
    for rec in records:
        if rec['state'] == 'recording':
            yield rec


def search_items(items, fieldtypes, queries):
    for item in items:
        if queries == None or get_is_match(item, fieldtypes, queries):
            yield item



def get_is_match(item, fieldtypes, queries):
    if queries and queries[0] == "all":
        return True    
    
    for query in queries:
        if not ':' in query:
            return False
        
        field, pattern = query.split(':', 1)
        if not get_is_fieldmatch(item, fieldtypes, field, pattern):
            return False

    return True



def get_is_fieldmatch(item, fieldtypes, field, pattern):
    if fieldtypes.get(field, None) == int:
        return get_int_match(item[field], pattern)
    
    elif fieldtypes.get(field, None) == datetime:
        return get_date_match(item[field], pattern)
    
    else:
        match = re.search(pattern, item[field], re.IGNORECASE)
        return match != None
    


def get_int_match(value, pattern):
    if pattern[0] == ">":
        return value > int(pattern[1:])
    elif pattern[0] == "<":
        return value < int(pattern[1:])
    else:
        return value == int(pattern)



def repl_daterel(match):
    timedeltas = {
        'm': timedelta(seconds=60),
        'h': timedelta(hours=1),
        'd': timedelta(days=1),
        'w': timedelta(weeks=1),
        'y': timedelta(days=365)
    }
    
    delta = timedeltas[match.group(2)]
    count = int(match.group(1))
    date = datetime.now() + delta * count
    return date.strftime('%Y-%m-%d %H:%M:%S')
    


def get_date_match(value, pattern):
    # replace relative definition to real date
    pattern = re.sub(r'([+-]\d+)([mhdwy])', repl_daterel, pattern.lower())

    if pattern[0] == ">":
        date = datetime.strptime(pattern[1:], '%Y-%m-%d %H:%M:%S') 
        return value > date
    elif pattern[0] == "<":
        date = datetime.strptime(pattern[1:], '%Y-%m-%d %H:%M:%S') 
        return value < date
    else:
        date = datetime.strptime(pattern[1:], '%Y-%m-%d %H:%M:%S') 
        return value == date

    return False



def get_wakedup(persistent_file, max_boot_time=300):
    timestamp = query_wake_timestamp(persistent_file)
    boot_time = time.time() - timestamp
    boot_time_ok = boot_time > 0 and boot_time < max_boot_time
    return boot_time_ok



def query_wake_timestamp(persistent_file):
    try:
        with open(persistent_file, 'r') as f:
            return int(f.readline().strip())
    
    except:
        return 0



def print_items(items, format):
    count = 0
    for item in items:
        count = count + 1
        try:
            if format == 'json':
                print(item)
                print("")
                
            elif format == 'full':
                keys = sorted(item.keys())
                
                for key in keys:
                    print('{0:<20}{1}'.format(key, item[key]))                    
                print("")
                
            else:
                print(format.format(**item))
                
        except KeyError:
            print("KeyError in format. Available fields are: ")
            for key in item:
                print("  " + key)
                
            # abort
            return False, count
        
    # no items?
    if count == 0:
        print("No items to print out.")

    # success
    return True, count



def get_default_host():
    return 'localhost:%s' % get_default_port()



def get_default_port():
    return 9982



def parse_host(host):
    if ':' in host:
        return host.split(':')[:2]
    else:
        return (host, get_default_port())



def create_parser(extend=None):
    # Add host argument. This is always available.
    parser = argparse.ArgumentParser()
    parser.add_argument("host", default=get_default_host(), nargs="?",
                        help='Defines the host to connect with. Default is "%s".' % get_default_host())
    
    if extend != None:
        extend(parser)
    
    return parser



def print_client_info(host, port, client):
    print("Machine:       %s:%s" % (host, port))
    print("Servername:    %s" % client.servername)
    print("Serverversion: %s" % client.serverversion)
    print("Capabilities:  %s" % client.capabilities)
    print("Channels:      %s" % len(client.channels))
    print("Records:       %s" % len(client.records))
    print("Tags:          %s" % len(client.tags))



def append_default_arguments(parser):
    parser.add_argument('--query', '-q', type = str, 
                        action = 'append',
                        help = 'One or more queries like "field:value". String values are compared by regex. Use < for lower, > for greater and +/- for relative time deltas.')
    
    parser.add_argument('--format', '-f', type = str,
                        default = None,
                        help = 'Defines print-format for found items. Format is described in python docs for string.format(). Available Templates are "full" or "json".')
    
    parser.add_argument('--noconfirm', action='store_true', 
                        default = False,
                        help = 'Delete will be performed without interactive question.')

