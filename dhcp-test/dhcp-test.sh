#!/bin/bash


OPTIONS=$(getopt -o 'p:' -l 'pacemaker-network:' -n "$(basename $0)" -- "$@")
if [ $? != 0 ] ; then
    echo "Terminating..." >&2;
    exit 1;
fi
eval set -- "$OPTIONS"

while true; do
    case "$1" in
        -p|--pacemaker-network)
            API_NETWORK="$API_NETWORK $2"; shift 2;;
        --) shift; break;;
        *) echo "Error: unknown option $1."; exit 1 ;;
    esac
done

if [ -z "${OS_AUTH_URL}" ] || [ -z "${OS_USERNAME}" ] || [ -z "${OS_PASSWORD}" ]; then
    echo
    echo 'Error: Missing OpenStack credentials (OS_AUTH_URL, OS_USERNAME and OS_PASSWORD).'
    echo 'You should source your `keystonerc` file.'
    echo
    exit 1
fi

set -e

cd `dirname $0`

IDENTITY_SERVICE_ID=$(openstack endpoint list  -f csv -c ID -c "Service Type" --quote minimal | grep identity | cut -d, -f1 -)
echo OpenStack Keystone API endpoints:
echo
openstack endpoint show $IDENTITY_SERVICE_ID -f shell | grep url
echo
echo


PIP=pip
VENV=

if hash virtualenv 2>/dev/null; then
    VENV=.venv
    virtualenv --distribute "$VENV" &>/dev/null
    PIP="$VENV/bin/pip"
fi

hash "$PIP" 2>/dev/null || { echo "pip or virtualenv is required"; exit 1; }

rm -f pip-log.txt
$PIP --log pip-log.txt install scapy ipaddress &>/dev/null

set +e
"$VENV/bin/python" test-pacemaker-networks.py $API_NETWORK
RESULT=$?
set -e

$PIP uninstall -y scapy ipaddress &>/dev/null

if [ ! -z "$VENV" ]; then
    rm -rf "$VENV"
fi

echo; echo
if [ $RESULT == 0 ]; then
    echo SUCESS: No rogue DHCP servers found
else
    echo FAILED: Found rogue DHCP servers
    exit 1
fi
