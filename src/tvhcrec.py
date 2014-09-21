#!/usr/bin/env python

import re
import os
import sys
import time
import tvhclib
from datetime import datetime, timedelta
from tvhc import *


def extend_parser(parser):
    tvhclib.append_default_arguments(parser)
    
    parser.add_argument('--delete', action='store_true', default = False,
                        help = 'Deletes found items.') 


if __name__ == '__main__':
    
    # parse arguments
    parser = tvhclib.create_parser(extend=extend_parser)
    args = parser.parse_args()
    
    # get host & port
    host, port = tvhclib.parse_host(args.host)

    # what's to do?
    with HtspClient() as client:
        if not client.try_open(host, port):
            tvhclib.open_fail(True)
    
        if args.query == None or args.query == '':
            tvhclib.print_client_info(host, port, client)

        records = client.records.values()
        records = sorted(records, key=lambda rec: rec['start']) 
        records = map(lambda r: tvhclib.extend_record(client, r), records)
        
        fieldtypes = tvhclib.fieldtypes['record']
        records = tvhclib.search_items(records, fieldtypes, args.query)
        
        format = args.format or tvhclib.formats['record']
        tvhclib.print_items(records, format)