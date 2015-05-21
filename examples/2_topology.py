## --*-- coding: utf-8 --*--

from mininet.net import Mininet
from mininet.node import OVSController


# topologia 2
nw2 = Mininet(controller = OVSController) # net is a Mininet() object
A2 = nw2.addHost( 'A1' ) # A is a Host
B2 = nw2.addHost( 'A2' ) # B is a Host
S2 = nw2.addSwitch( 'S1' ) # S is a Switch
nw2.addLink( A2, S2 ) # creates a between A and S
nw2.addLink( B2, S2 ) # creates a between B and S
