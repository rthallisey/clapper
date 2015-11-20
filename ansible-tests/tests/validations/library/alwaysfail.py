#!/usr/bin/env python


from ansible.module_utils.basic import *


def main():
    module = AnsibleModule(argument_spec={})

    module.fail_json(msg="This module always fails.")


if __name__ == '__main__':
    main()
