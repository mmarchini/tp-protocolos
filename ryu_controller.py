#coding=utf-8

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime

from eventlet import greenthread, semaphore
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib import mac
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ipv6, arp
from ryu.lib import hub

# Biblioteca que provê funcionalidades para a rede (cálculo de menor caminho)
import networkx as nx

# Representação da topologia completa em forma de grafo
green_nodes = range(1, 11) + map(lambda i: "00:04:00:00:00:0%d"%i, range(1, 8))
green_edges = [
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

# Representação da econômica em forma de grafo
red_nodes = range(1, 8) + map(lambda i: "00:04:00:00:00:0%d"%i, range(1, 8))
red_edges = [
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
    (2,  3,{'port':4}),(3,  2,{'port':2}),
    (3,  4,{'port':4}),(4,  3,{'port':2}),
    (4,  5,{'port':3}),(5,  4,{'port':2}),
    (5,  6,{'port':3}),(6,  5,{'port':2}),
    (5,  7,{'port':4}),(7,  5,{'port':3}),
    (6,  7,{'port':3}),(7,  6,{'port':4}),
]

# Estados da topologia
GREEN = 'green' # Topologia completa
RED   = 'red' # Topologia econõmica

def timestamp():
    """
    Função que retorna o horário atual, formatado para utilização em logs.
    """
    return "[%02d:%02d:%02d]"%datetime.now().timetuple()[3:6]

class ProjectController(app_manager.RyuApp):
    """
    Controlador OpenFlow implementando as seguintes funcionalidades:
        - Desligamento e religamento dos switches 8, 9 e 10 a cada 1 minuto
        - Definição do melhor caminho entre cada host através do algoritmo de menor caminho
        - Resposta a requisições ARP
    """

    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        """
        Construtor do Controlador, responsável por inicializar os grafos das
        topologias, a tabela IP-MAC utilizada nas respostas ARP, a cache de
        datapaths e a thread temporizadora
        """
        super(ProjectController, self).__init__(*args, **kwargs)

        # Inicializa o grafo da topologia completa
        self.green_net=nx.DiGraph()
        self.green_net.add_nodes_from(green_nodes)
        self.green_net.add_edges_from(green_edges)

        # Inicializa o grafo da topologia econômica
        self.red_net=nx.DiGraph()
        self.red_net.add_nodes_from(red_nodes)
        self.red_net.add_edges_from(red_edges)

        # Marca a topologia completa como sendo a topologia atual
        self.net = self.green_net
        self.status = GREEN

        # Inicializa a tabela IP-MAC
        self.arp_table = {}
        self.sw = {}

        # Inicializa a cache de datapaths (usada para deletar os flows)
        self.dps = {}
        self.dps_sem = semaphore.Semaphore(1)

        # Inicializa a thread temporizadora
        self._disabler = hub.spawn(self.disabler)

    def disabler(self,):
        """
        Thread temporizadora, responsável pela troca de estado da topologia a cada
        um minuto
        """
        while True:
            # Dorme por um minuto
            greenthread.sleep(60)

            if self.status == GREEN: # Troca da topologia completa para a econômica
                self.logger.info("%s Let's put %s to sleep", timestamp(), range(8, 11))
                self.net    = self.red_net
                self.status = RED
                self.clean_tables()
            else: # Troca da topologia econômica para a completa
                self.logger.info("%s Let's awake %s", timestamp(), range(8, 11))
                self.net = self.green_net
                self.status = GREEN
                self.clean_tables()

    def clean_tables(self):
        """
        Método responsável por limpar os fluxos de todos os switches. Esse método
        deve ser executado quando ocorrer a troca de estado da topologia
        """
        with self.dps_sem:
            # Busca todos os datapaths na cache
            for datapath in self.dps.values():
                ofproto = datapath.ofproto

                # Monta e envia o pacote OpenFlow informando para o switch
                # que ele deve apagar os dados da sua tabela
                wildcards = ofproto_v1_0.OFPFW_ALL
                match = datapath.ofproto_parser.OFPMatch(
                    wildcards, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

                mod = datapath.ofproto_parser.OFPFlowMod(
                    datapath=datapath, match=match, cookie=0,
                    command=ofproto.OFPFC_DELETE)
                datapath.send_msg(mod)
            # Limpa a cache de datapaths
            self.dps.clear()


    def add_flow(self, datapath, in_port, dst, actions):
        """
        Método responsável por adicionar um determinado fluxo em um switch.
        """
        with self.dps_sem:
            # Adiciona o datapath na cache, caso ele ainda não esteja presente
            dpid = datapath.id
            if not dpid in self.dps:
                self.dps[dpid] = datapath

            # Monta a mensagem OpenFlow para adicionar o fluxo no switch,
            # informando a porta que o pacote deve ser enviado caso o destino
            # seja igual a 'dst'
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
        """
        Método responsável por tratar pacotes do tipo PacketIn:w
        """
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        # Dropa pacotes IPv6
        if pkt.get_protocol(ipv6.ipv6):
            return None

        # Se for um pacote ARP, aprende o endereço da fonte
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            self.logger.info("ARP RECIEVED")
            self.arp_table[arp_pkt.src_ip] = src  # ARP learning

        # Se o endereço da fonte ainda não está presente no grafo, adiciona o
        # mesmo, com um caminho para o switch atual
        if src not in self.net:
            self.logger.info("%s >> %010d %s %s %s %s", timestamp(), msg.buffer_id, src, dst, dpid, msg.in_port)
            self.net.add_node(src)
            self.net.add_edge(dpid,src,{'port':msg.in_port})
            self.net.add_edge(src,dpid)

        # Se o endereço do destino está presente no grafo, calcula o menor
        # caminho e determina a porta que o pacote deve ser enviado
        if dst in self.net:
            self.logger.info("%s << %010d %s %s %s %s", timestamp(), msg.buffer_id, src, dst, dpid, msg.in_port)

            self.net.edges()
            path=nx.shortest_path(self.net,dpid,dst)
            next=path[1]
            out_port=self.net[dpid][next]['port']
        else:
            # Se o pacote for ARP, trata o mesmo de forma especial
            if self.arp_handler(msg):  # True: reply ou drop;  False: flood
                return None
            else: # Senão, flood
                self.logger.info("%s FLOOD %010d %s %s %s %s", timestamp(), msg.buffer_id, src, dst, dpid, msg.in_port)
                out_port = ofproto.OFPP_FLOOD

        # Determina a(s) porta(s) que o pacote vai seguir))
        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]

        # Se não for flood, adiciona o fluxo no switch
        if out_port != ofproto.OFPP_FLOOD:
            self.add_flow(datapath, msg.in_port, dst, actions)

        # Repassa a mensagem
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

        # Verifica se é ARP e se destino é Broadcast
        if eth_dst == mac.BROADCAST_STR and arp_pkt:
            arp_dst_ip = arp_pkt.dst_ip

            if (datapath.id, eth_src, arp_dst_ip) in self.sw:
                if self.sw[(datapath.id, eth_src, arp_dst_ip)] != in_port:
                    datapath.send_packet_out(in_port=in_port, actions=[])
                    return True
            else:
                self.sw[(datapath.id, eth_src, arp_dst_ip)] = in_port

        # Se for ARP Request, tenta responder
        if arp_pkt:
            opcode = arp_pkt.opcode
            arp_src_ip = arp_pkt.src_ip
            arp_dst_ip = arp_pkt.dst_ip

            if opcode == arp.ARP_REQUEST:
                # Procura na tabela IP-MAC
                if arp_dst_ip in self.arp_table:
                    actions = [parser.OFPActionOutput(in_port)]
                    # Monta o pacote ARP para responder
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

                    # Envia o ARP Reply com o endereço MAC do IP solicitado
                    out = parser.OFPPacketOut(
                        datapath=datapath,
                        buffer_id=ofproto.OFP_NO_BUFFER,
                        in_port=ofproto.OFPP_CONTROLLER,
                        actions=actions, data=ARP_Reply.data)
                    datapath.send_msg(out)
                    return True
        # Não é ARP Request ou não conhecemos o endereço IP ainda
        return False

