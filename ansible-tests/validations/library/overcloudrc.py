#!/usr/bin/env python

from ansible.module_utils.basic import *

import os.path
import subprocess


def main():
    module = AnsibleModule(argument_spec=dict(
        path=dict(required=True, type='str'),
    ))

    overcloudrc_path = module.params.get('path')

    if not os.path.isfile(overcloudrc_path):
        module.fail_json(
            msg="The overcloudrc file at {} does not exist.".format(
                overcloudrc_path))

    # Use bash to source overcloudrc and print the environment:
    command = ['bash', '-c', 'source ' + overcloudrc_path + ' && env']
    proc = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.wait() != 0:
        msg = "Could not source '{}'. Return code: {}.\nSTDERR:\n{}".format(
            overcloudrc_path, proc.returncode, proc.stderr.read())
        module.fail_json(msg=msg)

    facts = {}
    for line in proc.stdout:
        (key, _, value) = line.partition("=")
        if key.startswith("OS_"):
            facts[key] = value.rstrip()

    module.exit_json(changed=False, ansible_facts={'overcloudrc': facts})


if __name__ == '__main__':
    main()
