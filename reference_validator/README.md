Reference Validator
===================

<h1>WARNING: Work in progress, may return invalid results </h1>

<h2> Requirements </h2>

 - pyyaml
 - six

<h2> Introduction </h2>

This script goes through all HOT files associated with root template, taking mapped resources from environment files into account. It validates references and detects unused variables/instances in YAML files. It accepts the same basic parameters as heat (root template and environments).

<h2> Usage </h2>

    $ python[3] reference_validator.py -f <path/to/yaml/root template> -e <path/to/yaml/environment file>[<another/path/to/env/files>] [-p/--pretty-format] [-u/--unused] [-h/--help]

<h3> Parameters </h3>
<ul>
<li> `-f` is an absolute/relative path to root HOT template. </li>
<li> `-e` is an absolute/relative path to environment file(s). </li>
<li> `-p/--pretty-format` when selected, the output is colourful. </li>
<li> `-u/--unused` causes printing additional info (unused instances without reference).</li>
</ul>

<h2> Output </h2>

Script prints the result to standard output. The result contains a list of all associated files containing invalid references and info about involved instances. Optionally, it also prints a list of all unused instances.
