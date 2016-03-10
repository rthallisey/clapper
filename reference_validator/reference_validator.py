#!/usr/bin/env python
#coding=utf-8

from __future__ import with_statement, print_function

import argparse
import os
import pprint
import re
import sys
import yaml # pip install pyyaml

class YAML_colours:
        ''' Code for colouring output '''
        BLUE      = '\033[94m'
        GREEN     = '\033[92m'
        YELLOW    = '\033[93m'
        RED       = '\033[91m'
        GRAY      = '\033[97m'
        ORANGE    = '\033[33m'
        BOLD      = '\033[1m'
        UNDERLINE = '\033[4m'
        DEFAULT   = '\033[0m'

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
        self.print_unused = arguments['unused']
        self.pretty_format = arguments['pretty_format']
        self.printer = pprint.PrettyPrinter(indent=2)

        # Check HOT file (-f)
        abs_path = os.path.abspath(arguments['file'])
        if abs_path.endswith('yaml'):
            self.templates.insert(0, self.YAML_Hotfile(None, abs_path))

        # Check environment files (-e)
        if arguments['environment']:
            for env in list(arguments['environment']):
                abs_path = os.path.abspath(env)
                if abs_path.endswith('yaml'):
                    self.environments.insert(0, self.YAML_Env(None, abs_path))

        #print(self.environments, self.templates)

    class YAML_Types:
        ''' Enumerated reference get_ functions + properties:parameters reference '''
        RESOURCE  = 1 # get_resource
        PARAMETER = 2 # get_param
        ATTRIBUTE = 3 # get_attr
        PROPERTY  = 4 # parameter in file B does not have corresponding property in file A
        ENV_PARAMETER = 5 # parameters section in env file
        ENV_DEFAULT = 6   # parameter_defaults in env file

    class YAML_Hotfile:
        ''' Class with attributes needed for work with HOT files '''

        def __init__(self, parent_node, abs_path):
            ''' Node is initiated when being detected '''
            self.path = abs_path

            self.parent = parent_node   # Parent node or nothing in the case of root node
            self.children = []          # Ordered children - by the moment of appearance in the code

            self.resources = []         # YAML_Resource list
            self.params = {}            # name : used?
            self.outputs = []           # name, mapped to attributes TODO

            self.structure = {}         # structure of YAML file
            self.ok = True

            self.invalid = []           # list of invalid references (YAML_Reference)

        def validate_file(self, curr_nodes, templates, environments):
            ''' Validates YAML file'''

            # Add current node at the beginning
            curr_nodes.insert(0, self)

            # Open file
            try:
                with open(self.path, 'r') as fd:
                    self.structure = yaml.load(fd.read())
            except IOError:
                print('File ' + self.path + ' could not be opened.', file=sys.stderr)
                sys.exit(1)

            # Save all parameters names and resources + properties
            if 'parameters' in self.structure:
                for param in list(self.structure['parameters'].keys()):
                    self.params[param] = False

            # Save name and structure of each resource
            if 'resources' in self.structure:
                for resource in self.structure['resources']:
                    self.resources.append(YAML_HotValidator.YAML_Resource(resource,
                                          self.structure['resources'][resource]))

            # Save outputs
            if 'outputs' in self.structure:
                for out in self.structure['outputs']:
                    self.outputs.append(out)

            # Examine children nodes to get the full information about references
            for resource in self.resources:
                if resource.type.endswith('.yaml'):
                    templates.insert(0, YAML_HotValidator.YAML_Hotfile(self, resource.type))

                    # Add child
                    self.children.append(templates[0])

                    # Start validating child
                    templates[0].validate_file(curr_nodes, templates, environments)

                    # Whole subtree with root = current node is validated

                    # Check if parameters have corresponding properties or at least a default value
                    # or if they are mentioned in env file (param_default)
                    for par in self.children[-1].params.keys():
                        flag = False
                        if ((par not in resource.properties.keys()) and
                            (not 'default' in self.children[-1].structure['parameters'][par])):
                            for env in environments:
                                if par in list(env.params_default.keys()):
                                    env.params_default[par] = True
                                    flag = True
                        else:
                            flag = True

                        if not flag:
                            self.invalid.append(YAML_HotValidator.YAML_Reference(par, resource.name,
                                                YAML_HotValidator.YAML_Types.PROPERTY))
                            self.ok = False


                    # Tag used properties
                    for prop in resource.properties.keys():
                        if prop in self.children[-1].params.keys():
                            resource.properties[prop] = True

                else:
                    for env in environments:
                        if resource.type in list(env.resource_registry.keys()):
                        # only compare names, also params from env file
                            pass

            # Iterate over sections (all children validated by now)
            for section, instances in self.structure.iteritems():
                # skip those without nested structures
                if type(instances) == dict:

                    # iterate over instances (variables)
                    for variable, properties in instances.iteritems():
                        #print(variable)
                        self.inspect_instances(properties, variable)

            # Remove node from current nodes after validation
            curr_nodes.remove(self)


        def inspect_instances(self, properties, name):
            ''' Check if all references to variables are valid.
                properties - structures containing instance properties and their values
                name       - name of referring instance
            '''

            if isinstance(properties, list):
                for element in properties:
                    if isinstance(element, dict):
                        self.inspect_instances(element, name)
            elif isinstance(properties, dict):
                # Check references, mark used variables
                for key, value in properties.iteritems():
                    if key == 'get_param':
                        self.check_validity(value, name, YAML_HotValidator.YAML_Types.PARAMETER)
                    elif key == 'get_resource':
                        self.check_validity(value, name, YAML_HotValidator.YAML_Types.RESOURCE)
                    elif key == 'get_attr':
                        self.check_validity(value, name, YAML_HotValidator.YAML_Types.ATTRIBUTE)
                    else:
                        self.inspect_instances(value, name)


        def check_validity(self, value, name, section):
            ''' Check if all declared variables have been used.
                value   - referred variable
                name    - name of referring instance
                section - kind of referenced variable
            '''

            # Resource
            if section == YAML_HotValidator.YAML_Types.RESOURCE:
                if value not in [x.name for x in self.resources]:
                    # Add it to invalid references
                    self.invalid.append(YAML_HotValidator.YAML_Reference(value, name,
                                        YAML_HotValidator.YAML_Types.RESOURCE))
                    self.ok = False
                else:
                    for resource in self.resources:
                        if value == resource.name:
                            resource.setUsage()
                            break

            # Parameter
            elif section == YAML_HotValidator.YAML_Types.PARAMETER:
                if type(value) == list:
                    ret = self.check_param_hierarchy(value)
                    if not ret[0]:
                        # Add it to invalid references
                            self.invalid.append(YAML_HotValidator.YAML_Reference(ret[1], name,
                                            YAML_HotValidator.YAML_Types.PARAMETER))

    #                    if (self.pretty_format):
    #                        print ('Parameter ' + YAML_colours.YELLOW + ret[1] + YAML_colours.DEFAULT +
    #                        ' of instance ' + YAML_colours.YELLOW + value[0] + YAML_colours.DEFAULT +
    #                        ' referred in ' + YAML_colours.YELLOW + name + YAML_colours.DEFAULT +
    #                        ' is not declared.', file=sys.stderr)
    #                    else:
    #                        print ('Parameter ' + ret[1] + ' of instance ' + value[0] + ' referred in ' +
    #                                name + ' is not declared.', file=sys.stderr)
                            self.ok = False
                else:
                    if not self.detect_pseudoparam(value): # TODO add mapping
                        if value not in list(self.params.keys()):

                            # Add it to invalid references
                            self.invalid.append(YAML_HotValidator.YAML_Reference(value, name,
                                                YAML_HotValidator.YAML_Types.PARAMETER))
                            self.ok = False

                        elif (self.params[value] == False):
                           self.params[value] = True

            elif section == YAML_HotValidator.YAML_Types.ATTRIBUTE:
                if type(value) == list:
                    if value[0] not in [x.name for x in self.resources]:
                        # TODO Add checking .yaml files, outputs
                        self.invalid.append(YAML_HotValidator.YAML_Reference(value[0], name,
                                            YAML_HotValidator.YAML_Types.ATTRIBUTE))
                        self.ok = False

                    # if it is in a children node, check its first level of hierarchy
                    elif [True for x in self.resources if (x.name == value[0])
                                                          and x.type.endswith('.yaml')]:
                        flag = False
                        for r in self.resources:
                            if r.name == value[0]:
                                for f in self.children:
                                    if r.type == f.path:

                                        # outputs_list used in case of group
                                        if (r.isGroup and (value[1] == 'outputs_list') and
                                           (value[2] in f.outputs)):
                                            flag = True

                                        # mapped in outputs
                                        elif value[1] in f.outputs:
                                            flag = True

                                        #resource.<name> used
                                        elif value[1].startswith('resource.'):
                                            string = value[1].split('.')
                                            if string[1] in [x.name for x in f.resources]:
                                                flag = True
                                        break
                                break
                        if not flag:
                            self.invalid.append(YAML_HotValidator.YAML_Reference(value[0], name,
                                                YAML_HotValidator.YAML_Types.ATTRIBUTE))
                            self.ok = False


        def detect_pseudoparam(self, value): # TODO adapt to mapping
            ''' If parameter starts with "OS::", skip get_param check.
                value - string to be checked
            '''

            if value.startswith('OS::'):
                return True
            else:
                return False


        def check_param_hierarchy(self, hierarchy): # TODO: improve output info
            ''' When access path to variable entered, check validity of hierarchy.
                hierarchy - list of keys used for accessing value
            '''
            root = self.structure['parameters']

            # Validate path to value
            for ele in hierarchy:
                if ele in root:
                    root = root[ele]
                # For params with json type, allow for "default KV section"
                elif (('default' in root) and 
                      (self.structure['parameters'][hierarchy[0]]['type'] == 'json')):
                    root = root['default']
                else:
                    return (False, ele)
            return (True, None)

    class YAML_Env:
        ''' Class with attributes needed for work with environment files '''

        def __init__(self, parent_node, abs_path):
            self.path = abs_path

            # reference to parent and children nodes
            self.parent = parent_node
            self.children = []

            self.resource_registry = {} # original type: mapped type
            self.params = {}            # additional parameters, only for root file -f
            self.params_default = {}    # default values, can replace property in property>param anywhere

            self.structure = {}
            self.invalid = []           # invalid parameter references

            self.ok = True

    class YAML_Resource:
        ''' Stores useful info about resource, its structure '''
        def __init__(self, name, resource_struct):

            self.type = resource_struct['type']
            self.name = name
            self.properties = {}
            self.isGroup = False

            keys = []

            # If there are properties, save them
            if 'properties' in resource_struct:
                # Type and properties of the individual resource
                if self.type == 'OS::Heat::AutoScalingGroup':
                    self.type = resource_struct['properties']['resource']['type']
                    keys = list(resource_struct['properties']['resource']['properties'].keys())
                    self.isGroup = True
                elif self.type == 'OS::Heat::ResourceGroup':
                    self.type = resource_struct['properties']['resource_def']['type']
                    keys = list(resource_struct['properties']['resource_def']['properties'].keys())
                    self.isGroup = True
                else:
                    keys = list(resource_struct['properties'].keys())

                for key in keys:
                    self.properties[key] = False

            self.used = False

        # When resource is used, change the flag
        def setUsage(self):
            self.used = True

    class YAML_Reference:
        ''' Saves all invalid references for output. In YAML_Hotfile '''
        def __init__(self, referent, element, ref_type):
            self.referent = referent # name of referred element
            self.element = element   # in which resource was reference realized
            self.type = ref_type     # type of referred attribute (YAML_Types)

    def validate_environments(self, curr_nodes, mappings, environments):

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
            if 'resource_registry' in env_node.structure:
                for origin, custom in list(env_node.structure['resource_registry'].keys()):
                    env_node.resource_registry[origin] = custom

            # Save additional parameters + parameters with default values
            if 'parameters' in env_node.structure:
                for par in list(env_node.structure['parameters'].keys()):
                    env_node.params[par] = False

            if 'parameter_defaults' in env_node.structure:
                for par in list(env_node.structure['parameter_defaults'].keys()):
                    env_node.params_default[par] = False

            for child in list(env_node.resource_registry.values()):
                # TODO mappings to OS:: ??
                if child.endswith('.yaml'):
                    env_node.children.insert(0, self.YAML_Hotfile(env_node, os.path.abspath(child)))
                    # Add for further examination
                    self.mappings.append(env_node.children[0])


    def check_env_params(self, templates, environments):
        ''' Checks parameters section of environment files '''

        # Check parameters section
        for env in environments:
            for par in list(env.params.keys()):
                if par not in list(templates[-1].params.keys()):
                    env.ok = False
                    env.invalid.append(self.YAML_Reference(par, None, self.YAML_Types.ENV_PARAMETER))
                    # TODO isn't params[par] = False enough?
                else:
                    env.params[par] = True


        # Check parameter_defaults section
        for env in environments:
            for par in list(env.params_default.keys()):
                for hot in templates:
                    if par in list(hot.params.keys()):
                        env.params_default[par] = True
                        break

    def print_output(self):
        ''' Prints results of validation for all files. '''

        # Environments
        if self.environments:
            if self.pretty_format:
                print(YAML_colours.ORANGE + YAML_colours.BOLD + YAML_colours.UNDERLINE + 'Environments:' +
                      YAML_colours.DEFAULT + '\n')
            else:
                print('Environments:\n')

            for env in self.environments:

                # Print title
                if self.pretty_format:
                    print(YAML_colours.BOLD + YAML_colours.UNDERLINE + 'File ' + YAML_colours.BLUE +
                          env.path + YAML_colours.DEFAULT)
                else:
                    print('File ' + env.path)
                print('')

                # Parameters section
                if env.invalid:
                    if self.pretty_format:
                         print (YAML_colours.BOLD + 'Parameters without match in root template:' +
                                YAML_colours.DEFAULT,file=sys.stderr)
                    else:
                         print ('Parameters without match in root template:',file=sys.stderr)
                    for ref in env.invalid:
                        # Invalid parameters
                        if ref.type == self.YAML_Types.ENV_PARAMETER:
                             if self.pretty_format:
                                 print ('- ' + YAML_colours.YELLOW + ref.referent +
                                        YAML_colours.DEFAULT,file=sys.stderr)
                             else:
                                 print ('- ' + ref.referent + ' has no match in root template ',
                                        file=sys.stderr)
                    print('')

                # Parameter_defaults section
                if False in list(env.params_default.values()):
                    env.ok = False
                    if self.pretty_format:
                        print (YAML_colours.BOLD + 'Parameter defaults without match:' +
                               YAML_colours.DEFAULT, file=sys.stderr)
                    else:
                        print ('Parameter defaults without match:',file=sys.stderr)

                    for par in [x for x in list(env.params_default.keys())
                                if env.params_default[x] == False]:
                        if self.pretty_format:
                            print ('- ' + YAML_colours.YELLOW + par +
                                    YAML_colours.DEFAULT,file=sys.stderr)
                        else:
                            print ('- ' + par,file=sys.stderr)
                    print('')

                # Print file status as OK if there were no problems
                if env.ok:
                    if self.pretty_format:
                        print(YAML_colours.BOLD + 'Status: ' + YAML_colours.GREEN + 'OK' +
                              YAML_colours.DEFAULT)
                    else:
                        print ('Status: OK')
                else:
                    if self.pretty_format:
                        print(YAML_colours.BOLD + 'Status: ' + YAML_colours.RED + 'FAILED' +
                              YAML_colours.DEFAULT)
                    else:
                        print('Status: FAILED')

                print('\n\n')


        # Mappings to environments
        if self.mappings:
            if self.pretty_format:
                print(YAML_colours.ORANGE + YAML_colours.BOLD + YAML_colours.UNDERLINE +
                      'Mapped HOT files:' + YAML_colours.DEFAULT + '\n')
            else:
                print('Mapped HOT files:\n')

            for mapped in self.mappings:
                # Print title
                if self.pretty_format:
                    print(YAML_colours.BOLD + YAML_colours.UNDERLINE + 'File ' + YAML_colours.BLUE +
                          mapped.path + YAML_colours.DEFAULT)
                else:
                    print('File ' + mapped.path)
                print('')


        # HOT Files (should be always present)
        if self.pretty_format: 
            print(YAML_colours.ORANGE + YAML_colours.BOLD + YAML_colours.UNDERLINE + 'HOT Files:' +
                  YAML_colours.DEFAULT + '\n')
        else:
            print('HOT Files:\n')

        for node in reversed(self.templates):

            # Print title
            if self.pretty_format:
                print(YAML_colours.BOLD + YAML_colours.UNDERLINE + 'File ' + YAML_colours.BLUE +
                      node.path + YAML_colours.DEFAULT)
            else:
                print('File ' + node.path)
            print('')

            # Invalid references
            if node.invalid:
                if self.pretty_format:
                   print(YAML_colours.BOLD + 'Invalid references:' + YAML_colours.DEFAULT)
                else:
                   print('Invalid references:')

                for ref in node.invalid:
                    if ref.type == self.YAML_Types.RESOURCE:
                        if self.pretty_format:
                            print ('Resource ' + YAML_colours.YELLOW + ref.referent +
                                   YAML_colours.DEFAULT + ' referred in ' + YAML_colours.YELLOW +
                                   ref.element + YAML_colours.DEFAULT + ' is not declared.',
                                   file=sys.stderr)
                        else:
                            print ('Resource ' + ref.referent + ' referred in ' + ref.element +
                                   ' is not declared.', file=sys.stderr)

                    elif ref.type == self.YAML_Types.PARAMETER:
                        if self.pretty_format:
                            print ('Parameter ' + YAML_colours.YELLOW + ref.referent +
                                   YAML_colours.DEFAULT + ' referred in ' + YAML_colours.YELLOW +
                                   ref.element + YAML_colours.DEFAULT + ' is not declared.',
                                   file=sys.stderr)
                        else:
                            print ('Parameter ' + ref.referent + ' referred in ' + ref.element +
                                   ' is not declared.', file=sys.stderr)

                    elif ref.type == self.YAML_Types.ATTRIBUTE:
                        if self.pretty_format:
                            print ('Instance ' + YAML_colours.YELLOW + ref.referent + 
                                   YAML_colours.DEFAULT + ' referred by ' + YAML_colours.YELLOW +
                                   'get_attr' + YAML_colours.DEFAULT + ' in ' + YAML_colours.YELLOW +
                                   ref.element + YAML_colours.DEFAULT + ' is not declared.',
                                   file=sys.stderr)
                        else:
                            print ('Instance ' + ref.referent + ' referred by get_attr in ' +
                                   ref.element + ' is not declared.', file=sys.stderr)

                    elif ref.type == self.YAML_Types.PROPERTY:
                        if self.pretty_format:
                            print('Parameter ' + YAML_colours.YELLOW + ref.referent +
                                  YAML_colours.DEFAULT + ' in ' + YAML_colours.YELLOW + ref.element +
                          YAML_colours.DEFAULT + ' has no corresponding property.')
                print('')

            # Unused parameters
            if False in node.params.itervalues():
                if self.pretty_format:
                    print(YAML_colours.BOLD +  'Unused parameters:' + YAML_colours.DEFAULT,
                          file=sys.stderr)
                else:
                    print('Unused parameters:', file=sys.stderr)

                for key, value in node.params.iteritems():
                    if value == False:
                        if self.pretty_format:
                            print('- ' + YAML_colours.YELLOW + key + YAML_colours.DEFAULT,
                                  file=sys.stderr)
                        else:
                            print('- ' + key, file=sys.stderr)
                print('')

            # Print unused properties
            flag = False
            for res in [x for x in node.resources if x.type.endswith('.yaml')]:
                for prop, value in res.properties.iteritems():
                    if value == False:
                        flag = True
                        break
                if flag:
                    break
            if flag:
                node.ok = False
                if self.pretty_format:
                    print(YAML_colours.BOLD + 'Unused properties:' +
                        YAML_colours.DEFAULT, file=sys.stderr)
                else:
                    print('Properties without corresponding parameter :', file=sys.stderr)

                for res in [x for x in node.resources if x.type.endswith('.yaml')]:
                    for prop, value in res.properties.iteritems():
                        if value == False:
                            if self.pretty_format:
                                print('- ' + YAML_colours.YELLOW + prop + YAML_colours.DEFAULT +
                                      ' in ' + YAML_colours.YELLOW + res.name +
                                      YAML_colours.DEFAULT)
                            else:
                                print('- ' + prop + ' in ' + res.name)
                print('')

            # Print unused resources (optional)
            if (self.print_unused) and [True for x in node.resources if not x.used]:
                if (self.pretty_format):
                    print(YAML_colours.BOLD + 'Resources without reference:' +
                          YAML_colours.DEFAULT, file=sys.stderr)
                else:
                    print('Resources without reference:', file=sys.stderr)

                for resource in node.resources:
                    if resource.used == False:
                        if self.pretty_format:
                            print('- ' + YAML_colours.YELLOW + resource.name + YAML_colours.DEFAULT +
                                  ' (' + resource.type + ')',
                                  file=sys.stderr)
                        else:
                            print('- ' + resource.name, file=sys.stderr)
                print('')

            # Print file status as OK if there were no problems
            if node.ok:
                if self.pretty_format:
                    print(YAML_colours.BOLD + 'Status: ' + YAML_colours.GREEN + 'OK' +
                          YAML_colours.DEFAULT)
                else:
                    print ('Status: OK')
            else:
                if self.pretty_format:
                    print(YAML_colours.BOLD + 'Status: ' + YAML_colours.RED + 'FAILED' +
                          YAML_colours.DEFAULT)
                else:
                    print('Status: FAILED')

            print('\n\n')


def main():
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--unused', action='store_true',
                        help='When true, print all properties/resources that are not referred to.')
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
    validator.validate_environments(validator.curr_nodes, validator.mappings, validator.environments)

    # HOTs in mappings
    for hot in validator.mappings:
        hot.validate_file(validator.curr_nodes, validator.templates, validator.environments)

    # HOT: change to its directory, validate -f
    os.chdir(os.path.dirname(validator.templates[0].path))
    validator.templates[0].validate_file(validator.curr_nodes, validator.templates,
                                         validator.environments)

    # Check environment parameters
    validator.check_env_params(validator.templates, validator.environments)

    # Print results
    validator.print_output()

    sys.exit(0)

if __name__ == '__main__':
    main()
