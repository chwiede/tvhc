#!/usr/bin/env python

import re
import sys
import shutil
import argparse
from argparse import RawTextHelpFormatter
from datetime import datetime, timedelta
from tvhc.htspclient import *

# Defaults
FORMAT_REC = "{id:>6}: {startdate} - {title} ({length})"
FORMAT_CHN = "{id:>12}: {channelNumber:>4} - {channelName} ({type})"


# Setup praser. see http://pymotw.com/2/argparse/ for details.
parser = argparse.ArgumentParser(formatter_class = RawTextHelpFormatter)


# define parser arguments
parser.add_argument('--machine', '-m', type = str, 
                    default = 'localhost:9982', 
                    help = 'Specifies the machine. Default is "localhost:9982"')

parser.add_argument('--query', '-q', type = str, action = 'append',
                    help = 'One or more queries like "field:value". String values are compared by regex. Use < for lower, > for greater and +/- for relative time deltas.')

parser.add_argument('--type', '-t', type = str,
                    default = 'rec', choices = ['rec', 'chn'],
                    help = 'Defines type of item to work with. Available are [rec, chn]. Default is "rec".')

parser.add_argument('--format', '-f', type = str,
                    default = None,
                    help = 'Defines printformat for found items. Format is described in python docs for string.format(). Available Templates are "full" or "json".')

parser.add_argument('--delete', action='store_true', 
                    default = False,
                    help = 'Deletes found items.') 
                    
parser.add_argument('--noconfirm', action='store_true', 
                    default = False,
                    help = 'Delete will be performed without interactive question.')

parser.add_argument('--wakeup', action='store_true',
                    default = False,
                    help = 'Plans to wake up for next record via RTC.') 
                    
                    
#parser.add_argument('--print', '-p', action = 'store', default = None, choices = ['rec'], help = 'prints a list of items.')
#parser.add_argument('--remove', '-r', action = 'store', default = None, choices = ['rec'], help = "removes an item. Use with --id.")
#parser.add_argument('--id', action = 'store', default = None, help = 'specifies the id of an item.')

parser.add_argument('--version', action='version', version='%(prog)s 1.0')

parser.description = ('A simple client for tvheadend. You can query for channels or records '
                      'and print custom formatted lists of found items. '
                      'You also can delete found items.')

parser.epilog = ('Examples:\n\n'
                 
                 'tvhc\n'
                 'Shows an overview of the tvheadend-server on localhost.\n\n'
                 
                 'tvhc -m hostname\n'
                 'Shows an overview of the tvheadend-server on host "hostname".\n\n'
                 
                 'tvhc -q all -f json'
                 'Lists all records in json-format.\n\n'

                 'tvhc -q "startdate:<-30d" -q "title:house"\n'
                 'Lists all records older than 30 days and with a title matching the regex-pattern "house".\n\n'

                 'tvhc -q "startdate:<-30d" -q "title:house" --delete\n'
                 'Delete all records older than 30 days and with a title matching the regex-pattern "house".\n\n'

                 'tvhc -q all -t chn -f "{channelName:<30}{type}"\n'
                 'Lists all channels with a specific format, showing channel name and type.\n\n'
                 )

# parse args
args = parser.parse_args()


# define fieldtypes
fieldtypes = {
    'rec.id': int,
    'rec.start': int,
    'rec.stop': int,
    'rec.duration': int,
    'rec.startdate': datetime,
}


def print_overview(client):
    print("Machine:       %s:%s" % (host, port))
    print("Servername:    %s" % client.servername)
    print("Serverversion: %s" % client.serverversion)
    print("Capabilities:  %s" % client.capabilities)
    print("Channels:      %s" % len(client.channels))
    print("Records:       %s" % len(client.records))
    print("Tags:          %s" % len(client.tags))
    


def parse_hostport(machine):
    if ":" in args.machine:
        return args.machine.split(":")
    else:
        return (args.machine, 9982)
    


def get_records(client):
    result = client.records.copy()
    for rec in result.values():
        rec['channelname'] = client.channels[rec['channel']]['channelName']
        rec['startdate'] = datetime.fromtimestamp(rec['start'])
        rec['duration'] = rec['stop'] - rec['start']
        rec['length'] = timedelta(seconds = rec['stop'] - rec['start'])

    return sorted(result.values(), key=lambda rec: rec['start'])    

    

def get_channels(client):
    result = client.channels.copy()
    for chn in result.values():
        chn['id'] = chn['channelId']
        
        if chn['services'] != None and len(chn['services']) > 0:
            chn['type'] = chn['services'][0]['type']
        else:
            chn['type'] = "?"

    return sorted(result.values(), key=lambda chn: chn['channelNumber'])

    

def get_items_of(client, type):
    if type == 'rec':
        return get_records(client)
    elif type == 'chn':
        return get_channels(client)      
    else:
        raise Exception("type %s is not supported." % type)
    


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
    


def get_is_fieldmatch(item, type, field, pattern):
    typekey = "%s.%s" % (type, field)
    
    if fieldtypes.get(typekey, None) == int:
        return get_int_match(item[field], pattern)
    
    elif fieldtypes.get(typekey, None) == datetime:
        return get_date_match(item[field], pattern)
    
    else:
        match = re.search(pattern, item[field], re.IGNORECASE)
        return match != None
    
    # fallback
    return False 
    


def get_is_match(item, type, query):
    if len(query) == 1 and query[0] == "all":
        return True    
    
    for flt in query:
        if not ':' in flt:
            return False
        
        field, pattern = flt.split(':', 1)
        if not get_is_fieldmatch(item, type, field, pattern):
            return False

    return True



def find_by_args(client, type, query):
    result = []
    
    if type == 'rec' and query[0] == "next":
        result.append(get_next_record(client))
    
    items = get_items_of(client, type)
    for item in items:
        is_match = get_is_match(item, type, query)  
        if is_match:
            result.append(item)   
    
    return result



def get_print_format(args_format):
    format = args_format
    
    if format == None and args.type == 'rec':
        format = FORMAT_REC
    elif format == None and args.type == 'chn':
        format = FORMAT_CHN    

    return format



def print_items(format, items, type):
    for item in items:
        try:
            if format == 'json':
                print(item)
                print("")
                
            elif format == 'full':
                keys = sorted(item.keys())
                
                if type == 'rec' and 'description' in keys:
                    keys.remove('description')
                    keys.append('description')
                    
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
            return False

    # success
    return True



def delete_items(client, items, noconfirm, type):
    question = '\nDelete %s %s-items? Enter "yes" or "no": ' % (len(items), type)
    if noconfirm or input(question).lower() == 'yes':
        if type == 'rec':        
            for item in items:
                x = client.delete_record(item['id'])
                print("DEL ANSWER: %s" % x)
        
        print("%s items deleted." % len(items))
    else:
        print("Abort - nothing deleted.")




def get_next_record(client):
    now = time.time()
    records = get_records(client)
    records = sorted(records, key=lambda rec: rec['start'])
    for rec in records:
        if float(rec['start']) > now:
            return rec

    return None


# get host and port
host, port = parse_hostport(args.machine)

    
# create client and open connection
with HtspClient() as client:
    if not client.open(host, port):
        print('could not connect to "%s:%s" - Giving up.' % (host, port))
        sys.exit(1)

    # print overview, if no search arguments
    if args.query == None:
        print_overview(client)    
    
    # search arguments are given.
    else:
        # search items.
        items = find_by_args(client, args.type, args.query)
        
        # get format
        format = get_print_format(args.format)
                
        # print items
        proceed = print_items(format, items, args.type)
        
        # should items be deleted?
        if len(items) > 0 and proceed and args.delete:
            success = delete_items(client, items, args.noconfirm, args.type)
            
