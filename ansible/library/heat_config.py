#!/usr/bin/env python


def main():
    module = AnsibleModule(argument_spec={})

    facts = {
        'heat_facts': {
            'stuff': 'HELLO WORLD'
        }
    }

    # if json files not found:
    # module.fail_json(msg='ERROR MESSAGE GOES HERE')

    result = {
        'ansible_facts': facts,
        'changed': True,
    }
    module.exit_json(**result)


from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
