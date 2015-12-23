#!/usr/bin/env python

import glob
from os import path


# Import explicitly in this order to fix the import issues:
# https://bugzilla.redhat.com/show_bug.cgi?id=1065251
import ansible.playbook
import ansible.constants as C
import ansible.utils.template
from ansible import callbacks

import yaml

DEFAULT_METADATA = {
    'name': 'Unnamed',
    'description': 'No description',
    'stage': 'Default stage',
}


def get_validation_metadata(validation, key):
    try:
        return validation[0]['vars']['metadata'][key]
    except KeyError:
        return DEFAULT_METADATA.get(key)


def get_all_validations():
    '''Loads all validations.'''
    paths = glob.glob('validations/*.yaml')
    result = {}
    for index, validation_path in enumerate(sorted(paths)):
        with open(validation_path) as f:
            validation = yaml.safe_load(f.read())
            # TODO: switch to generating a proper UUID. We need to figure out
            # how to make sure we always assign the same ID to the same test.
            uuid = str(index + 1)
            result[uuid] = {
                'uuid': uuid,
                'playbook': validation_path,
                'name': get_validation_metadata(validation, 'name'),
                'description': get_validation_metadata(validation, 'description'),
            }
    return result


def get_all_stages():
    '''Loads all validation types and includes the related validations.'''
    paths = glob.glob('stages/*.yaml')
    result = {}
    all_validations = get_all_validations().values()
    for index, stage_path in enumerate(sorted(paths)):
        with open(stage_path) as f:
            stage = yaml.safe_load(f.read())
            stage_uuid = str(index + 1)
            validations = included_validation(stage, stage_path, all_validations)
            result[stage_uuid] = {
                'uuid': stage_uuid,
                'name': get_validation_metadata(stage, 'name'),
                'description': get_validation_metadata(stage, 'description'),
                'stage': get_validation_metadata(stage, 'stage'),
                'validations': validations,
            }
    return result


def included_validation(stage, stage_path, all_validations):
    '''Returns all validations included in the validation_type.'''
    validations = []
    for entry in stage:
        if 'include' in entry:
            included_playbook_path = entry['include']
            stage_directory = path.dirname(stage_path)
            normalised_path = path.normpath(
                path.join(stage_directory, included_playbook_path))
            matching_validations = [validation for validation in all_validations
                                    if validation['playbook'] == normalised_path]
            if len(matching_validations) > 0:
                validations.append(matching_validations[0])
    return validations


class ValidationCancelled(Exception):
    pass


class SilentPlaybookCallbacks(object):
    ''' Unlike callbacks.PlaybookCallbacks this doesn't print to stdout. '''

    def __init__(self, cancel_event):
        self.cancel_event = cancel_event

    def on_start(self):
        callbacks.call_callback_module('playbook_on_start')

    def on_notify(self, host, handler):
        callbacks.call_callback_module('playbook_on_notify', host, handler)

    def on_no_hosts_matched(self):
        callbacks.call_callback_module('playbook_on_no_hosts_matched')

    def on_no_hosts_remaining(self):
        callbacks.call_callback_module('playbook_on_no_hosts_remaining')

    def on_task_start(self, name, is_conditional):
        callbacks.call_callback_module(
            'playbook_on_task_start', name, is_conditional)
        if self.cancel_event and self.cancel_event.is_set():
            raise ValidationCancelled()

    def on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None,
                       confirm=False, salt_size=None, salt=None, default=None):
        callbacks.call_callback_module(
            'playbook_on_vars_prompt',
            varname,
            private=private,
            prompt=prompt,
            encrypt=encrypt,
            confirm=confirm,
            salt_size=salt_size,
            salt=None,
            default=default)

    def on_setup(self):
        callbacks.call_callback_module('playbook_on_setup')

    def on_import_for_host(self, host, imported_file):
        callbacks.call_callback_module(
            'playbook_on_import_for_host', host, imported_file)

    def on_not_import_for_host(self, host, missing_file):
        callbacks.call_callback_module(
            'playbook_on_not_import_for_host', host, missing_file)

    def on_play_start(self, name):
        callbacks.call_callback_module('playbook_on_play_start', name)

    def on_stats(self, stats):
        callbacks.call_callback_module('playbook_on_stats', stats)


def run(validation, cancel_event):
    C.HOST_KEY_CHECKING = False
    stats = callbacks.AggregateStats()
    playbook_callbacks = SilentPlaybookCallbacks(cancel_event)
    runner_callbacks = callbacks.DefaultRunnerCallbacks()
    playbook = ansible.playbook.PlayBook(
        playbook=validation['playbook'],
        # TODO we should use a dynamic inventory based on data coming from
        # tripleo-common/heat/ironic
        # http://docs.ansible.com/ansible/developing_api.html
        host_list='hosts',
        stats=stats,
        callbacks=playbook_callbacks,
        runner_callbacks=runner_callbacks)
    try:
        result = playbook.run()
    except ValidationCancelled:
        result = {}
        for host in playbook.inventory.list_hosts():
            result[host] = {
                'failures': 1,
                'unreachable': 0,
                'description': "Validation was cancelled.",
            }

    for host, status in result.items():
        success = status['failures'] == 0 and status['unreachable'] == 0
        result[host]['success'] = success
    return result
