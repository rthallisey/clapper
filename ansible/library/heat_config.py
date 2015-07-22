#!/usr/bin/env python


import json


def get_occ_files():
    with open('/var/lib/os-collect-config/os_config_files.json', 'r') as f:
        return json.loads(f.read())


def main():
    module = AnsibleModule(argument_spec={})

    facts = {
        'files': {}
    }

    for path in get_occ_files():
        try:
            with open(path, 'r') as f:
                contents = f.read()
        except:
            contents = None

        if contents:
            try:
                facts['files'][path] = json.loads(contents)
            except:
                module.fail_json(msg="Could not parse json at '%s'" % path)

    complete_config = {}
    for conf in facts['files'].values():
        complete_config.update(conf)
    facts['complete'] = complete_config

    result = {
        'ansible_facts': facts,
        'changed': True,
    }
    module.exit_json(**result)


from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
