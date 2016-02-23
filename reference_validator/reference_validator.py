#!/usr/bin/env python
#coding=utf-8

from __future__ import with_statement, print_function

import argparse
import os
import pprint
import re
import sys
import yaml # pip install pyyaml

# Enumerated get_ functions
RESOURCE = 1
PARAMETER = 2
ATTRIBUTE = 3

# Code for colouring output
class YAML_colours:
    BLUE      = '\033[94m'
    GREEN     = '\033[92m'
    YELLOW    = '\033[93m'
    RED       = '\033[91m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'
    DEFAULT   = '\033[0m'

# Class with attributes needed for work with HOT files
class YAML_Hotfile:
    def __init__(self, parent_node, abs_path):
        ''' Node is initiated when being detected '''
        self.path = abs_path

        self.parent = parent_node   # Parent node or nothing in the case of root node
        self.children = []          # Ordered children - by the moment of appearance in the code

        self.resources = []         # YAML_Resource list
        self.params = {}            # name : used?
        self.outputs = []           # name

        self.structure = {}         # structure of YAML file
        self.ok = True

        self.cursor = False         # position in the file to be able to continue after children nodes 

# Class with attributes needed for work with environment files
class YAML_Env:
    def __init__(self, parent_node, abs_path):
        self.path = abs_path

        # reference to parent and children nodes
        self.parent = parent_node
        self.children = []

        self.resource_registry = {} # original type: mapped type
        self.params = {}            # additional parameters
        self.params_default = {}    # default values

        self.structure = {}
        self.ok = True

        self.cursor = False         # position in the file to be able to continue after children nodes 

# Stores useful info about resource, its structure
class YAML_Resource:
    def __init__(self, name, resource_struct):

        self.type = resource_struct['type']
        self.name = name
        self.properties = {}

        keys = []

        # Sort out group type and resource type
        self.isGroup = (self.type == 'OS::Heat::AutoScalingGroup')

        # If there are properties, save them
        if 'properties' in resource_struct:
            if self.isGroup:
                # type and properties of the individual resource
                self.type = resource_struct['properties']['resource']['type']
                keys = list(resource_struct['properties']['resource']['properties'].keys())
            else:
                #print (resource_struct['properties'].keys())
                keys = list(resource_struct['properties'].keys())

        for key in keys:
            self.properties[key] = False

        self.used = False

    # When resource is used, change the flag
    def setUsage(self):
        self.used = True

class YAML_HotValidator:
    ''' Detects unused variables, invalid references.'''

    def __init__(self, arguments):
        ''' Finds *.yaml files based on entered arguments.
            arguments - dictionary with parsed arguments and their values
        '''

        # in environments, mappings, templates: all nodes with references to parent/children
        # in curr_nodes: currently validated nodes (DFS - depth-first search)

        # List of YAML files to be checked + referenced children nodes
        self.environments = []
        self.mappings = [] # TODO if there are multiple mappings of one origin, which one is used?
        self.templates = []

        # Currently opened nodes
        self.curr_nodes = []

        # Applied parameters
        self.print_unused_resources = arguments['unused_resources']
        self.pretty_format = arguments['pretty_format']
        self.printer = pprint.PrettyPrinter(indent=2)

        # Check HOT file (-f)
        abs_path = os.path.abspath(arguments['file'])
        self.create_node(abs_path, None, self.templates, False)

        # Check environment files (-e)
        if arguments['environment']:
            for env in list(arguments['environment']):
                abs_path = os.path.abspath(env)
                self.create_node(env, None, self.environments, True)

        #print(self.environments, self.templates)

    def create_node(self, path, parent, destination, isEnv):
        ''' If file has a matching suffix, adds him at the beginning of dedicated list.
            path        - path to the file
            parent      - pointer to parent node or False (root)
            destination - where the created node will be added
            isEnv       - is it env file (or file referenced by env file)?
        '''
        if path.endswith('yaml'):
            if isEnv:
                destination.insert(0, YAML_Env(parent, path))
            else:
                destination.insert(0, YAML_Hotfile(parent, path))

    # TODO: write invalid reference header only if there is a problem
    def print_ref_header(self):
        return

    def validate_environments(self):

        # Add all root environment nodes for validation
        self.curr_nodes.append(self.environments)

        if not self.environments:
            return

        for env_node in self.environments:
            try:
                with open(env_node.path, 'r') as fd:
                    env_node.structure = yaml.load(fd.read())
            except IOError:
                print('File ' + env_node.path + ' could not be opened.', file=sys.stderr)
                sys.exit(1)

            # Save mappings
            for origin, custom in list(env_node.structure['resource_registry'].keys()):
              env_node.resource_registry[origin] = custom

            # Save additional parameters + parameters with default values
            for par in list(env_node.structure['parameters'].keys()):
                env_node.params[par] = False

            for par in list(env_node.structure['parameter_defaults']):
                env_node.params_def[par] = False

            for child in list(self.resource_registry.values()):
                self.create_node(os.path.abspath(child), env_node, env_node.children, False)
                # Can there be nested env files or just normal HOT? -> validate env/files
                self.mappings.append(env_node.children.last()) # add for further examination

    def validate_file(self, yaml_node):
        ''' Validates YAML file - yaml_node.'''

        # Add current node at the beginning
        self.curr_nodes.insert(0, yaml_node)

        try:
            with open(yaml_node.path, 'r') as fd:
                yaml_node.structure = yaml.load(fd.read())
        except IOError:
            print('File ' + yaml_node.path + ' could not be opened.', file=sys.stderr)
            sys.exit(1)

        if (self.pretty_format):
            print(YAML_colours.BOLD + YAML_colours.UNDERLINE + 'File ' + YAML_colours.BLUE +
                  yaml_node.path + YAML_colours.DEFAULT)
        else:
            print('File ' + yaml_file)
        print('')

        # Save all parameters names and resources + properties
        for param in list(yaml_node.structure['parameters'].keys()):
            yaml_node.params[param] = False

        # Save name and structure of each resource
        for resource in yaml_node.structure['resources']:
            yaml_node.resources.append(YAML_Resource(resource,
                                       yaml_node.structure['resources'][resource]))

        # Examine children nodes to get the full information about references
        # if type == ...yaml > add node, start examining
        # if type mapped to ...yaml, only check properties x parameters, do not add node
        for resource in yaml_node.resources:
            if resource.type.endswith('.yaml'):
                self.create_node(resource.type, yaml_node, self.templates, False)

                # Add child
                yaml_node.children.append(self.templates[0])

                # Start validating child
                self.validate_file(self.templates[0])

                # Whole subtree with root = current node is validated

                # Check properties TODO: unused properties/parameters
                print(YAML_colours.BOLD + 'Not received parameters at ' + resource.name +
                      ' of ' + YAML_colours.BOLD + YAML_colours.BLUE +
                      os.path.basename(yaml_node.path) + ':' + YAML_colours.DEFAULT)
                for par in yaml_node.children[-1].params.keys():
                    if par not in resource.properties.keys():
                        print('- ' + YAML_colours.YELLOW + par + YAML_colours.DEFAULT)
                print('\n')

            else:
                for env in self.environments:
                    if resource.type in list(env.resource_registry.keys()):
                    # only compare names, also params from env file
                        pass

            


        # Iterate over sections (all children validated by now)
        if (self.pretty_format):
            print(YAML_colours.BOLD + 'Invalid references:' + YAML_colours.DEFAULT)
        else:
            print('Invalid references:')

        for section, instances in yaml_node.structure.iteritems():
            # skip those without nested structures
            if type(instances) == dict:

                # iterate over instances (variables)
                for variable, properties in instances.iteritems():
                    #print(variable)
                    self.inspect_instances(yaml_node, properties, variable)
        print('')

        # Print unused variables
        if False in yaml_node.params.itervalues():
            if (self.pretty_format):
                print(YAML_colours.BOLD +  'Unused parameters:' + YAML_colours.DEFAULT,
                      file=sys.stderr)
            else:
                print('Unused parameters:', file=sys.stderr)
            for key, value in yaml_node.params.iteritems():
                if value == False:
                    if(self.pretty_format):
                        print('- ' + YAML_colours.YELLOW + key + YAML_colours.DEFAULT, file=sys.stderr)
                    else:
                        print('- ' + key, file=sys.stderr)
            print('')

        # Print unused resources (optional)
        if (self.print_unused_resources) and [True for x in yaml_node.resources if not x.used]:
            if (self.pretty_format):
                print(YAML_colours.BOLD + 'Resources without reference:' +
                      YAML_colours.DEFAULT, file=sys.stderr)
            else:
                print('Resources without reference:', file=sys.stderr)
            for resource in yaml_node.resources:
                if resource.used == False:
                    if (self.pretty_format): 
                        print('- ' + YAML_colours.YELLOW + resource.name + YAML_colours.DEFAULT,
                              file=sys.stderr)
                    else:
                        print('- ' + resource.name, file=sys.stderr)
            print('')

        # Print file status as OK if there were no problems
        if yaml_node.ok:
            if (self.pretty_format):
                print(YAML_colours.BOLD + 'Status: ' + YAML_colours.GREEN + 'OK' +
                      YAML_colours.DEFAULT)
            else:
                print ('Status: OK')
        else:
            if (self.pretty_format):
                print(YAML_colours.BOLD + 'Status: ' + YAML_colours.RED + 'FAILED' +
                      YAML_colours.DEFAULT)
            else:
                print('Status: FAILED')
            yaml_node.ok = True
            
        print('\n\n')

        # Remove node from current nodes after validation
        self.curr_nodes.remove(yaml_node)


    def inspect_instances(self, yaml_node, properties, name):
        ''' Check if all references to variables are valid.
            properties - structures containing instance properties and their values
            name       - name of referring instance
        '''

        if isinstance(properties, list):
            for element in properties:
                if isinstance(element, dict):
                    self.inspect_instances(yaml_node, element, name)
        elif isinstance(properties, dict):
            # Check references, mark used variables
            for key, value in properties.iteritems():
                #print(name, key)
                if key == 'get_param':
                    self.check_validity(yaml_node, value, name, PARAMETER)
                elif key == 'get_resource':
                    self.check_validity(yaml_node, value, name, RESOURCE)
                elif key == 'get_attr':
                    self.check_validity(yaml_node, value, name, ATTRIBUTE)
                else:
                    self.inspect_instances(yaml_node, value, name)


    def check_validity(self, yaml_node, value, name, section):
        ''' Check if all declared variables have been used.
            value   - referred variable
            name    - name of referring instance
            section - kind of referenced variable
        '''

        # Resource
        if section == RESOURCE:
            if value not in [x.name for x in self.curr_nodes[0].resources]:
                if (self.pretty_format):
                    print ('Resource ' + YAML_colours.YELLOW + value + YAML_colours.DEFAULT +
                           ' referred in ' + YAML_colours.YELLOW + name + 
                           YAML_colours.DEFAULT + ' is not declared.', file=sys.stderr)
                else:
                    print ('Resource ' + value + ' referred in ' + name + ' is not declared.',
                           file=sys.stderr)
                yaml_node.ok = False
            else:
                for resource in self.curr_nodes[0].resources:
                    if value == resource.name:
                        resource.setUsage()
                        break

        # Parameter
        elif section == PARAMETER:
            if type(value) == list:
                ret = self.check_param_hierarchy(value)
                if not ret[0]:
                    if (self.pretty_format):
                        print ('Parameter ' + YAML_colours.YELLOW + ret[1] + YAML_colours.DEFAULT +
                        ' of instance ' + YAML_colours.YELLOW + value[0] + YAML_colours.DEFAULT +
                        ' referred in ' + YAML_colours.YELLOW + name + YAML_colours.DEFAULT +
                        ' is not declared.', file=sys.stderr)
                    else:
                        print ('Parameter ' + ret[1] + ' of instance ' + value[0] + ' referred in ' +
                                name + ' is not declared.', file=sys.stderr)
                    yaml_node.ok = False
            else:
                if not self.detect_pseudoparam(value):
                    if value not in list(self.curr_nodes[0].params.keys()):
                        if (self.pretty_format):
                            print ('Parameter ' + YAML_colours.YELLOW + value + YAML_colours.DEFAULT +
                                   ' referred in ' + YAML_colours.YELLOW + name + YAML_colours.DEFAULT +
                                   ' is not declared.',file=sys.stderr)
                        else:
                            print ('Parameter ' + value + ' referred in ' + name + ' is not declared.',
                                   file=sys.stderr)
                        yaml_node.ok = False
                    elif (self.curr_nodes[0].params[value] == False):
                       self.curr_nodes[0].params[value] = True
        elif section == ATTRIBUTE:
            if type(value) == list:

                if value[0] not in [x.name for x in self.curr_nodes[0].resources]:
                    if (self.pretty_format):
                        print ('Instance ' + YAML_colours.YELLOW + value[0] + YAML_colours.DEFAULT +
                               ' referred by ' + YAML_colours.YELLOW + 'get_attr' + YAML_colours.DEFAULT +
                               ' in ' + YAML_colours.YELLOW + name + YAML_colours.DEFAULT +
                               ' is not declared.', file=sys.stderr)
                    else:
                        print ('Instance ' + value[0] + ' referred by ' + 'get_attr in ' +
                               name + ' is not declared.', file=sys.stderr)
                    yaml_node.ok = False


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

    def check_resource_type(self, resource):
        if resource['type'].endswith('.yaml'):
            pass

def main():
    # Parse arguments
    parser = argparse.ArgumentParser()
    #parser.add_argument('files', type=str, nargs='+', metavar='path/to/file_or_dir',
    #                    help='Files to be parsed.')
    parser.add_argument('-u', '--unused-resources', action='store_true',
                        help='When true, print all resources that are not referred to.')
    parser.add_argument('-p', '--pretty-format', action='store_true',
                        help='When true, provides colourful output')
    parser.add_argument('-e', '--environment', metavar='path/to/environment', nargs='*',
                        help='Environment files to be used.')
    parser.add_argument('-f', '--file', metavar='path/to/file',
                        help='HOT file to be used.')

    # Initialize validator
    validator = YAML_HotValidator(vars(parser.parse_args()))
    # Run validator

    # env to get mappings
    validator.validate_environments()

    # HOTs in mappings
    for hot in validator.mappings:
        validator.validate_file(hot)

    # HOT: change to its directory, validate -f
    os.chdir(os.path.dirname(validator.templates[0].path))
    validator.validate_file(validator.templates[0])

    #print(validator.templates[1].path, validator.templates[1].parent.path)

    sys.exit(0)

if __name__ == '__main__':
    main()
