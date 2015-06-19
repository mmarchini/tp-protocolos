#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, Host, OVSKernelSwitch, OVSSwitch
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.log import setLogLevel, info


def evalTopo():
  "Evaluation Topo for Green Network"

  net = Mininet( topo=None, controller=RemoteController, switch=OVSKernelSwitch )

  net.addController( 'c0', RemoteController, ip="127.0.0.1", port=6633 )

  # Adding switches and nodes (one node to each switch)
  s1 = net.addSwitch('s1')
  h1 = net.addHost('h1', ip='10.0.0.1', mac='00:04:00:00:00:01')

  s2 = net.addSwitch('s2')
  h2 = net.addHost('h2', ip='10.0.0.2', mac='00:04:00:00:00:02')

  s3 = net.addSwitch('s3')
  h3 = net.addHost('h3', ip='10.0.0.3', mac='00:04:00:00:00:03')

  s4 = net.addSwitch('s4')
  h4 = net.addHost('h4', ip='10.0.0.4', mac='00:04:00:00:00:04')

  s5 = net.addSwitch('s5')
  h5 = net.addHost('h5', ip='10.0.0.5', mac='00:04:00:00:00:05')

  s6 = net.addSwitch('s6')
  h6 = net.addHost('h6', ip='10.0.0.6', mac='00:04:00:00:00:06')

  s7 = net.addSwitch('s7')
  h7 = net.addHost('h7', ip='10.0.0.7', mac='00:04:00:00:00:07')

  s8 = net.addSwitch('s8')
  s9 = net.addSwitch('s9')
  s10 = net.addSwitch('s10')




  # Creating links between hosts and switches
  net.addLink(h1, s1)
  net.addLink(h2, s2)
  net.addLink(h3, s3)
  net.addLink(h4, s4)
  net.addLink(h5, s5)
  net.addLink(h6, s6)
  net.addLink(h7, s7)

  #Creating links between switches
  net.addLink(s1, s2)
  net.addLink(s1, s8)
  net.addLink(s1, s7)
  net.addLink(s1, s10)
  net.addLink(s2, s10)
  net.addLink(s2, s3)
  net.addLink(s3, s9)
  net.addLink(s3, s4)
  net.addLink(s4, s5)
  net.addLink(s4, s8)
  net.addLink(s5, s6)
  net.addLink(s5, s7)
  net.addLink(s6, s7)
  net.addLink(s7, s8)
  net.addLink(s8, s9)
  net.addLink(s8, s10)
  net.addLink(s9, s10)

  net.start()

  # Start HTTP server on hosts 10.0.0.1 and 10.0.0.3
  h1.sendCmd("cd webpage && python -m SimpleHTTPServer 80 &")
  h3.sendCmd("cd webpage && python -m SimpleHTTPServer 80 &")

  CLI( net )

  net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    evalTopo()
