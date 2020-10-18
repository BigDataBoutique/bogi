#!/usr/bin/env python

import os
import sys
import logging
import argparse

from bogi.parser.main import Parser as BogiParser
from bogi.http_runner import HttpRunner
from bogi.logger import logger


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('http_path', type=str, help='.http files directory or single .http file path')
    parser.add_argument('--quiet', '-q', action='store_true', help='Only log errors')
    args = parser.parse_args()

    if args.quiet:
        logger.setLevel(logging.ERROR)

    if not os.path.exists(args.http_path):
        logger.error("{} does not exist".format(args.http_path))
        sys.exit(2)

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
            except Exception as e:
                logger.error('Parsing error in {}'.format(fname))
                logger.exception(e)
                continue

            logger.info(f'{bcolors.HEADER}Processing {fname}, {len(requests)} requests.{bcolors.ENDC}')

            try:
                failures = HttpRunner(requests, ignore_headers=True).run()
                if not failures:
                    logger.info(f'\t{bcolors.OKGREEN}\u2713 Success{bcolors.ENDC}')
                    success_count += 1
                    continue

                for fail in failures:
                    if fail.request.id:
                        logger.error(f'\t{bcolors.FAIL}Error in "{fail.request.id}". {fail.error}{bcolors.ENDC}')
                    else:
                        logger.error(f'\t{bcolors.FAIL}Check {fail.request.method} {fail.request.target} failed\n\t{fail.error}{bcolors.ENDC}')

            except Exception as e:
                logger.fatal("Exception while running {}\n".format(fname))
                logger.exception(e)

    if success_count == len(http_paths):
        logger.info(f'{bcolors.BOLD}{bcolors.OKGREEN}{success_count} requests passed.{bcolors.ENDC}')
        sys.exit(0)
    else:
        logger.fatal(f'{bcolors.BOLD}{bcolors.FAIL}{success_count} requests passed checks, {len(http_paths) - success_count} failed.{bcolors.ENDC}')
        sys.exit(1)
