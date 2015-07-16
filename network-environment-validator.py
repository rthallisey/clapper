import sys
import yaml
from socket import inet_ntoa
from struct import pack

def main():
    cidrinfo = {}
    poolsinfo = {}
    vlaninfo = {}
    routeinfo = {}
    bondinfo = {}

    with open("/home/stack/network-environment.yaml", 'r') as test_file:
        network_data=(yaml.load(test_file))
#        print(network_data)

    for net in network_data['parameter_defaults']:
        data=network_data['parameter_defaults'][net]

        if net.endswith('NetCidr'):
            cidrinfo[net]=data

        elif net.endswith('AllocationPools'):
            poolsinfo[net]=data

        elif net.endswith('NetworkVlanID'):
            vlaninfo[net]=data

        elif net == 'ExternalInterfaceDefualtRoute':
            routeinfo=data

        elif net == 'BondInterfaceOvsOptions':
            bondinfo=data


    subnet_overlap(cidrinfo)
    bonding_mode(bondinfo)

def subnet_overlap(subnet):
    for net in subnet:
        print net,":",subnet[net]
    #    mask = net.split('/')[1]

def bonding_mode(bonding):
    print("bonding info: %s" %bonding)

if __name__ == "__main__":
    main()

