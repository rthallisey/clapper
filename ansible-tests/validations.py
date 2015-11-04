#!/usr/bin/env python

import sys
import glob

def die(msg):
    print msg
    sys.exit(1)

def validations():
    validations = glob.glob('playbooks/*.yaml')
    return list(sorted(validations))


def command_list(**args):
    for i, name in enumerate(validations()):
        print "%d. %s" % (i + 1, name)


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
        validation_path = validations()[index]
    except IndexError:
        die("Invalid validation ID.")
        sys.exit(1)
    print "Running validation '%s'" % validation_path

def unknown_command(*args):
    die("Unknown command")


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        die("You must enter a command")
    command = sys.argv[1]
    command_fn = globals().get('command_%s' % command, unknown_command)
    command_fn(*sys.argv[2:])
