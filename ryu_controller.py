# Copyright (C) 2013 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import struct
from datetime import datetime
from eventlet import greenthread

from ryu.base import app_manager
from ryu.controller.ofp_event import EventOFPSwitchFeatures
from ryu.controller.handler import CONFIG_DISPATCHER
# from ryu.app.ofctl.api import get_datapath
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib import dpid as dpid_lib
from ryu.lib import stplib, hub
from ryu.lib.mac import haddr_to_str

import topology

def generate_config(bridges):
    config = {}
    for bridge in bridges:
        config[bridge] = {
            "bridge":{
                "max_age":5,
                "priority":0x1000*bridge,
                "hello_time":1,
                "fwd_delay":3,
            }
        }
    return config

class SimpleSwitchStp(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]
    _CONTEXTS = {'stplib': stplib.Stp}

    def __init__(self, *args, **kwargs):
        super(SimpleSwitchStp, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.stp = kwargs['stplib']
        self.last_minute = -1
        self.disabled_switches = set([])

        self.stp.set_config(generate_config(range(1,11)))

        self._disabler = hub.spawn(self.disabler)

    def disabler(self,):
        while True:
            greenthread.sleep(1)

            last_minute = datetime.now().minute
            what_to_disable = [10, 9, 8]
            if last_minute%2 == 0:
                for dpid in filter(self.switch_enabled, what_to_disable):
                    self.logger.info("Trying to disable switch %d", dpid)
                    self.disable_switch(dpid)
            else:
                for dpid in filter(self.switch_disabled, what_to_disable):
                    self.logger.info("Trying to enable switch %d", dpid)
                    self.enable_switch(dpid)

    def add_flow(self, datapath, in_port, dst, actions):
        ofproto = datapath.ofproto
        self.logger.info("Adding flow to %d", datapath.id)

        wildcards = ofproto_v1_0.OFPFW_ALL
        wildcards &= ~ofproto_v1_0.OFPFW_IN_PORT
        wildcards &= ~ofproto_v1_0.OFPFW_DL_DST

        match = datapath.ofproto_parser.OFPMatch(
            wildcards, in_port, 0, dst,
            0, 0, 0, 0, 0, 0, 0, 0, 0)

        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0,
            command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
            priority=ofproto.OFP_DEFAULT_PRIORITY,
            flags=ofproto.OFPFF_SEND_FLOW_REM, actions=actions)
        datapath.send_msg(mod)

    def delete_flow(self, datapath):
        ofproto = datapath.ofproto
        self.logger.info("Removing flow from %d", datapath.id)

        wildcards = ofproto_v1_0.OFPFW_ALL
        match = datapath.ofproto_parser.OFPMatch(
            wildcards, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0,
            command=ofproto.OFPFC_DELETE)
        datapath.send_msg(mod)

    def enable_switch(self, dpid):
        bridge = self.stp.bridge_list.get(dpid, None)
        if not bridge:
            return
        map(bridge.link_up, filter(lambda p: bridge.ports[p].state == stplib.PORT_STATE_DISABLE, bridge.ports))
        self.disabled_switches.discard(dpid)

    def disable_switch(self, dpid):
        bridge = self.stp.bridge_list.get(dpid, None)
        if not bridge:
            self.logger.info("Trying to disable switch %d failed: NOT FOUND", dpid)
            return
        self.disabled_switches.add(dpid)
        map(bridge.link_down, filter(lambda p: bridge.ports[p].state != stplib.PORT_STATE_DISABLE, bridge.ports))
        if dpid in self.mac_to_port.keys():
            del self.mac_to_port[dpid]

    def switch_enabled(self, dpid):
        bridge = self.stp.bridge_list.get(dpid, None)
        if not bridge:
            return None
        return reduce(lambda a, b: b.state != stplib.PORT_STATE_DISABLE and a, bridge.ports.values(), True)

    def switch_disabled(self, dpid):
        return not self.switch_enabled(dpid)

    @set_ev_cls(stplib.EventPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto

        dst, src, _eth_type = struct.unpack_from('!6s6sH', buffer(msg.data), 0)

        dpid = datapath.id
        if dpid in self.disabled_switches:
            return
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s",
                          dpid, haddr_to_str(src), haddr_to_str(dst),
                          msg.in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = msg.in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        # if out_port != ofproto.OFPP_FLOOD:
        #     self.add_flow(datapath, msg.in_port, dst, actions)

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions)
        datapath.send_msg(out)

    @set_ev_cls(stplib.EventTopologyChange, MAIN_DISPATCHER)
    def _topology_change_handler(self, ev):
        dp = ev.dp
        dpid_str = dpid_lib.dpid_to_str(dp.id)
        msg = 'Receive topology change event. Flush MAC table.'
        self.logger.info("[dpid=%s] %s", dpid_str, msg)

        if dp.id in self.mac_to_port:
            del self.mac_to_port[dp.id]
        # self.delete_flow(dp)

    @set_ev_cls(stplib.EventPortStateChange, MAIN_DISPATCHER)
    def _port_state_change_handler(self, ev):
        dpid_str = dpid_lib.dpid_to_str(ev.dp.id)
        # if self.switch_disabled(ev.dp.id): self.delete_flow(ev.dp)
        of_state = {stplib.PORT_STATE_DISABLE: 'DISABLE',
                    stplib.PORT_STATE_BLOCK: 'BLOCK',
                    stplib.PORT_STATE_LISTEN: 'LISTEN',
                    stplib.PORT_STATE_LEARN: 'LEARN',
                    stplib.PORT_STATE_FORWARD: 'FORWARD'}
        self.logger.info("[dpid=%s][port=%d] state=%s",
                          dpid_str, ev.port_no, of_state[ev.port_state])
