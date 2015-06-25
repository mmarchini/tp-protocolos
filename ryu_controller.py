#  This is part of our final project for the Computer Networks Graduate Course at Georgia Tech
#    You can take the official course online too! Just google CS 6250 online at Georgia Tech.
#
#  Contributors:
#
#    Akshar Rawal (arawal@gatech.edu)
#    Flavio Castro (castro.flaviojr@gmail.com)
#    Logan Blyth (lblyth3@gatech.edu)
#    Matthew Hicks (mhicks34@gatech.edu)
#    Uy Nguyen (unguyen3@gatech.edu)
#
#  To run:
#
#    ryu--manager --observe-links shortestpath.py
#
#Copyright (C) 2014, Georgia Institute of Technology.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
An OpenFlow 1.0 shortest path forwarding implementation.
"""

# import time
from datetime import datetime

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib import mac
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ipv6, arp

# from ryu.topology.api import get_switch, get_link
# from ryu.app.wsgi import ControllerBase
# from ryu.topology import event, switches
import networkx as nx

nodes = range(1, 11) + map(lambda i: "00:04:00:00:00:0%d"%i, range(1, 8))
edges = [
    #
    (1, "00:04:00:00:00:01",{'port':1}),
    (2, "00:04:00:00:00:02",{'port':1}),
    (3, "00:04:00:00:00:03",{'port':1}),
    (4, "00:04:00:00:00:04",{'port':1}),
    (5, "00:04:00:00:00:05",{'port':1}),
    (6, "00:04:00:00:00:06",{'port':1}),
    (7, "00:04:00:00:00:07",{'port':1}),
    #
    (1,  2,{'port':2}),(2,  1,{'port':2}),
    (1,  7,{'port':3}),(7,  1,{'port':2}),
    (1,  8,{'port':4}),(8,  1,{'port':1}),
    (1, 10,{'port':5}),(10, 1,{'port':1}),
    (2, 10,{'port':3}),(10, 2,{'port':2}),
    (2,  3,{'port':4}),(3,  2,{'port':2}),
    (3,  9,{'port':3}),(9,  3,{'port':1}),
    (3,  4,{'port':4}),(4,  3,{'port':2}),
    (4,  5,{'port':3}),(5,  4,{'port':2}),
    (4,  8,{'port':4}),(8,  4,{'port':2}),
    (5,  6,{'port':3}),(6,  5,{'port':2}),
    (5,  7,{'port':4}),(7,  5,{'port':3}),
    (6,  7,{'port':3}),(7,  6,{'port':4}),
    (7,  8,{'port':5}),(8,  7,{'port':3}),
    (8,  9,{'port':4}),(9,  8,{'port':2}),
    (8, 10,{'port':5}),(10, 8,{'port':3}),
    (9, 10,{'port':3}),(10, 9,{'port':4}),
]


def timestamp():
    return "[%02d:%02d:%02d]"%datetime.now().timetuple()[3:6]

class ProjectController(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ProjectController, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        self.net=nx.DiGraph()
        self.net.add_nodes_from(nodes)
        self.net.add_edges_from(edges)
        self.arp_table = {
            "10.0.0.1":"00:04:00:00:00:01",
            "10.0.0.2":"00:04:00:00:00:02",
            "10.0.0.3":"00:04:00:00:00:03",
            "10.0.0.4":"00:04:00:00:00:04",
            "10.0.0.5":"00:04:00:00:00:05",
            "10.0.0.6":"00:04:00:00:00:06",
            "10.0.0.7":"00:04:00:00:00:07"
        }
        self.sw = {}

    def add_flow(self, datapath, in_port, dst, actions):
        ofproto = datapath.ofproto

        match = datapath.ofproto_parser.OFPMatch(
            in_port=in_port, dl_dst=haddr_to_bin(dst))

        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0,
            command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
            priority=ofproto.OFP_DEFAULT_PRIORITY,
            flags=ofproto.OFPFF_SEND_FLOW_REM, actions=actions)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        if pkt.get_protocol(ipv6.ipv6):  # Drop the IPV6 Packets.
            return None

        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            self.logger.info("ARP RECIEVED")
            self.arp_table[arp_pkt.src_ip] = src  # ARP learning

        if src not in self.net:
            self.logger.info("%s >> %010d %s %s %s %s", timestamp(), msg.buffer_id, src, dst, dpid, msg.in_port)
            self.net.add_node(src)
            self.net.add_edge(dpid,src,{'port':msg.in_port})
            self.net.add_edge(src,dpid)
        if dst in self.net:
            self.logger.info("%s << %010d %s %s %s %s", timestamp(), msg.buffer_id, src, dst, dpid, msg.in_port)

            self.net.edges()
            path=nx.shortest_path(self.net,dpid,dst)
            next=path[1]
            out_port=self.net[dpid][next]['port']
        else:
            if self.arp_handler(msg):  # 1:reply or drop;  0: flood
                return None
            else:
                self.logger.info("%s FLOOD %010d %s %s %s %s", timestamp(), msg.buffer_id, src, dst, dpid, msg.in_port)
                out_port = ofproto.OFPP_FLOOD

        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            self.add_flow(datapath, msg.in_port, dst, actions)

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions)
        datapath.send_msg(out)

    def arp_handler(self, msg):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.in_port

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        arp_pkt = pkt.get_protocol(arp.arp)

        if eth:
            eth_dst = eth.dst
            eth_src = eth.src

        # Break the loop for avoiding ARP broadcast storm
        if eth_dst == mac.BROADCAST_STR and arp_pkt:
            arp_dst_ip = arp_pkt.dst_ip

            if (datapath.id, eth_src, arp_dst_ip) in self.sw:
                if self.sw[(datapath.id, eth_src, arp_dst_ip)] != in_port:
                    datapath.send_packet_out(in_port=in_port, actions=[])
                    return True
            else:
                self.sw[(datapath.id, eth_src, arp_dst_ip)] = in_port

        # Try to reply arp request
        if arp_pkt:
            # hwtype = arp_pkt.hwtype
            # proto = arp_pkt.proto
            # hlen = arp_pkt.hlen
            # plen = arp_pkt.plen
            opcode = arp_pkt.opcode
            arp_src_ip = arp_pkt.src_ip
            arp_dst_ip = arp_pkt.dst_ip

            if opcode == arp.ARP_REQUEST:
                if arp_dst_ip in self.arp_table:
                    actions = [parser.OFPActionOutput(in_port)]
                    ARP_Reply = packet.Packet()

                    ARP_Reply.add_protocol(ethernet.ethernet(
                        ethertype=eth.ethertype,
                        dst=eth_src,
                        src=self.arp_table[arp_dst_ip]))
                    ARP_Reply.add_protocol(arp.arp(
                        opcode=arp.ARP_REPLY,
                        src_mac=self.arp_table[arp_dst_ip],
                        src_ip=arp_dst_ip,
                        dst_mac=eth_src,
                        dst_ip=arp_src_ip))

                    ARP_Reply.serialize()

                    out = parser.OFPPacketOut(
                        datapath=datapath,
                        buffer_id=ofproto.OFP_NO_BUFFER,
                        in_port=ofproto.OFPP_CONTROLLER,
                        actions=actions, data=ARP_Reply.data)
                    datapath.send_msg(out)
                    return True
        return False

