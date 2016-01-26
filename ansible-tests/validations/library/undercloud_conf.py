#!/usr/bin/env python

import ConfigParser
from os import path

from ansible.module_utils.basic import *


def main():
    module = AnsibleModule(argument_spec=dict(
        undercloud_conf_path=dict(required=True, type='str'),
    ))

    undercloud_conf_path = module.params.get('undercloud_conf_path')

    if path.exists(undercloud_conf_path) and path.isfile(undercloud_conf_path):
        config = ConfigParser.SafeConfigParser()
        config.read(undercloud_conf_path)

        sections = ['DEFAULT'] + config.sections()
        result = dict(((section, dict(config.items(section)))
                       for section in sections))

        module.exit_json(changed=False,
                         ansible_facts={u'undercloud_conf': result})
    else:
        module.fail_json(msg="Could not open the undercloud.conf file at '%s'"
                         % undercloud_conf_path)


if __name__ == '__main__':
    main()
