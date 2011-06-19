"""Linux based switches"""

from subprocess import call
import atexit

class Bridge(object):
    """Linux based bridge L2 switch

    Enable forwarding in linux kernel and iptables
    """

    devnum = 0

    def __init__(self, id):
        """Initialize

        id - Unique switch identifier.
        """

        self.id = id
        self.links = {}

        self.dev = "br{0}".format(Bridge.devnum)
        Bridge.devnum += 1

        cmd = "brctl addbr {0}"
        call(cmd.format(self.dev), shell=True)
        
        cmd = "ifconfig {0} up"
        call(cmd.format(self.dev), shell=True)
        
        atexit.register(self.shutdown)

    def add_link(self, devid, devname):
        """Add add a link to the switch

        devid - Unique device id
        devname - Device name
        """

        self.links[devid] = devname

        cmd = "brctl addif {0} {1}"
        call(cmd.format(self.dev, devname), shell=True)

        cmd = "ifconfig {0} up"
        call(cmd.format(devname), shell=True)

    def shutdown(self):
        """Remove the switch

        Automatically called on exit.
        """

        print "Removing switch {0} ...".format(self.id)

        cmd = "ifconfig {0} down"
        call(cmd.format(self.dev), shell=True)
        
        cmd = "brctl delbr {0}"
        call(cmd.format(self.dev), shell=True)

class OpenVSwitch(object):
    """Open vSwitch based switch; Depends on ovs-vswitchd

    To use this configure ovs-vswitchd as described in the Open vSwitch
    installation manual INSTALL.Linux
    """

    devnum = 0

    def __init__(self, id):
        """Initialize

        id - Unique switch identifier.
        """

        self.id = id
        self.links = {}
        
        self.dev = "br{0}".format(OpenVSwitch.devnum)
        OpenVSwitch.devnum += 1

        cmd = "ovs-vsctl add-br {0}"
        call(cmd.format(self.dev), shell=True)

        atexit.register(self.shutdown)

    def add_link(self, devid, devname):
        """Add add a link to the switch

        devid - Unique device id
        devname - Device name
        """

        self.links[devid] = devname

        cmd = "ovs-vsctl add-port {0} {1}"
        call(cmd.format(self.dev, devname), shell=True)

        cmd = "ifconfig {0} up"
        call(cmd.format(devname), shell=True)

    def shutdown(self):
        """Remove the switch

        Automatically called on exit.
        """
        
        print "Removing switch {0} ...".format(self.id)

        cmd = "ovs-vsctl del-br {0}"
        call(cmd.format(self.dev), shell=True)

