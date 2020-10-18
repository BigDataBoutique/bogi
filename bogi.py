#!/usr/bin/env python

import os
import sys
import logging
import argparse

from bogi.parser.main import Parser as BogiParser
from bogi.http_runner import HttpRunner
from bogi.logger import logger

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

            logger.debug('* Processing {}, {} requests.'.format(fname, len(requests)))

            try:
                failures = HttpRunner(requests, ignore_headers=True).run()
                if not failures:
                    logger.debug('Success.')
                    success_count += 1
                    continue

                for fail in failures:
                    if fail.request.id:
                        logger.error('Error in "{}". {}'.format(fail.request.id, fail.error))
                    else:
                        logger.error('Error in request {}\n{}'.format(str(fail.request), fail.error))

            except Exception as e:
                logger.error("Exception while running {}\n".format(fname))
                logger.exception(e)

    if success_count == len(http_paths):
        logger.debug("All requests passed.")
        sys.exit(0)
    else:
        logger.error("Fail. {}/{} tests passed.".format(success_count, len(http_paths)))
        sys.exit(1)
