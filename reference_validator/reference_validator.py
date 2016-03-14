#!/usr/bin/env python
#coding=utf-8

from __future__ import with_statement, print_function

import argparse
import os
import pprint
import re
import sys
import six  # compatibility
import yaml # pip install pyyaml

class YAML_colours:
        ''' Code for colouring output '''
        BLUE      = '\033[94m'
        GREEN     = '\033[92m'
        YELLOW    = '\033[93m'
        RED       = '\033[91m'
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
        self.mappings = []
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
        else:
            print('Wrong template file suffix (YAML expected).',file=sys.stderr)
            sys.exit(1)

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

    class YAML_Hotfile:
        ''' Class with attributes needed for work with HOT files '''

        def __init__(self, parent_node, abs_path):
            ''' Node is initiated when being detected '''
            self.path = abs_path

            self.parent = parent_node   # Parent node or nothing in the case of root node
            self.children = []          # Ordered children - by the moment of appearance in the code

            self.resources = []         # YAML_Resource list
            self.params = {}            # name : used
            self.outputs = []           # name

            self.structure = {}         # structure of YAML file
            self.ok = True

            self.invalid = []           # list of invalid references (YAML_Reference)

        def validate_file(self, curr_nodes, templates, environments):
            ''' Validates YAML file'''

            # Add current node at the beginning
            curr_nodes.insert(0, self)
            #print(self.path, self.parent.path)

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

                    # Check parameters and properties
                    #self.validate_prop_par(self.children[-1], resource, environments)

                # If its type is mapped to yaml file, check against mapping
                # TODO: move elsewhere due to checking against not yet validated mapped file when going through mapped files
                else:
                    for env in environments:
                        for origin, mapped in six.iteritems(env.resource_registry):
                            if resource.type == origin:
                                # Check properties and parameters
                                for child in env.children:
                                    if child.path == mapped:
                                        pass
                                        #self.validate_prop_par(child, resource, environments)

            # Iterate over sections (all children validated by now)
            for section, instances in six.iteritems(self.structure):
                # skip those without nested structures
                if type(instances) == dict:

                    # iterate over instances (variables)
                    for variable, properties in six.iteritems(instances):
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
                    #print (element)
                    if isinstance(element, dict) or isinstance(element, list):
                        self.inspect_instances(element, name)
            elif isinstance(properties, dict):
                # Check references, mark used variables
                #print (properties)
                for key, value in six.iteritems(properties):
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
                            resource.used = True
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
                    if not self.detect_pseudoparam(value):
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
                                        if ((len(value) >= 3) and r.isGroup and
                                            (value[1] == 'outputs_list') and
                                            (value[2] in f.outputs)):
                                            flag = True

                                        # mapped to outputs
                                        elif ((len(value) >= 2) and (value[1] in f.outputs)):
                                            flag = True

                                        #resource.<name> used
                                        elif ((len(value) >= 2) and value[1].startswith('resource.')):
                                            string = value[1].split('.')
                                            if string[1] in [x.name for x in f.resources]:
                                                flag = True
                                        break
                                break
                        if not flag:
                            self.invalid.append(YAML_HotValidator.YAML_Reference(value[0], name,
                                                YAML_HotValidator.YAML_Types.ATTRIBUTE))
                            self.ok = False


        def detect_pseudoparam(self, value):
            ''' Skip get_param check for OS::stack_name, OS::stack_id and OS::project_id.
                value - string to be checked
            '''

            return (value in ['OS::stack_name', 'OS::stack_id', 'OS::project_id'])


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

    class YAML_Reference:
        ''' Saves all invalid references for output. In YAML_Hotfile '''
        def __init__(self, referent, element, ref_type):
            self.referent = referent # name of referred element
            self.element = element   # in which resource was reference realized
            self.type = ref_type     # type of referred attribute (YAML_Types)

    def load_environments(self):

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
                for origin, custom in six.iteritems(env_node.structure['resource_registry']):
                    env_node.resource_registry[origin] = custom

            # Save additional parameters + parameters with default values
            if 'parameters' in env_node.structure:
                for par in list(env_node.structure['parameters'].keys()):
                    env_node.params[par] = False

            if 'parameter_defaults' in env_node.structure:
                for par in list(env_node.structure['parameter_defaults'].keys()):
                    env_node.params_default[par] = False

            for child in list(env_node.resource_registry.values()):
                if child.endswith('.yaml'):
                    env_node.children.insert(0, self.YAML_Hotfile(env_node, child))
                    self.mappings.append(env_node.children[0])


    def validate_env_params(self):
        ''' Checks parameters section of environment files '''

        # Check parameters section
        for env in self.environments:
            for par in list(env.params.keys()):
                if par in list(self.templates[-1].params.keys()):
                    env.params[par] = True

        # Check parameter_defaults section
        for env in self.environments:
            for par in list(env.params_default.keys()):
                for hot in self.templates:
                    if par in list(hot.params.keys()):
                        env.params_default[par] = True
                        break
                for hot in self.mappings:
                    if par in list(hot.params.keys()):
                        env.params_default[par] = True
                        break

    # TODO go through tree of files, not just the list
    def validate_properties(self):
        ''' Validate properties x parameters '''

        # Go through all resources
        for hot in self.templates + self.mappings:
            for resource in hot.resources:

                # If type is YAML file
                if resource.type.endswith('.yaml'):
                    for child in [self.mappings + self.templates]:
                        if (resource.type == child.path) and (child.parent == hot):
                            self.check_prop_par(child, resource)
                            break

                # If type is mapped to YAML file
                else:
                    found = False
                    for env in self.environments:
                        for origin, mapped in six.iteritems(env.resource_registry):
                            if resource.type == origin:
                                for child in self.mappings + self.templates:
                                    if child.path == mapped:
                                        self.check_prop_par(child, resource)
                                        found = True
                                        break
                                break
                        if found:
                            break

    def check_prop_par(self, child, resource):
        ''' Check properties against parameters and vice versa, tag used. '''         

        # Check if parameters have default or value from props
        for par in child.params.keys():
            flag = False
            if ((par not in resource.properties.keys()) and
                (not 'default' in child.structure['parameters'][par])):
                for env in self.environments:
                    if par in list(env.params_default.keys()):
                        env.params_default[par] = True
                        flag = True
            else:
                flag = True

            if not flag:
                self.invalid.append(self.YAML_Reference(par, resource.name,
                                    self.YAML_Types.PROPERTY))
                child.ok = False # TODO FIX

        # Check used properties
        for prop in resource.properties.keys():
            if prop in child.params.keys():
                resource.properties[prop] = True

    def validate_root_params(self):
        ''' Checks availability of values of parameters in root template '''

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
                if False in list(env.params.values()):
                    env.ok = False
                    if self.pretty_format:
                         print (YAML_colours.BOLD + 'Parameters without match in root template:' +
                                YAML_colours.DEFAULT,file=sys.stderr)
                    else:
                         print ('Parameters without match in root template:',file=sys.stderr)
                    for par in [x for x in list(env.params.keys())
                                if env.params[x] == False]:
                        if self.pretty_format:
                            print ('- ' + YAML_colours.YELLOW + par + YAML_colours.DEFAULT,
                                   file=sys.stderr)
                        else:
                            print ('- ' + par, file=sys.stderr)
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


        # HOT Files and mappings
        rev_templates = list(reversed(self.templates))
        for hot in [x for x in [rev_templates, list(reversed(self.mappings))] if len(x)]:
            if self.pretty_format: 
                print(YAML_colours.ORANGE + YAML_colours.BOLD + YAML_colours.UNDERLINE + ('HOT Files:' if hot == rev_templates else 'Mapped HOT Files:') +
                      YAML_colours.DEFAULT + '\n')
            else:
                print(('HOT Files:' if hot == rev_templates else 'Mapped HOT Files:') + '\n')

            for node in hot:

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

                # Unused parameters (optional) ??
                if self.print_unused and (False in node.params.values()):
                    if self.pretty_format:
                        print(YAML_colours.BOLD +  'Unused parameters:' + YAML_colours.DEFAULT,
                              file=sys.stderr)
                    else:
                        print('Unused parameters:', file=sys.stderr)

                    for key, value in six.iteritems(node.params):
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
                    for prop, value in six.iteritems(res.properties):
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
                                      ' (' + resource.type + ')', file=sys.stderr)
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
                        help='When true, prints all unused resources/parameters.')
    parser.add_argument('-p', '--pretty-format', action='store_true',
                        help='When true, provides colourful output')
    parser.add_argument('-e', '--environment', metavar='path/to/environment', nargs='+',
                        help='Environment files to be used.')
    parser.add_argument('-f', '--file', metavar='path/to/file',
                        help='HOT file to be used.')

    # Initialize validator
    validator = YAML_HotValidator(vars(parser.parse_args()))

    # Run validator

    # Load environments to get mappings
    validator.load_environments()

    # Validate HOTs in mappings
    for hot in list(reversed(validator.mappings)):
        if hot.parent in validator.environments:
            os.chdir(os.path.dirname(hot.parent.path))
            hot.validate_file(validator.curr_nodes, validator.mappings, validator.environments)
        # All mappings are at the beginning, followed by their children
        else:
            break

    # Validate HOTs: change to its directory, validate -f
    os.chdir(os.path.dirname(validator.templates[0].path))
    validator.templates[0].validate_file(validator.curr_nodes, validator.templates,
                                         validator.environments)

    # Check environment parameters against fully loaded HOT structure
    validator.validate_env_params()

    # TODO check parameters for root template + props x params everywhere
    validator.validate_properties()
    # TODO if there are multiple mappings of one origin, which one is used? - write warning/error

    # Print results
    validator.print_output()

    sys.exit(0)

if __name__ == '__main__':
    main()
