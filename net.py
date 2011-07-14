"""A network is collection of hosts connected by switches

This module defines the Host and Network classes which should remain fairly
standard. There can however be different types of switches so they have been
moved to module switch.
"""

from subprocess import call
from procns import NetNS

from misc import id_to_ip, id_to_mac, Closeable

class Host(NetNS):
    """Host is just a process with a separate network namespace"""

    ifacenum = 1

    def __init__(self, id):
        NetNS.__init__(self)

        self.id = id
        self.links = {}
    
    def add_link(self, devid, devname):
        """Add a link to host

        devid   - Unique link idenifier.
        devname - Name of the device. E.g (eth0. h0-eth1, wlan0, ...)
        """

        self.links[devid] = devname

        cmd = "ip link set %s netns %d"
        call(cmd % (devname, self.main.pid), shell=True)

    def close(self):
        print "Removing host %s ..." % self.id

        NetNS.close(self)

    def config_lo(self):
        """Configure the loopback device"""

        self.call("ifconfig lo 127.0.0.1/8 up")

    def config_link(self, dev, ip=None, mask=8, mac=None):
        """Configure the ip and mac address of network device

        dev   - If dev is a known linkid then that device is used. Otherwise
                this treated as the physical device name.
        ip    - IP address to be assigned.
        mask  - Number of bits of representing network.
        mac   - The mac address to be assigned.
        """

        if dev in self.links:
            dev = self.links[dev]
        if ip is None:
            ip = id_to_ip(Host.ifacenum)
        if mac is None:
            mac = id_to_mac(Host.ifacenum)

        Host.ifacenum += 1

        cmd = "ifconfig %s hw ether %s"
        self.call(cmd % (dev, mac))
        
        cmd = "ifconfig %s %s/%d"
        self.call(cmd % (dev, ip, mask))
        
        cmd = "ifconfig %s up"
        self.call(cmd % dev)

class VLink(Closeable):
    """A veth link"""

    def __init__(self, id, nid1, nid2):
        Closeable.__init__(self)

        self.id = id
        self.dev1 = "%s-%s" % (nid1, id)
        self.dev2 = "%s-%s" % (nid2, id)

        cmd = "ip link add name %s type veth peer name %s"
        call(cmd % (self.dev1, self.dev2), shell=True)

    def close(self):
        """Remove the veth link"""

        print "Removing link %s ..." % self.id

        cmd = "ip link delete %s 2> /dev/null"
        call(cmd % self.dev1, shell=True)

class NetDev(Closeable):
    """A real network device

    This class is used to connect the virtual network to the real one
    """

    def __init__(self, id, dev):
        Closeable.__init__(self)

        self.id = id
        self.dev = dev

    def close(self):
        """Print a disconnecting message and exit"""

        print "Disconnecting %s ..." % self.dev

class Network(Closeable):
    """A network is a set of nodes connected by links"""

    def __init__(self):
        Closeable.__init__(self)

        self.nodes = {}
        self.links = {}
        self.ndevs = {}

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

        nid1   - Node id of the first node.
        nid2   - Node id of the second node.
        linkid - Unique id for the link.
        """

        if nid1 not in self.nodes:
            raise KeyError("Invalid nodeid %s" % nid1)
        if nid2 not in self.nodes:
            raise KeyError("Invalid nodeid %s" % nid2)
        if linkid in self.links:
            raise ValueError("Duplicate linkid %s" % linkid)

        link = VLink(linkid, nid1, nid2)
        self.links[linkid] = link

        node1 = self.nodes[nid1]
        node2 = self.nodes[nid2]

        node1.add_link(linkid, link.dev1)
        node2.add_link(linkid, link.dev2)
        
    def add_dev(self, nid, dev, devid):
        """Connect a real device to the network

        nid1   - Node id of the connected node.
        dev    - The name of the real device.
        devid - Unique id for the link.
        """

        if nid not in self.nodes:
            raise KeyError("Invalid nodeid %s" % nid)
        if devid in self.ndevs:
            raise ValueError("Duplicate linkid %s" % devid)

        ndev = NetDev(devid, dev)
        self.ndevs[devid] = ndev

        node = self.nodes[nid]
        node.add_link(devid, ndev.dev)

    def close(self):
        """Delete all the veth links created

        Remember to call this or you shall have many veth pairs lying arround.
        Make use of the context manager using _wait_ to make sure stuff is
        cleaned.
        """

        print "Removing Network"

        for node in self.nodes.itervalues():
            node.close()

        for link in self.links.itervalues():
            link.close()
        
        for ndev in self.ndevs.itervalues():
            ndev.close()
