#!/usr/bin/env python


import sys

import validations


def die(msg):
    print msg
    sys.exit(1)


def command_list(**args):
    for validation in validations.get_all().values():
        print "%s. %s (%s)" % (validation['uuid'], validation['name'],
                validation['path'])


def command_run(*args):
    if len(args) != 1:
        die("You must pass one argument: the validation ID.")
    uuid = args[0]
    try:
        validation = validations.get_all()[uuid]
    except KeyError:
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
