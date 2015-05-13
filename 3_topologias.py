## --*-- coding: utf-8 --*--

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel

class SingleSwitchTopo(Topo):
    "Single switch connected to n hosts."
    def build(self, n=2):
        switch = self.addSwitch('s1')
        # Python's range(N) generates 0..N-1
        for h in range(n):
            host = self.addHost('h%s' % (h + 1))
            self.addLink(host, switch)

def simpleTest():
    "Create and test a simple network"
    topo = SingleSwitchTopo(n=4)
    net = Mininet(topo)
    net.start()
    print "Dumping host connections"
    dumpNodeConnections(net.hosts)
    print "Testing network connectivity"
    net.pingAll()
    net.stop()

if __name__ == '__main__':
    # Tell mininet to print useful information
    setLogLevel('info')
    simpleTest()

# topologia 1
nw1 = Mininet() # net is a Mininet() object 
A1 = nw1.addHost( 'A' ) # A is a Host() object 
B1 = nw1.addHost( 'B' ) # B is a Host() object 
net.addLink( A1, B1 ) # creates a between A and B 

# topologia 2
nw2 = Mininet() # net is a Mininet() object 
A2 = nw2.addHost( 'A' ) # A is a Host
B2 = nw2.addHost( 'B' ) # B is a Host
S2 = nw2.addSwitch( 'S' ) # S is a Switch
nw2.addLink( A2, S2 ) # creates a between A and S
nw2.addLink( B2, S2 ) # creates a between B and S 

# topologia 3
nw3 = Mininet() # net is a Mininet() object 
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