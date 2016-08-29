#!/usr/bin/env python

import base64
import itertools
from subprocess import Popen, PIPE
from xml.etree import ElementTree

from ansible.module_utils.basic import *


def parse_pcs_status(pcs_status_xml):
    root = ElementTree.fromstring(pcs_status_xml)
    result = {
        'failures': root.findall('failures/failure'),
    }
    return result


def format_failure(failure):
    return ("Task {task} {op_key} failed on node {node}. Exit reason: "
            "'{exitreason}'. Exit status: '{exitstatus}'."
            .format(task=failure.get('task'),
                    op_key=failure.get('op_key'),
                    node=failure.get('node'),
                    exitreason=failure.get('exitreason'),
                    exitstatus=failure.get('exitstatus')))


def main():
    module = AnsibleModule(argument_spec=dict(
        status=dict(required=True, type='str'),
    ))

    pcs_status = parse_pcs_status(base64.b64decode(module.params.get('status')))
    failures = pcs_status['failures']
    failed = len(failures) > 0
    if failed:
        msg="The pacemaker status contains some failed actions:\n" +\
            '\n'.join((format_failure(failure) for failure in failures))
    else:
        msg="The pacemaker status reports no errors."
    module.exit_json(
        failed=failed,
        msg=msg,
    )


if __name__ == '__main__':
    main()
