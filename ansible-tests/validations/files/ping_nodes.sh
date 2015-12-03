#!/bin/bash

# For each unique remote IP (specified via Heat) we check to
# see if one of the locally configured networks matches and if so we
# attempt a ping test the remote network IP.
function ping_controller_ips() {
  local REMOTE_IPS=$@

  for REMOTE_IP in $(echo $REMOTE_IPS | sed -e "s| |\n|g" | sort -u); do

    for LOCAL_NETWORK in $(/usr/sbin/ip r | grep -v default | cut -d " " -f 1); do
       local LOCAL_CIDR=$(echo $LOCAL_NETWORK | cut -d "/" -f 2)
       local LOCAL_NETMASK=$(ipcalc -m $LOCAL_NETWORK | grep NETMASK | cut -d "=" -f 2)
       local REMOTE_NETWORK=$(ipcalc -np $REMOTE_IP $LOCAL_NETMASK | grep NETWORK | cut -d "=" -f 2)

       if [ $REMOTE_NETWORK/$LOCAL_CIDR == $LOCAL_NETWORK ]; then
         echo -n "Trying to ping $REMOTE_IP for local network $LOCAL_NETWORK..."
         if ! ping -c 1 $REMOTE_IP &> /dev/null; then
           echo "FAILURE"
           echo "$REMOTE_IP is not pingable. Local Network: $LOCAL_NETWORK" >&2
           exit 1
         fi
         echo "SUCCESS"
       fi
    done
  done
}

function ping_default_gateway() {
  DEFAULT_GW=$(/usr/sbin/ip r | grep default | cut -d " " -f 3)
  echo -n "Trying to ping default gateway ${DEFAULT_GW}..."
  if ! ping -c 1 $DEFAULT_GW &> /dev/null; then
    echo "FAILURE"
    echo "$DEFAULT_GW is not pingable."
    exit 1
  fi
  echo "SUCCESS"
}

ping_controller_ips "$@"
ping_default_gateway
