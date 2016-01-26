import getopt
import json
from subprocess import Popen, PIPE
import os
import sys


def hardware_data(hw_id, upenv):
    '''Read the inspector data about the given node from Swift'''
    p = Popen(('swift', 'download', '--output', '-', 'ironic-inspector', hw_id),
              env=upenv, stdout=PIPE, stderr=PIPE)
    if p.wait() == 0:
        return json.loads(p.stdout.read())


def all_equal(coll):
    if len(coll) <= 1:
        return True
    first = coll[0]
    for item in coll[1:]:
        if item != first:
            return False
    return True


def main(argv):
    envfile = ''
    outputfile = 'diff-output.json'
    try:
        opts, args = getopt.getopt(argv, "hi:", ["ifile="])
    except getopt.GetoptError:
        print 'test.py -i <envfile>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'test.py -i <envfile>'
            sys.exit()
        elif opt in ("-i", "--ifile"):
            envfile = arg
    print 'Input file is "', envfile
    print 'Output file is "', outputfile

    with open(str(envfile)) as data_file:
        env_data = json.load(data_file)

    upenv = os.environ.copy()
    upenv.update(env_data)

    p = Popen(('swift', 'list', 'ironic-inspector'), env=upenv, stdout=PIPE, stderr=PIPE)
    if p.wait() != 0:
        print "Error running `swift list ironic-inspector`"
        print p.stderr.read()
        sys.exit(1)

    hardware_ids = [i.strip() for i in p.stdout.read().splitlines() if i.strip()]
    hw_dicts = {}
    for hwid in hardware_ids:
        hw_dicts[hwid] = hardware_data(hwid, upenv)

    with open('diff-output.json', 'w') as out:
        json.dump(hw_dicts, out)

if __name__ == "__main__":
    main(sys.argv[1:])
