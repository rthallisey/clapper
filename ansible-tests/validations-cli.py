#!/usr/bin/env python


import sys

import validations


def die(msg):
    print msg
    sys.exit(1)


def command_list(**args):
    for i, validation in enumerate(validations.get_all()):
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
        validation = validations.get_all()[index]
    except IndexError:
        die("Invalid validation ID.")
    print "Running validation '%s'" % validation['name']
    results = validations.run(validation)
    for host, status in results.items():
        result_msg = 'SUCCESS' if status['success'] else 'FAILURE'
        print host, result_msg
    if all(status['success'] for status in results.values()):
        print "Validation succeeded."
    else:
        print "Validation failed."


def unknown_command(*args):
    die("Unknown command")

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        die("You must enter a command")
    command = sys.argv[1]
    command_fn = globals().get('command_%s' % command, unknown_command)
    command_fn(*sys.argv[2:])
