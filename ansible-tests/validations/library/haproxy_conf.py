#!/usr/bin/env python

import re

from ansible.module_utils.basic import *


# ConfigParser chokes on both mariadb and haproxy files. Luckily They have
# a syntax approaching ini config file so they are relatively easy to parse.
# This generic ini style config parser is not perfect -- it can ignore some
# valid options --  but good enough for our use case.
def generic_ini_style_conf_parser(file_path, section_regex, option_regex):
    config = {}
    current_section = None
    with open(file_path) as config_file:
        for line in config_file:
            match_section = re.match(section_regex, line)
            if match_section:
                current_section = match_section.group(1)
                config[current_section] = {}
            match_option = re.match(option_regex, line)
            if match_option and current_section:
                option = re.sub('\s+', ' ', match_option.group(1))
                config[current_section][option] = match_option.group(2)
    return config


def parse_haproxy_conf(file_path):
    section_regex = '^(\w+)'
    option_regex = '^(?:\s+)(\w+(?:\s+\w+)*?)\s+([\w/]*)$'
    return generic_ini_style_conf_parser(file_path, section_regex, option_regex)


def main():
    module = AnsibleModule(argument_spec=dict(
        haproxy_conf_path=dict(required=True, type='str'),
    ))

    haproxy_conf_path = module.params.get('haproxy_conf_path')

    try:
        config = parse_haproxy_conf(haproxy_conf_path)
    except IOError:
        module.fail_json(msg="Could not open the haproxy conf file at: '%s'" %
                         haproxy_conf_path)

    module.exit_json(changed=False, ansible_facts={u'haproxy_conf': config})


if __name__ == '__main__':
    main()
