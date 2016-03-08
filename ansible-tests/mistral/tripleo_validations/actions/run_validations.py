import subprocess

from mistral.actions import base


def call(program, *args):
    '''
    Call the program with the specified arguments.

    Return the exit value, stdout and stderr.
    '''
    process = subprocess.Popen((program,) + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    exit_value = process.wait()
    return (exit_value, stdout, stderr)


class RunValidations(base.Action):
    def __init__(self):
        pass

    def run(self):
        # TODO(mandre) pass args to run-validation
        exit_code, stdout, stderr = call('/usr/bin/sudo', '-u', 'stack', '/usr/bin/run-validation')
        return {
            'exit_code': exit_code,
            'stdout': stdout,
            'stderr': stderr,
        }
