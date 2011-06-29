from net import Host, Network
from switch import OpenVSwitch, Bridge

with Network() as net:
    net.add_node("h0", Host("h0"))
    net.add_node("h1", Host("h1"))
    net.add_node("s0", Bridge("s0"))
    net.add_node("s1", Bridge("s1"))
    net.add_node("s2", Bridge("s2"))

    net.add_link("h0", "s0", "l0")
    net.add_link("h1", "s1", "l1")
    net.add_link("s0", "s2", "l2")
    net.add_link("s1", "s2", "l3")

    net.nodes["h0"].config_link("l0")
    net.nodes["h1"].config_link("l1")

    net.nodes["h0"].call("ifconfig")
    net.nodes["h1"].call("ifconfig")

    net.nodes["h0"].call("ping 10.0.0.2")
    net.nodes["h1"].call("ping 10.0.0.1")

