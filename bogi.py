#!/usr/bin/env python

import argparse
import bogi.parser

parser = argparse.ArgumentParser()
parser.add_argument('specs', type=str, nargs='+', help='Paths to request specs')
args = parser.parse_args()

bogi_parser = bogi.parser.Parser()
for path in args.specs:
	with open(path, 'r') as file:		
		requests = bogi_parser.parse(file.read())
		for r in requests:
			print(r)