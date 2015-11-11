#!/usr/bin/env python

import sys
import requests

VALIDATION_SERVER = 'http://localhost:5000/v1/'

def die(msg):
    print msg
    sys.exit(1)


def command_list(**args):
    resp = requests.get(VALIDATION_SERVER + 'validations/')
    if resp.status_code != 200:
        die('something went wrong')
    for validation in resp.json():
        print "%s. %s" % (validation['uuid'], validation['name'])

def command_run(*args):
    if len(args) != 1:
        die("You must pass one argument: the validation ID.")
    uuid = args[0]
    resp = requests.put(VALIDATION_SERVER + 'validations/' + uuid + '/run')
    if resp.status_code == 404:
        die("Invalid validation ID.")
    elif resp.status_code != 204:
        die("something went wrong")

    print "Running validation '%s'" % uuid


def unknown_command(*args):
    die("Unknown command")

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        die("You must enter a command")
    command = sys.argv[1]
    command_fn = globals().get('command_%s' % command, unknown_command)
    command_fn(*sys.argv[2:])
