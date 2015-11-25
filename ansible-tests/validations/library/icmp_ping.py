#!/usr/bin/env python

DOCUMENTATION = '''
---
module: icmp_ping
short_description: ICMP ping remote hosts
requirements: [ ping ]
description:
    - Check host connectivity with ICMP ping.
options:
    host:
        required: true
        description:
            - IP address or hostname of host to ping
        type: str
author: "Martin Andre (@mandre)"
'''

EXAMPLES = '''
# Ping host:
- icmp: name=somegroup state=present
- hosts: webservers
  tasks:
    - name: Check Internet connectivity
      ping: host="www.ansible.com"
'''


def main():
    module = AnsibleModule(
        argument_spec = dict(
            host = dict(required=True, type='str'),
        )
    )

    failed = False

    host = module.params.pop('host')
    result = module.run_command('ping -c 1 {}'.format(host))[0]
    if result != 0:
        failed = True

    module.exit_json(failed=failed, changed=False)


from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
