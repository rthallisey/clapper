#!/usr/bin/env python

import ConfigParser
from os import path

from ansible.module_utils.basic import *


def main():
    module = AnsibleModule(argument_spec=dict(
        option=dict(required=True, type='str'),
        section=dict(required=True, type='str'),
        file=dict(required=True, type='str'),
    ))

    option = module.params.get('option')
    section = module.params.get('section')
    ini_path = path.expanduser(module.params.get('file'))

    if path.exists(ini_path) and path.isfile(ini_path):
        config = ConfigParser.SafeConfigParser()
        config.read(ini_path)

        result = config.get(section, option)

        module.exit_json(changed=False, value=result)
    else:
        module.fail_json(msg="Could not open the '%s' file"
                         % undercloud_conf_path)


if __name__ == '__main__':
    main()
