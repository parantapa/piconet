"""Linux based switches"""

from subprocess import call

class Bridge(object):
    """Linux based bridge L2 switch

    Enable forwarding in linux kernel and iptables.
    """

    devnum = 0

    def __init__(self, id):
        self.id = id
        self.links = {}

        self.devname = "br%d" % Bridge.devnum
        Bridge.devnum += 1

        cmd = "brctl addbr %s"
        call(cmd % self.devname, shell=True)
        
        cmd = "ifconfig %s up"
        call(cmd % self.devname, shell=True)
        
    def add_link(self, devid, devname):
        """Add add a link to the switch

        devid   - Unique device id
        devname - Device name
        """

        self.links[devid] = devname

        cmd = "brctl addif %s %s"
        call(cmd % (self.devname, devname), shell=True)

        cmd = "ifconfig %s up"
        call(cmd % devname, shell=True)

    def close(self):
        """Remove the switch"""

        print "Removing switch %s ..." % self.id

        cmd = "ifconfig %s down"
        call(cmd % self.devname, shell=True)
        
        cmd = "brctl delbr %s"
        call(cmd % self.devname, shell=True)

class OpenVSwitch(object):
    """Open vSwitch based switch; Depends on ovs-vswitchd

    To use this configure ovs-vswitchd as described in the Open vSwitch
    installation manual INSTALL.Linux.
    """

    devnum = 0

    def __init__(self, id):
        self.id = id
        self.links = {}
        
        self.devname = "br%d" % OpenVSwitch.devnum
        OpenVSwitch.devnum += 1

        cmd = "ovs-vsctl add-br %s"
        call(cmd % self.devname, shell=True)

    def add_link(self, devid, devname):
        """Add add a link to the switch

        devid   - Unique device id
        devname - Device name
        """

        self.links[devid] = devname

        cmd = "ovs-vsctl add-port %s %s"
        call(cmd % (self.devname, devname), shell=True)

        cmd = "ifconfig %s up"
        call(cmd % devname, shell=True)

    def close(self):
        """Remove the switch"""

        print "Removing switch %s ..." % self.id

        cmd = "ovs-vsctl del-br %s"
        call(cmd % self.devname, shell=True)

