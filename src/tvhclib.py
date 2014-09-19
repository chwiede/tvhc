#!/usr/bin/env python

import sys
import time
import argparse
from datetime import datetime, timedelta
from argparse import RawTextHelpFormatter


def open_fail(exit):
    print("Could not establish connection...")
    
    if exit:
        sys.exit(1)
    

def extend_record(client, record):
    rec = record.copy()
    rec['channelname'] = client.channels[rec['channel']]['channelName']
    rec['startdate'] = datetime.fromtimestamp(rec['start'])
    rec['duration'] = rec['stop'] - rec['start']
    rec['length'] = timedelta(seconds = rec['stop'] - rec['start'])
    return rec
    

def get_next_record(client, relatime=time.time()):
    records = client.records.values()
    records = sorted(records, key=lambda rec: rec['start'])    
    for rec in records:
        if float(rec['start']) > time.time():
            return rec
    
    return None
    


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
    #parser = argparse.ArgumentParser(formatter_class = RawTextHelpFormatter)
    parser = argparse.ArgumentParser()
    parser.add_argument("host", default=get_default_host(), nargs="?",
                        help='Defines the host to connect with. Default is "%s".' % get_default_host())
    
    if extend != None:
        extend(parser)
    
    return parser


    
    