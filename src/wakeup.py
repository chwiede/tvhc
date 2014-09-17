#!/usr/bin/env python

import os
import sys
import time
import tvhclib
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
            f.write("%s\n" % timestamp)


def extend_parser(parser):
    parser.add_argument('--device', default=default_device, metavar="PATH",
                        help='Defines the RTC device. Default value is "%s"' % default_device)

    parser.add_argument('--persistent', default=default_persistent, metavar="PATH",
                        help='Defines the persistent file. Default value is "%s"' % default_persistent)
    
    parser.add_argument('--clear', action='store_true', default=False,
                        help="Clears wakeup on persistent and RTC device.")

    parser.add_argument('--timestamp', type=int, default=None,
                        help="Manually define timestamp. No record will be searched.")


def print_wake_set(timestamp):
    print("Wakeup set to %s." % timestamp)
    

if __name__ == '__main__':
    
    # parse arguments
    parser = tvhclib.create_parser(extend=extend_parser)
    args = parser.parse_args()
    
    # get host & port
    host, port = tvhclib.parse_host(args.host)
    
    # clear or set?
    if args.clear:
        clear_wake(args.persistent, args.device)
        print("Wakeup cleared.")
        
    elif args.timestamp != None:
        set_wake(args.persistent, args.device, args.timestamp)
        print_wake_set(args.timestamp)
        
    else:        
        
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
                timestamp = int(next_record['start'])
                set_wake(args.persistent, args.device, timestamp)
                print_wake_set(timestamp)
    