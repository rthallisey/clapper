#!/usr/bin/env python

import glob
import sys


# Import explicitly in this order to fix the import issues:
# https://bugzilla.redhat.com/show_bug.cgi?id=1065251
import ansible.playbook
import ansible.constants as C
import ansible.utils.template
from ansible import errors
from ansible import callbacks
from ansible import utils
from ansible.color import ANSIBLE_COLOR, stringc
from ansible.callbacks import display

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


def run_validation(validation):
    playbook = ansible.playbook.PlayBook(
        playbook=validation['path'],
        host_list='hosts',  # TODO: shouldn't be hardcoded
        stats=callbacks.AggregateStats(),
        callbacks=callbacks.PlaybookCallbacks(),
        runner_callbacks=callbacks.PlaybookRunnerCallbacks(stats=callbacks.AggregateStats()))
    playbook.run()


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
    run_validation(validation)


def unknown_command(*args):
    die("Unknown command")


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        die("You must enter a command")
    command = sys.argv[1]
    command_fn = globals().get('command_%s' % command, unknown_command)
    command_fn(*sys.argv[2:])
