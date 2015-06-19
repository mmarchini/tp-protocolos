#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel

class EvalTopo (Topo):
   "Evaluation Topo for Green Network"

   def __init__( self ):

      Topo.__init__( self )

      # Adding switches and nodes (one node to each switch)
      s1 = self.addSwitch('s1')
      h1 = self.addHost('h1', ip='10.0.0.1', mac='00:04:00:00:00:01')

      s2 = self.addSwitch('s2')
      h2 = self.addHost('h2', ip='10.0.0.2', mac='00:04:00:00:00:02')

      s3 = self.addSwitch('s3')
      h3 = self.addHost('h3', ip='10.0.0.3', mac='00:04:00:00:00:03')

      s4 = self.addSwitch('s4')
      h4 = self.addHost('h4', ip='10.0.0.4', mac='00:04:00:00:00:04')

      s5 = self.addSwitch('s5')
      h5 = self.addHost('h5', ip='10.0.0.5', mac='00:04:00:00:00:05')

      s6 = self.addSwitch('s6')
      h6 = self.addHost('h6', ip='10.0.0.6', mac='00:04:00:00:00:06')

      s7 = self.addSwitch('s7')
      h7 = self.addHost('h7', ip='10.0.0.7', mac='00:04:00:00:00:07')

      s8 = self.addSwitch('s8')
      s9 = self.addSwitch('s9')
      s10 = self.addSwitch('s10')



      # Creating links between hosts and switches
      self.addLink(h1, s1)
      self.addLink(h2, s2)
      self.addLink(h3, s3)
      self.addLink(h4, s4)
      self.addLink(h5, s5)
      self.addLink(h6, s6)
      self.addLink(h7, s7)

      #Creating links between switches
      self.addLink(s1, s2)
      self.addLink(s1, s7)
      self.addLink(s1, s8)
      self.addLink(s1, s10)
      self.addLink(s2, s10)
      self.addLink(s2, s3)
      self.addLink(s3, s9)
      self.addLink(s3, s4)
      self.addLink(s4, s5)
      self.addLink(s4, s8)
      self.addLink(s5, s6)
      self.addLink(s5, s7)
      self.addLink(s6, s7)
      self.addLink(s7, s8)
      self.addLink(s8, s9)
      self.addLink(s8, s10)
      self.addLink(s9, s10)


topos = {'evaltopo' : (lambda: EvalTopo() ) }
