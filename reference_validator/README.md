Reference Validator
===================

<h2> Requirements </h2>
 
 - pyyaml

<h2> Usage </h2>

This script validates references and detects unused variables in YAML files. It does not detect variables beyond scope of currently opened file. Therefore, it cannot be used to validate references to variables defined by Heat.

    $ python reference_validator.py <path/to/yaml/files> [another/path/to/files] [-r/--recursive] [-u/--unused-resources] [-h/--help]

<b> Parameters </b>
<ul>
<li> path/to/file            Absolute/relative path to file/directory containing YAML files. </li>
<li> -r/--recursive          Scans all subdirectories of a given path for YAML files. </li>
<li> -u/--unused-resources   Prints resources that not referred to in YAML file.</li>
</ul>

<b> Output </b>
Script returns all invalid references including name about instance where the reference is used and a list of all unused parameters (and optionally resources).

TODO: formatted output
