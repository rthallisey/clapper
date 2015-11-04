#!/usr/bin/env python

import sys
import glob

import yaml


def die(msg):
    print msg
    sys.exit(1)

def validations():
    paths = glob.glob('playbooks/*.yaml')
    result = []
    for validation_path in sorted(paths):
        with open(validation_path) as f:
            validation = yaml.safe_load(f.read())
            result.append({
                'path': validation_path,
                'name': validation[0]['vars']['metadata']['name']
            })
    return result


def command_list(**args):
    for i, validation in enumerate(validations()):
        print "%d. %s (%s)" % (i + 1, validation['name'], validation['path'])


def command_run(*args):
    if len(args) != 1:
        die("You must pass one argument: the validation ID.")
    try:
        index = int(args[0]) - 1
    except ValueError:
        die("Validation ID must be a number.")
    if index < 0:
        die("Validation ID must be a positive number.")
    try:
        validation = validations()[index]
    except IndexError:
        die("Invalid validation ID.")
        sys.exit(1)
    print "Running validation '%s'" % validation['name']


def unknown_command(*args):
    die("Unknown command")


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        die("You must enter a command")
    command = sys.argv[1]
    command_fn = globals().get('command_%s' % command, unknown_command)
    command_fn(*sys.argv[2:])
