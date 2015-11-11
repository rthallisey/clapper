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

def command_results(**args):
    resp = requests.get(VALIDATION_SERVER + 'validation_results/')
    if resp.status_code != 200:
        die('something went wrong')
    for result in resp.json():
        print "%s: %s" % (result['date'], result['status'])
        if 'detailed_description' in result:
            for (host, detail) in result['detailed_description'].items():
                print "\t%s: skipped=%s\tok=%s\tchanged=%s\tunreachable=%s\tfailed=%s" % \
                    (host,
                     detail['skipped'],
                     detail['ok'],
                     detail['changed'],
                     detail['unreachable'],
                     detail['failures'])

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
    die("Unknown command. Available commands: {}".format(available_commands()))

def is_command(function_name):
    return function_name.startswith('command_')

def available_commands(*args):
    return [x[8:] for x in filter(is_command, globals().keys())]

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        die("You must enter a command. Available commands: {}".format(available_commands()))
    command = sys.argv[1]
    function = globals().get('command_%s' % command, unknown_command)
    function(*sys.argv[2:])
