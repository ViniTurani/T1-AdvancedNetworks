## Summary of Changes and Techniques

- **Topology Setup**

  - Retained the original Mininet topology: two switches (`s1`, `s2`) and four hosts (`h1`, `h2`, `h3`, `h4`).
  - All host‑to‑switch and switch‑to‑switch links remain at 10 Mb/s using `TCLink`.

- **HTB Queuing on OVS**

  - Enabled Linux‑HTB QoS on the OVS inter‑switch link (`s1-eth3` ↔ `s2-eth1`).
  - Created two HTB queues via `ovs-vsctl`:

  1. **Queue 1**: reserved 8 Mb/s for RTP video/audio.
  2. **Queue 0**: reserved 2 Mb/s for competing iperf traffic.

- **OpenFlow Queue Mapping**

  - Added OpenFlow rules with `ovs-ofctl` on each switch:
    - UDP dst ports **5004** and **5006** → **queue 1** (RTP).
    - UDP dst port **5001** → **queue 0** (iperf).

- **DSCP Marking**
  - On **h1** (RTP sender):
    ```bash
    iptables -t mangle -A POSTROUTING -p udp --dport 5004 -j DSCP --set-dscp-class EF
    iptables -t mangle -A POSTROUTING -p udp --dport 5006 -j DSCP --set-dscp-class EF
    ```
  - On **h3** (iperf sender):
    ```bash
    iptables -t mangle -A POSTROUTING -p udp --dport 5001 -j DSCP --set-dscp-class CS1
    ```

---

With these modifications, the RTP video stream is guaranteed 8 Mb/s of bandwidth and is prioritized over the iperf flows, ensuring smooth video delivery under traffic contention. ```
