#!/usr/bin/env python

import re
import os
import sys
import time
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
    
        # get all records sorted by date with extended data.
        records = client.records.values()
        records = sorted(records, key=lambda rec: rec['start']) 
        records = map(lambda r: tvhclib.extend_record(client, r), records)
        
        # filter by given query - if any
        fieldtypes = tvhclib.fieldtypes['record']
        records = list(tvhclib.search_items(records, fieldtypes, args.query))
        
        # print with given format
        format = args.format or tvhclib.formats['record']
        proceed, count = tvhclib.print_items(records, format)
        
        if not proceed:
            sys.exit()
        
        # what to do next?
        if args.delete and count > 0:
            if args.noconfirm or tvhclib.ask_for_delete(count, 'record'):
                for record_id in map(lambda r: r['id'], records):
                    client.delete_record(record_id)
                    print("ID %s deleted." % record_id)
