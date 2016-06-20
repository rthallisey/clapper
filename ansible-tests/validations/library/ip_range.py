#!/usr/bin/env python

import netaddr

from ansible.module_utils.basic import *

def main():
    module = AnsibleModule(argument_spec=dict(
        start=dict(required=True, type='str'),
        end=dict(required=True, type='str'),
        min_size=dict(required=True, type='int'),
    ))

    start = module.params.get('start')
    end = module.params.get('end')

    iprange = netaddr.IPRange(start, end)

    if len(iprange) < module.params.get('min_size'):
        module.exit_json(
            changed=True,
            warnings=[
                'The IP range {} - {} contains {} addresses.'.format(
                    start, end, len(iprange)),
                'This might not be enough for the deployment or later scaling.'
            ])
    else:
        module.exit_json(msg='success')


if __name__ == '__main__':
    main()
