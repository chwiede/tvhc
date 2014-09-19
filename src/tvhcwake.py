#!/usr/bin/env python

import re
import os
import sys
import time
import tvhclib
from datetime import datetime, timedelta
from tvhc import *


default_ahead = 300
default_persistent = '/var/tmp/tvhc_wakeup'
default_device = '/sys/class/rtc/rtc0/wakealarm'



def clear_wake(persistent, device):
    for path in (persistent, device):
        with open(path, 'w') as f:
            f.write("0\n")


def set_wake(persistent, device, timestamp):
    # always clear wake before set!
    # should be done due to some mainboard implementations.
    clear_wake(persistent, device)
    
    for path in (persistent, device):
        with open(path, 'w') as f:
            f.write("%s\n" % int(timestamp))


def extend_parser(parser):
    parser.add_argument('--device', '-d', default=default_device, metavar="PATH",
                        help='Defines the RTC device. Default value is "%s"' % default_device)

    parser.add_argument('--persistent', '-p', default=default_persistent, metavar="PATH",
                        help='Defines the persistent file. Default value is "%s"' % default_persistent)
    
    parser.add_argument('--clear', '-c', action='store_true', default=False,
                        help='Clears wakeup on persistent and RTC device.')

    parser.add_argument('--time', '-t', type=str, default=None,
                        help='Manually define time to wakeup. No record will be searched. Give either timestamp or iso-datetime.')
    
    parser.add_argument('--ahead', '-a', type=int, default=-1,
                        help='Wakeup some seconds before. Default is 0 seconds if timestamp given, otherwise %s.' % default_ahead)

    parser.add_argument('--query', '-q', action='store_true', default=False,
                        help='Shows last known wakeup timestamp.')


def print_wake_set(timestamp, title=None):
    dt = datetime.fromtimestamp(timestamp).isoformat()

    if title != None and title != '':
        print('Wakeup set to %s for "%s".' % (dt, title))
    else:
        print('Wakeup set to %s.' % dt)    



def query(persistent):
    try:
        with open(args.persistent, 'r') as f:
            ts = int(f.readline().strip())
            return ts
    
    except:
        return None
    
    

if __name__ == '__main__':
    
    # parse arguments
    parser = tvhclib.create_parser(extend=extend_parser)
    args = parser.parse_args()
    
    # get host & port
    host, port = tvhclib.parse_host(args.host)
    
    # what's to do?
    if args.query:
        
        ts = query(args.persistent)
        if ts != None:
            now = time.time()
            dt = datetime.fromtimestamp(ts)
            
            word = 'was' if ts < now else 'is'
            delta = timedelta(seconds = int(abs(ts-now)))
            print("Found timestamp is %s" % ts)
            print('Wakeup %s planned for %s' % (word, dt.isoformat()))
            
            sign = "-" if ts < now else "+"
            print('Time delta is %s%s' % (sign, delta))

        else:
            print("No planned wakeup found.") 
    
    
    elif args.clear:
        clear_wake(args.persistent, args.device)
        print("Wakeup cleared.")
        
    elif args.time != None:
        
        if args.ahead == -1:
            args.ahead = 0
        
        if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$', args.time):
            dt = datetime.strptime(args.time, '%Y-%m-%dT%H:%M:%S')
            timestamp = dt.timestamp()
        elif re.match(r'^\d+$', args.time):
            timestamp = int(args.time)
        else:
            print("Invalid time! Define integer-timestamp or date and time as ISO 8601.")
            sys.exit()

        # subtract ahead
        timestamp = timestamp - args.ahead
        set_wake(args.persistent, args.device, timestamp)
        print_wake_set(timestamp)
        
    else:        
        
        if args.ahead == -1:
            args.ahead = default_ahead

        # connect and get next record
        with HtspClient() as client:
            if not client.try_open(host, port):
                tvhclib.open_fail(True)
            
            # get next future record
            next_record = tvhclib.get_next_record(client)
            
            if next_record == None:
                print("No planned record found.")
                sys.exit()
            else:
                timestamp = int(next_record['start']) - args.ahead
                set_wake(args.persistent, args.device, timestamp)
                print_wake_set(timestamp, next_record['title'])
    