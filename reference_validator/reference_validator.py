#!/usr/bin/env python
#coding=utf-8

from __future__ import with_statement, print_function

import sys
import os
import argparse
import re
import yaml # pip install pyyaml
import pprint

RESOURCE = 1
PARAMETER = 2
ATTRIBUTE = 3

class YAML_HotValidator:
    ''' Detects unused variables, invalid references.'''

    def __init__(self, arguments):
        ''' Finds *.yaml files based on entered arguments.
            arguments - dictionary with parsed arguments and their values
        '''

        # List of YAML files to be checked
        self.yaml = []

        # YAML file in dict format
        self.yaml_dict = {}

        # Stores resources and parameters along with the times they are used.
        self.resources = {}
        self.params = {}

        self.print_unused_resources = arguments['unused_resources']
        self.ok = True
        self.printer = pprint.PrettyPrinter(indent=2)

        dirs = []

        # Get all directly entered YAML files + list directories
        for path in arguments['files']:
            abs_path = os.path.abspath(path)
            if os.path.isdir(abs_path):
                dirs.append(abs_path)
            else:
                self.check_suffix(os.path.dirname(abs_path), path)

        # Get YAML files from directories
        for directory in dirs:
            if arguments['recursive']:
                for dirpath, dirs, files in os.walk(directory, topdown=False, followlinks=False):
                    for f in files:
                        self.check_suffix(dirpath, f)
            else:
                for f in os.listdir(directory):
                    self.check_suffix(directory, f)


    def check_suffix(self, cur_dir, cur_file):
        ''' If file has a matching suffix, adds him to dedicated list.
            cur_dir  - path to current directory
            cur_file - filename of currently inspected file
        '''

        if cur_file.endswith('yaml'):
            self.yaml.append(os.path.join(cur_dir, cur_file))


    def validate_files(self):
        ''' Validates YAML files. '''

        for yaml_file in self.yaml:
            try:
                with open(yaml_file, 'r') as fd:
                    self.yaml_dict = yaml.load(fd.read())
            except IOError:
                sys.stderr.write('File ' + yaml_file + ' could not be opened.', file=sys.stderr)

            print("File " + yaml_file)

            # save all parameters and resources names
            for param in list(self.yaml_dict['parameters'].keys()):
                self.params[param] = False
            for resource in list(self.yaml_dict['resources'].keys()):
                self.resources[resource] = False 

            # iterate over sections
            for section, instances in self.yaml_dict.iteritems():
                # skip those without nested structures
                if type(instances) == dict:

                    # iterate over instances (variables)
                    for variable, properties in instances.iteritems():
                        #print(variable)
                        self.inspect_instances(properties, variable)

            # Print unused variables
            if False in self.params.itervalues():
                self.ok = False
                print('Unused parameters:', file=sys.stderr)
                for key, value in self.params.iteritems():
                    if value == False:
                        print('- ' + key, file=sys.stderr)
 
            if (self.print_unused_resources) and (False in self.resources.itervalues()):
                self.ok = False
                print('Resources without reference:', file=sys.stderr)
                for key, value in self.resources.iteritems():
                    if value == False:
                        print('- ' + key, file=sys.stderr)

            if self.ok:
                print('OK')
            else:
                print('')
                self.ok = True

            # clear parameters and resources for next file
            self.resources = {}
            self.params = {}


    def inspect_instances(self, properties, name):
        ''' Check if all references to variables are valid.
            properties - structures containing instance properties and their values
            name       - name of referring isntance
        '''

        if isinstance(properties, list):
            for element in properties:
                if isinstance(element, dict):
                    ok = self.inspect_instances(element, name)
        elif isinstance(properties, dict):
            # Check references, mark used variables
            for key, value in properties.iteritems():
                #print(name, key)
                if key == 'get_param':
                    self.check_validity(value, name, PARAMETER)
                elif key == 'get_resource':
                    self.check_validity(value, name, RESOURCE)
                elif key == 'get_attr':
                    self.check_validity(value, name, ATTRIBUTE)
                else:
                    self.inspect_instances(value, name)


    def check_validity(self, value, name, section):
        ''' Check if all declared variables have been used.
            value   - referred variable
            name    - name of referring instance
            section - kind of referenced variable
        '''

        ok = True

        # Resource
        if section == RESOURCE:
            if value not in list(self.resources.keys()):
                print ("Resource " + value + ' referred in ' + name + ' is not declared.', file=sys.stderr)
                self.ok = False
            elif self.resources[value] == False:
                self.resources[value] = True
        # Param
        elif section == PARAMETER:
            if type(value) == list:
                ret = self.check_param_hierarchy(value)
                if not ret[0]:
                    print ('Parameter ' + ret[1] + ' of instance ' + value[0] + ' referred in ' + name + ' is not declared.', file=sys.stderr)
                    self.ok = False
            else:
                if not self.detect_pseudoparam(value):
                    if value not in list(self.params.keys()):
                        print ('Parameter ' + value + ' referred in ' + name + ' is not declared.', file=sys.stderr)
                        self.ok = False
                    elif (self.params[value] == False):
                        self.params[value] = True
        elif section == ATTRIBUTE:
            if type(value) == list:
                if value[0] not in list(self.resources.keys()):
                    print ('Instance ' + value[0] + ' referred by get_attr in ' + name + ' is not declared.', file=sys.stderr)
                    self.ok = False


    def detect_pseudoparam(self, value):
        ''' If parameter starts with "OS::", skip get_param check.
            value - string to be checked
        '''
 
        if value.startswith('OS::'):
            return True
        else:
            return False


    def check_param_hierarchy(self, hierarchy):
        ''' When access path to variable entered, check validity of hierarchy.
            hierarchy - list of keys used for accessing value
        '''

        root = self.yaml_dict['parameters']

        # Validate path to value
        for ele in hierarchy: 
            if ele in root:
                root = root[ele]
            else:
                return (False, ele)
        return (True, None)

def main():
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('files', type=str, nargs='+', metavar='path/to/file_or_dir',
                        help='Files to be parsed.')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='When directory entered, search for files in its subdirectories recursively.')
    parser.add_argument('-u', '--unused-resources', action='store_true',
                        help='When true, print all resources that are not referred to.')

    # Initialize validator
    validator = YAML_HotValidator(vars(parser.parse_args()))
    # Run validator
    validator.validate_files()

    sys.exit(0)

if __name__ == '__main__':
    main()
