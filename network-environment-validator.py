#!/usr/bin/env python

import argparse
import sys

from validation_library.validate_network_environment import validate


def main():
    parser = argparse.ArgumentParser(description='Clapper')
    parser.add_argument('-n', '--netenv',
                        help='path to network environment file',
                        type=str,
                        default='network-environment.yaml')
    args = parser.parse_args()

    errors = validate(args.netenv)

    if errors:
        for error in errors:
            print error
    else:
        print "No errors found"


if __name__ == "__main__":
    sys.exit(main())
