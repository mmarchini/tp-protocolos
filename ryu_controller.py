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

import time
import struct
import logging
from datetime import datetime

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ipv4, ipv6

from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import ControllerBase
from ryu.topology import event, switches
import networkx as nx

class BufferID(object):

    def __init__(self, value):
        self.buffer_id = value

    @property
    def buffer_id(self):
        return self._buffer_id

    @buffer_id.setter
    def buffer_id(self, value):
        self.timestamp = time.time()
        self._buffer_id = value

    @classmethod
    def cleanup(self, _dict, timeout=120):
        now = time.time()
        bids = []
        for bid in _dict:
            if now-bid.timestamp < timeout:
                bids.append(bid)
        for bid in bids:
            del _dict[bid]
        return _dict

def timestamp():
    return "[%02d:%02d:%02d]"%datetime.now().timetuple()[3:6]

class ProjectController(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ProjectController, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        self.net=nx.DiGraph()
        self.nodes = {}
        self.links = {}

        self.avoid_loop = {}

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

    def skip_packet(self, buffer_id, dpid):
        BufferID.cleanup(self.avoid_loop)
        bid = filter(lambda b: b.buffer_id == buffer_id, [bid for bid in self.avoid_loop])
        if len(bid) == 0:
            bid = BufferID(buffer_id)
            self.avoid_loop[bid] = [dpid]
            return False
        bid = bid[0]
        if dpid in self.avoid_loop[bid]:
            return True
        self.avoid_loop[bid].append(dpid)
        return False

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
        if msg.buffer_id != ofproto.OFP_NO_BUFFER and self.skip_packet(msg.buffer_id, dpid):
            self.logger.info("%s DROP %010d %s %s %s %s", timestamp(), msg.buffer_id, src, dst, dpid, msg.in_port)
            return
        if src not in self.net:
            self.logger.info("%s >> %010d %s %s %s %s", timestamp(), msg.buffer_id, src, dst, dpid, msg.in_port)
            self.net.add_node(src)
            self.net.add_edge(dpid,src,{'port':msg.in_port})
            self.net.add_edge(src,dpid)
        if dst in self.net:
            self.logger.info("%s << %010d %s %s %s %s", timestamp(), msg.buffer_id, src, dst, dpid, msg.in_port)

            path=nx.shortest_path(self.net,src,dst)
            next=path[path.index(dpid)+1]
            out_port=self.net[dpid][next]['port']
        else:
            self.logger.info("%s FLOOD %010d %s %s %s %s", timestamp(), msg.buffer_id, src, dst, dpid, msg.in_port)
            out_port = ofproto.OFPP_FLOOD

        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]

        # WE WANT PACKET_IN TO AVOID LOOPS
        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            self.add_flow(datapath, msg.in_port, dst, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions)
        datapath.send_msg(out)

    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self, ev):
        switch_list = get_switch(self.topology_api_app, None)
        switches=[switch.dp.id for switch in switch_list]
        self.net.add_nodes_from(switches)

        links_list = get_link(self.topology_api_app, None)
        links=[(link.src.dpid,link.dst.dpid,{'port':link.src.port_no}) for link in links_list]
        self.net.add_edges_from(links)
        links=[(link.dst.dpid,link.src.dpid,{'port':link.dst.port_no}) for link in links_list]
        self.net.add_edges_from(links)

