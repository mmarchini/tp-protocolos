## --*-- coding: utf-8 --*--

from mininet.net import Mininet
from mininet.node import OVSController

# topologia 3
nw3 = Mininet(controller = OVSController) # net is a Mininet() object
A3 = nw3.addHost( 'A' ) # A is a Host
B3 = nw3.addHost( 'B' ) # B is a Host
C3 = nw3.addHost( 'C' ) # C is a Host
D3 = nw3.addHost( 'D' ) # D is a Host
S3_1 = nw3.addSwitch( 'S1' ) # S is a Switch
S3_2 = nw3.addSwitch( 'S2' ) # S is a Switch
nw3.addLink( A3, S3_1 ) # creates a between A and S1
nw3.addLink( B3, S3_1 ) # creates a between B and S1
nw3.addLink( C3, S3_2 ) # creates a between C and S2
nw3.addLink( D3, S3_2 ) # creates a between D and S2
nw3.addLink( S3_1, S3_2 ) # creates a between S1 and S2
