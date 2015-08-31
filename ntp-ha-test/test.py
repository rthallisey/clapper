import re
from subprocess import Popen, PIPE
import sys

# Super hacky but easier to do than calling Keystone and Heat's APIs
process = Popen(('heat', 'stack-show', 'overcloud'), stdout=PIPE, stderr=PIPE)
output = process.stdout.read()


# If we're in a HA mode (i.e. more than one controller), make sure the
# NtpServer parameters are set.
controller_count = int(re.search(r'"Controller-[^":]*::count"\s*:\s*"([^"]*)"', output).group(1))
if controller_count > 1:
    print "This is a HA setup, checking whether NTP is configured."
    ntp_servers = re.findall(r'"(Controller|Compute)-[^":]*::NtpServer"\s*:\s*"([^"]*)"', output)
    if all(t[1] for t in ntp_servers):
        print "SUCCESS: Controller and Compute nodes are configured with NTP."
    else:
        print "ERROR: NTP server is not configured for Controller or Compute nodes!"
        sys.exit(1)
else:
    print "SUCESS: This is not a HA setup, we don't need NTP configured."
