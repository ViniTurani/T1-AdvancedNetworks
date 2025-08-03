# Network Emulation with Mininet

## Objective

Simulate a network with video transmission using RTP between two nodes, degrade video quality using `iperf` traffic, and then apply QoS to preserve video quality. This guide is intended for computers running Ubuntu Linux or other Debian-based distributions. If needed, we recommend using a [virtual machine](https://www.osboxes.org/ubuntu/#ubuntu-24-04-vbox) with Ubuntu 24.04 for VirtualBox.

## Install Mininet

Install the required packages:

```bash
sudo apt-get install mininet
sudo apt-get install openvswitch-testcontroller
sudo apt-get install iperf ifstat
```

Kill the local controller:

```bash
sudo killall ovs-testcontroller
```

## Test video streaming via RTP

Download a sample video to the local machine:

```bash
wget https://download.blender.org/durian/trailer/sintel_trailer-480p.mp4 -O video.mp4
```

Install ffmpeg:

```bash
sudo apt-get install ffmpeg
```

To allow the video player (executed as root inside Mininet) to access the sound system and display windows on the user interface, it is necessary to grant root user permission to use the X server. Run the following command in the terminal before starting the experiment:

```bash
xhost +SI:localuser:root
```

Run the experiment:

```bash
sudo python3 experimento.py
```

## Clean up the environment after emulation

When Mininet is abruptly stopped, it may be necessary to perform a cleanup of the environment.

Run this command to remove virtual interfaces, bridges, and lingering Mininet processes:

```bash
sudo mn -c
```

## References:

- Get Started With Mininet: https://mininet.org/download/  
- Ubuntu 24.04 Virtual Machine: https://www.osboxes.org/ubuntu/#ubuntu-24-04-VirtualBox
