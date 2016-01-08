#!/usr/bin/env python

from os import path

from ansible.module_utils.basic import *


def read_int(module, file_path):
    '''
    Read a file and convert its value to int.

    Raise ansible failure otherwise.
    '''
    try:
        with open(file_path) as f:
            file_contents = f.read()
        return int(file_contents)
    except IOError:
        module.fail_json(msg="Cannot open '%s'" % file_path)
    except ValueError:
        module.fail_json(msg="The '%s' file doesn't contain an integer value" %
                         file_path)

def main():
    module = AnsibleModule(argument_spec=dict(
        drive=dict(required=True, type='str')
    ))

    drive = module.params.get('drive')
    queue_path = path.join('/sys/class/block', drive, 'queue')

    physical_block_size_path = path.join(queue_path, 'physical_block_size')
    logical_block_size_path = path.join(queue_path, 'logical_block_size')

    physical_block_size = read_int(module, physical_block_size_path)
    logical_block_size = read_int(module, logical_block_size_path)

    if physical_block_size == logical_block_size:
        module.exit_json(
            changed=False,
            msg="The disk %s probably doesn't use Advance Format." % drive,
        )
    else:
        module.exit_json(
            # NOTE(shadower): we're marking this as `changed`, to make it
            # visually stand out when running via Ansible directly instead of
            # using the API.
            #
            # The API & UI is planned to look for the `warnings` field and
            # display it differently.
            changed=True,
            warnings=["Physical and logical block sizes of drive %s differ "
            "(%s vs. %s). This can mean the disk uses Advance Format." % (
                drive, physical_block_size, logical_block_size)],
        )


if __name__ == '__main__':
    main()
