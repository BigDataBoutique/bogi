#!/usr/bin/env python
import datetime
import os
import sys
import logging
import argparse
from time import sleep
from urllib.parse import urlparse

import lark
from elasticsearch import Elasticsearch, helpers

from bogi import bcolors
from bogi.callbacks import LoggerCallback
from bogi.parser.main import Parser as BogiParser
from bogi.http_runner import HttpRunner
from bogi.logger import logger

es = None
report_to_es = False


def run(base_dir):
    es_actions = []
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
                callback = HttpRunner(requests, base_dir=base_dir,
                                      callback=LoggerCallback(logger), ignore_headers=True).run()
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

    if len(http_paths) > success_count:
        logger.fatal(f'{bcolors.BOLD}{bcolors.FAIL}{success_count} requests passed checks, '
                     f'{len(http_paths) - success_count} failed.{bcolors.ENDC}')
    else:
        logger.info(f'{bcolors.BOLD}{bcolors.OKGREEN}{success_count}/{http_paths} requests passed.{bcolors.ENDC}')

    return success_count, len(http_paths) - success_count


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('http_path', type=str, help='.http files directory or single .http file path')
    parser.add_argument('--es_hosts', type=str, help='Elasticsearch hosts to index results into', required=False)
    parser.add_argument('--quiet', '-q', action='store_true', help='Only log errors')
    parser.add_argument('--loops', type=int, help='How many times to loop (0-1=once, -1=indefinitely)', default=0)
    parser.add_argument('--loop-sleep', type=int, help='How many seconds to sleep between loops', default=10)
    args = parser.parse_args()

    if args.quiet:
        logger.setLevel(logging.ERROR)

    if not os.path.exists(args.http_path):
        logger.error("{} does not exist".format(args.http_path))
        sys.exit(2)

    if args.es_hosts:
        es = Elasticsearch(hosts=args.es_hosts)
        if not es.ping():
            raise Exception(f'Elasticsearch at {args.es_hosts} is unavailable, quitting')
        report_to_es = True
        logger.info(f'{bcolors.WARNING}Elasticsearch at {args.es_hosts} configured{bcolors.ENDC}')

    if os.path.isdir(args.http_path):
        http_paths = [os.path.join(args.http_path, fname)
                      for fname in os.listdir(args.http_path)]
        base_dir = args.http_path
    else:
        http_paths = [args.http_path]
        base_dir = os.path.dirname(args.http_path)
    http_paths = [path for path in http_paths if path.endswith('.http')]

    if args.loops > 1:
        for i in range(args.loops):
            run(base_dir)
            logger.info(f'[{i+1}/{args.loops}] {bcolors.WARNING}Sleeping for {args.loop_sleep} seconds{bcolors.ENDC}')
            sleep(args.loop_sleep)
    elif args.loops == -1:
        while True:
            run(base_dir)
            logger.info(f'[\u221E] {bcolors.WARNING}Sleeping for {args.loop_sleep} seconds{bcolors.ENDC}')
            sleep(args.loop_sleep)
    else:
        successes, failures = run(base_dir)
        if failures > 0:
            sys.exit(1)
        else:
            sys.exit(0)
