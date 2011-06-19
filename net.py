"""A network is collection of hosts connected by switches

This module defines the Host and Network classes which should remain fairly
standard. There can however be different types of switches so they have been
moved to module switch.
"""

from subprocess import call
from procns import NetNS

import atexit

def id_to_tup(id):
    """Create a three byte tuple form and integer id"""

    id = int(id)

    aa = id % 256
    id = (id - aa) / 256
    bb = id % 256
    id = (id - bb) / 256
    cc = id % 256

    return (cc, bb, aa)

def id_to_ip(id):
    """Create an ip from the an integer id"""

    return "10.%d.%d.%d" % id_to_tup(id)

def id_to_mac(id):
    """Create a ethernet address from an integer id"""

    return "00:00:00:%02x:%02x:%02x" % id_to_tup(id)

class Host(NetNS):
    """Host is just a process with a separate network namespace"""

    ifacenum = 1

    def __init__(self, id):
        """Initialize

        id - Unique host identifier
        """

        NetNS.__init__(self)

        self.id = id
        self.links = {}
    
    def add_link(self, devid, devname):
        """Add a link to host

        devid - Unique link idenifier.
        devname - Name of the device. E.g (eth0. h0-eth1, wlan0, ...)
        """

        self.links[devid] = devname

        cmd = "ip link set {0} netns {1}"
        call(cmd.format(devname, self.main.pid), shell=True)

    def config_lo(self):
        """Configure the loopback device"""

        self.call("ifconfig lo 127.0.0.1/8 up", shell=True)

    def config_link(self, dev, ip=None, mask=8, mac=None):
        """Configure the ip and mac address of network device

        dev - If dev is a known linkid then that device is used. Otherwise
              this treated as the physical device name.
        ip - IP address to be assigned.
        mask - Number of bits of representing network.
        mac - The mac address to be assigned.
        """

        if dev in self.links:
            dev = self.links[dev]
        if ip is None:
            ip = id_to_ip(Host.ifacenum)
        if mac is None:
            mac = id_to_mac(Host.ifacenum)

        Host.ifacenum += 1

        cmd = "ifconfig {0} hw ether {1}"
        self.call(cmd.format(dev, mac), shell=True)
        
        cmd = "ifconfig {0} {1}/{2}"
        self.call(cmd.format(dev, ip, mask), shell=True)
        
        cmd = "ifconfig {0} up"
        self.call(cmd.format(dev), shell=True)

class Network(object):
    """A network is a set of nodes connected by links"""

    def __init__(self):
        """Initialize"""

        self.nodes = {}
        self.links = {}

        atexit.register(self.shutdown)

    def add_node(self, nodeid, node):
        """Add a node with a given node id

        nodeid - Unique node identifier.
        node - The node object. I should support an add_link method.    
        """

        if nodeid in self.nodes:
            raise ValueError("Duplicate nodeid %s" % nodeid)

        self.nodes[nodeid] = node

    def add_link(self, nid1, nid2, linkid):
        """Create a veth link and connect two nodes

        nid1 - Node id of the first node.
        nid2 - Node id of the second node.
        linkid - Unique id for the link.
        """

        if nid1 not in self.nodes:
            raise KeyError("Invalid nodeid %s" % nid1)
        if nid2 not in self.nodes:
            raise KeyError("Invalid nodeid %s" % nid2)
        if linkid in self.links:
            raise ValueError("Duplicate linkid %s" % linkid)

        dev1 = "{0}-eth{1}".format(nid1, linkid)
        dev2 = "{0}-eth{1}".format(nid2, linkid)
        
        self.links[linkid] = (dev1, dev2) 

        cmd = "ip link add name {0} type veth peer name {1}"
        call(cmd.format(dev1, dev2), shell=True)
        
        node1 = self.nodes[nid1]
        node2 = self.nodes[nid2]

        node1.add_link(linkid, dev1)
        node2.add_link(linkid, dev2)

    def shutdown(self):
        """Delete all the veth links created

        This should not be called manually. This is called automatically at
        exit.
        """

        cmd = "ip link delete {0} 2> /dev/null"
        for dev1, dummy in self.links.itervalues():
            call(cmd.format(dev1), shell=True)

