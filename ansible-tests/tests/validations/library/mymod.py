#!/usr/bin/env python


from ansible.module_utils.basic import *


def main():
    module = AnsibleModule(argument_spec={})

    result = {
        'ansible_facts': {
            'custom_fact': 'Hello!'},
        'changed': True,
    }
    module.exit_json(**result)


if __name__ == '__main__':
    main()
