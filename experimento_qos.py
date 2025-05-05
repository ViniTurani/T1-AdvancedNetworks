#!/usr/bin/env python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.node import OVSKernelSwitch, DefaultController
from mininet.log import setLogLevel
from time import sleep
import sys

class RTPTopo(Topo):
    def build(self):
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        h1 = self.addHost('h1')  # vídeo origem
        h2 = self.addHost('h2')  # vídeo destino
        h3 = self.addHost('h3')  # iperf origem
        h4 = self.addHost('h4')  # iperf destino

        # Links de 10 Mbit entre nós
        self.addLink(h1, s1, cls=TCLink, bw=10)
        self.addLink(h3, s1, cls=TCLink, bw=10)
        self.addLink(h2, s2, cls=TCLink, bw=10)
        self.addLink(h4, s2, cls=TCLink, bw=10)
        self.addLink(s1, s2, cls=TCLink, bw=10)


def show_tc_config(switch, iface):
    print(f"=== TC config em {iface} de {switch.name} ===")
    print(switch.cmd(f'tc qdisc show dev {iface}'))
    print(switch.cmd(f'tc class show dev {iface}'))
    print(switch.cmd(f'tc filter show dev {iface}'))


def apply_htb_reserve_qos(switch, iface):
    # Limpa configurações anteriores
    switch.cmd(f'tc qdisc del dev {iface} root')

    # Qdisc root HTB
    switch.cmd(f'tc qdisc add dev {iface} root handle 1: htb default 2')

    # Classe 1:1 RTP reserva 6 Mbit
    switch.cmd(
        f'tc class add dev {iface} parent 1:0 classid 1:1 '
        f'htb rate 6mbit ceil 6mbit burst 15k cburst 15k'
    )
    # fq_codel para reduzir jitter
    switch.cmd(
        f'tc qdisc add dev {iface} parent 1:1 handle 10: fq_codel limit 1000 target 5ms'
    )

    # Classe 1:2 Best-Effort até 4 Mbit
    switch.cmd(
        f'tc class add dev {iface} parent 1:0 classid 1:2 '
        f'htb rate 4mbit ceil 4mbit burst 15k cburst 15k'
    )
    switch.cmd(
        f'tc qdisc add dev {iface} parent 1:2 handle 20: sfq perturb 10'
    )

    # Filtros RTP → 1:1
    for port in (5004, 5006):
        switch.cmd(
            f'tc filter add dev {iface} protocol ip parent 1:0 prio 1 u32 '
            f'match ip dport {port} 0xffff flowid 1:1'
        )


def run():
    topo = RTPTopo()
    net = Mininet(
        topo=topo,
        link=TCLink,
        switch=OVSKernelSwitch,
        controller=DefaultController
    )
    net.start()

    h1, h2, h3, h4 = net.get('h1', 'h2', 'h3', 'h4')
    s1, s2 = net.get('s1', 's2')

    print("Aplicando QoS: reserva 6Mbit para RTP no link s1-eth3...")
    apply_htb_reserve_qos(s1, 's1-eth3')
    show_tc_config(s1, 's1-eth3')

    # Preparar vídeo
    print("Preparando vídeo em h1...")
    h1.cmd(
        'if [ ! -f video.mp4 ]; then wget ' \
        'https://download.blender.org/durian/trailer/sintel_trailer-480p.mp4 -O video.mp4; fi'
    )

    # Iniciar RTP
    print("Iniciando RTP (h1 → h2)...")
    h1.cmd(
        'ffmpeg -re -i video.mp4 '
        '-map 0:v:0 -c:v libx264 -preset ultrafast -tune zerolatency '
        '-x264-params "keyint=25:scenecut=0:repeat-headers=1" '
        '-f rtp rtp://10.0.0.2:5004?pkt_size=1200 '
        '-map 0:a:0 -c:a aac -ar 44100 -b:a 128k '
        '-f rtp rtp://10.0.0.2:5006?pkt_size=1200 '
        '-sdp_file video.sdp > /tmp/ffmpeg.log 2>&1 &'
    )
    sleep(2)

    # Iniciar ffplay
    print("Iniciando reprodução em h2...")
    h2.cmd(
        'ffplay -protocol_whitelist file,udp,rtp -fflags nobuffer '
        '-flags low_delay -i video.sdp > /tmp/ffplay.log 2>&1 &'
    )
    sleep(2)

    # Iniciar monitor antes do iperf
    print("Monitorando tráfego s1-eth3...")
    monitor = s1.popen('ifstat -i s1-eth3 0.5', stdout=sys.stdout)

    # Espera 10s para acumular dados RTP
    sleep(10)

    # Iniciar iperf para gerar carga por 20s
    num_streams = 3
    duration = 20
    print(f"Iniciando {num_streams} fluxos iperf UDP (h3 → h4) por {duration}s...")
    for i in range(num_streams):
        h3.cmd(f'iperf -c 10.0.0.4 -u -b 3M -t {duration} > /tmp/iperf_{i}.log 2>&1 &')

    # Continua monitorando por mais 40s
    sleep(duration + 40)

    print("Encerrando monitoramento e rede...")
    monitor.terminate()
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()
