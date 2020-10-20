#!/usr/bin/env python
import datetime
import os
import sys
import logging
import argparse
from urllib.parse import urlparse

import lark
from elasticsearch import Elasticsearch, helpers

from bogi import bcolors
from bogi.callbacks import LoggerCallback
from bogi.parser.main import Parser as BogiParser
from bogi.http_runner import HttpRunner
from bogi.logger import logger

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('http_path', type=str, help='.http files directory or single .http file path')
    parser.add_argument('--es_hosts', type=str, help='Elasticsearch hosts to index results into', required=False)
    parser.add_argument('--quiet', '-q', action='store_true', help='Only log errors')
    args = parser.parse_args()

    if args.quiet:
        logger.setLevel(logging.ERROR)

    if not os.path.exists(args.http_path):
        logger.error("{} does not exist".format(args.http_path))
        sys.exit(2)

    es = None
    report_to_es = False
    es_actions = []
    if args.es_hosts:
        es = Elasticsearch(hosts=args.es_hosts)
        if not es.ping():
            raise Exception(f'Elasticsearch at {args.es_hosts} is unavailable, quitting')
        report_to_es = True

    if os.path.isdir(args.http_path):
        http_paths = [os.path.join(args.http_path, fname)
                      for fname in os.listdir(args.http_path)]
    else:
        http_paths = [args.http_path]
    http_paths = [path for path in http_paths if path.endswith('.http')]

    success_count = 0

    for path in http_paths:
        with open(path, 'r') as file:
            fname = os.path.basename(path)

            try:
                requests = BogiParser().parse(file.read())
            except lark.LarkError as e:
                logger.error(f'{bcolors.WARNING}Parsing error in {fname}{bcolors.ENDC}\n{str(e)}')
                continue

            logger.info(f'{bcolors.HEADER}Processing {fname}, {len(requests)} requests.{bcolors.ENDC}')

            try:
                callback = HttpRunner(requests, callback=LoggerCallback(logger), ignore_headers=True).run()
                if report_to_es:
                    index_name = 'bogi-reports-' + datetime.date.today().strftime('%Y.%m.%d')
                    es_actions.extend([{
                        '_index': index_name,
                        '_source': {
                            'request_id': '',
                            'request': {
                                'url': s.request.target,
                                'method': s.request.method,
                                'domain': urlparse(s.request.target).netloc,
                            },
                            'success': True,
                            'latency': s.latency,
                            'response_time': s.response_time,
                        }
                    } for s in callback.successes
                    ])
                    es_actions.extend([{
                        '_index': index_name,
                        '_source': {
                            'request_id': '',
                            'request': {
                                'url': f.request.target,
                                'method': f.request.method,
                                'domain': urlparse(f.request.target).netloc,
                            },
                            'success': False,
                            'response_time': f.response_time,
                            'error': f.error,
                        }
                    } for f in callback.failures
                    ])

                if len(callback.failures) == 0:
                    logger.info(f'\t{bcolors.OKGREEN}\u2713 Success{bcolors.ENDC}')
                    success_count += 1

            except Exception as e:
                logger.fatal("Exception while running {}\n".format(fname))
                logger.exception(e)

    if report_to_es and len(es_actions):
        helpers.bulk(es, es_actions, stats_only=True)
        es_actions = []

    if success_count == len(http_paths):
        logger.info(f'{bcolors.BOLD}{bcolors.OKGREEN}{success_count} requests passed.{bcolors.ENDC}')
        sys.exit(0)
    else:
        logger.fatal(f'{bcolors.BOLD}{bcolors.FAIL}{success_count} requests passed checks, '
                     f'{len(http_paths) - success_count} failed.{bcolors.ENDC}')
        sys.exit(1)
