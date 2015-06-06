## --*-- coding: utf-8 --*--

from mininet.net import Mininet
from mininet.node import OVSController


# topologia 1
nw1 = Mininet(controller = OVSController) # net is a Mininet() object
A1 = nw1.addHost( 'A' ) # A is a Host() object
B1 = nw1.addHost( 'B' ) # B is a Host() object
nw1.addLink( A1, B1 ) # creates a between A and B
