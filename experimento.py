#!/usr/bin/env python3

import sys
from time import sleep

from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import DefaultController, OVSKernelSwitch
from mininet.topo import Topo


class RTPTopo(Topo):
    def build(self):
        s1 = self.addSwitch("s1")
        s2 = self.addSwitch("s2")

        h1 = self.addHost("h1")  # vídeo origem
        h2 = self.addHost("h2")  # vídeo destino
        h3 = self.addHost("h3")  # iperf origem
        h4 = self.addHost("h4")  # iperf destino

        # links de acesso com 10Mb/s
        self.addLink(h1, s1, cls=TCLink, bw=10)
        self.addLink(h3, s1, cls=TCLink, bw=10)
        self.addLink(h2, s2, cls=TCLink, bw=10)
        self.addLink(h4, s2, cls=TCLink, bw=10)
        # link entre switches com 10Mb/s e filas HTB
        self.addLink(s1, s2, cls=TCLink, bw=10, use_htb=True)


def setup_qos(sw, intf):
    """
    Configura QoS HTB no switch `sw` na porta `intf`,
    com duas filas:
      - queue 0: min/max-rate = 2Mb/s (iperf)
      - queue 1: min/max-rate = 8Mb/s (RTP)
    """
    sw.cmd(f"""
        ovs-vsctl -- --id=@q0 create queue other-config:min-rate=2000000 other-config:max-rate=2000000 \
                  -- --id=@q1 create queue other-config:min-rate=8000000 other-config:max-rate=8000000 \
                  -- --id=@newqos create qos type=linux-htb other-config:max-rate=10000000 \
                     queues:0=@q0 queues:1=@q1 \
                  -- set port {intf} qos=@newqos
    """)
    # Regras OpenFlow: RTP → fila 1, iperf → fila 0
    sw.cmd(
        f"ovs-ofctl add-flow {sw.name} 'udp,tp_dst=5004 actions=set_queue:1,normal' "
    )
    sw.cmd(
        f"ovs-ofctl add-flow {sw.name} 'udp,tp_dst=5006 actions=set_queue:1,normal' "
    )
    sw.cmd(
        f"ovs-ofctl add-flow {sw.name} 'udp,tp_dst=5001 actions=set_queue:0,normal' "
    )


def run():
    topo = RTPTopo()
    net = Mininet(
        topo=topo,
        link=TCLink,
        switch=OVSKernelSwitch,
        controller=DefaultController,
        autoSetMacs=True,
    )
    net.start()

    h1, h2, h3, h4 = net.get("h1", "h2", "h3", "h4")
    s1, s2 = net.get("s1", "s2")

    # Marcações DSCP
    h1.cmd(
        "iptables -t mangle -A POSTROUTING -p udp --dport 5004 -j DSCP --set-dscp-class EF"
    )
    h1.cmd(
        "iptables -t mangle -A POSTROUTING -p udp --dport 5006 -j DSCP --set-dscp-class EF"
    )
    h3.cmd(
        "iptables -t mangle -A POSTROUTING -p udp --dport 5001 -j DSCP --set-dscp-class CS1"
    )

    # Configura QoS em s1 e s2
    setup_qos(s1, "s1-eth3")
    setup_qos(s2, "s2-eth1")

    # Inicia monitoramento de delay com ping
    print("Iniciando monitoramento de latência (ping) de h1 para h2...")
    h1.cmd("ping 10.0.0.2 -i 1 -D > /tmp/ping.log 2>&1 &")

    # Inicia captura de estatísticas de filas
    print("Log de estatísticas de QoS em /tmp/qos.log...")
    s1.cmd(
        "bash -c 'while true; do date +"
        "%Y-%m-%d %H:%M:%S"
        "; ovs-appctl qos/show s1-eth3; sleep 5; done' > /tmp/qos.log 2>&1 &"
    )

    print("Iniciando transmissão RTP de h1 para h2...")
    h1.cmd(
        "ffmpeg -re -i video.mp4 "
        "-map 0:v:0 -c:v libx264 -preset ultrafast -tune zerolatency "
        '-x264-params "keyint=25:scenecut=0:repeat-headers=1" '
        "-f rtp rtp://10.0.0.2:5004?pkt_size=1200 "
        "-map 0:a:0 -c:a aac -ar 44100 -b:a 128k "
        "-f rtp rtp://10.0.0.2:5006?pkt_size=1200 "
        "-sdp_file video.sdp > /tmp/ffmpeg.log 2>&1 &"
    )

    sleep(2)

    print("Iniciando ffplay em h2...")
    h2.cmd(
        'ffplay -report -protocol_whitelist "file,udp,rtp" '
        "-fflags nobuffer -flags low_delay -i video.sdp "
        "> /tmp/ffplay.log 2>&1 &"
    )

    sleep(2)

    print("Iniciando monitoramento de throughput (ifstat)...")
    monitor = s1.popen("ifstat -i s1-eth3 0.5", stdout=sys.stdout)

    sleep(10)

    num_streams = 3
    duration = 20
    print(
        f"Iniciando {num_streams} fluxo(s) iperf UDP de h3 para h4 por {duration} segundos..."
    )
    for i in range(num_streams):
        h3.cmd(f"iperf -c 10.0.0.4 -u -b 3M -t {duration} > /tmp/iperf_{i}.log 2>&1 &")

    print("Executando experimento por mais 40 segundos...")
    sleep(40)

    print("Encerrando monitoramentos...")
    monitor.terminate()
    s1.cmd("pkill -f 'ovs-appctl qos/show'")
    h1.cmd("pkill -f 'ping 10.0.0.2'")

    print("Encerrando rede...")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run()
