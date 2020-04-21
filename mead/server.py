#!/usr/bin/env python
# coding:utf-8
""" Starts a UDP server listening for connecting clients. """
import sys
import socket
import struct
from typing import Dict, Tuple
from collections import namedtuple

# pylint: disable=invalid-name

FullCone = "Full Cone"  # 0
RestrictNAT = "Restrict NAT"  # 1
RestrictPortNAT = "Restrict Port NAT"  # 2
SymmetricNAT = "Symmetric NAT"  # 3
UnknownNAT = "Unknown NAT"  # 4
NATTYPE = (FullCone, RestrictNAT, RestrictPortNAT, SymmetricNAT, UnknownNAT)


def addr2bytes(addr: Tuple[str, int], nat_type_id: str) -> bytes:
    """ Convert an address-NATtype pair to a hash. """
    host, port = addr
    try:
        host = socket.gethostbyname(host)
    except (socket.gaierror, socket.error):
        raise ValueError("invalid host")
    try:
        port = int(port)
    except ValueError:
        raise ValueError("invalid port")
    try:
        nat_type_idx = int(nat_type_id)
    except ValueError:
        raise ValueError("invalid NAT type")
    byte_address = socket.inet_aton(host)
    byte_address += struct.pack("H", port)
    byte_address += struct.pack("H", nat_type_idx)
    return byte_address


def main() -> None:
    """ Starts a UDP server listening for connecting clients. """
    port = int(sys.argv[1])

    sockfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sockfd.bind(("", port))
    print("listening on *:%d (udp)" % port)

    ClientInfo = namedtuple("ClientInfo", "addr, nat_type_id")
    channel_map: Dict[str, ClientInfo] = {}

    while True:
        # Receive a channel and NAT type from a client.
        data_bytes, addr = sockfd.recvfrom(1024)
        data = data_bytes.decode("ascii")
        channel, nat_type_id = data.strip().split()
        print("connection from %s:%d" % addr)

        # Tell the client ``ok``, it is connected to the channel.
        ok_msg_bytes = ("ok %s" % channel).encode("ascii")
        sockfd.sendto(ok_msg_bytes, addr)

        # Display channel and NAT type.
        nat_type = NATTYPE[int(nat_type_id)]
        print("channel=%s, nat_type=%s, ok sent to client" % (channel, nat_type))

        # Wait until the client confirms it received the ``ok``.
        data_bytes, addr = sockfd.recvfrom(2)
        data = data_bytes.decode("ascii")
        if data != "ok":
            continue

        print("request received for channel:", channel)

        # Attempt to match client with an already-connected client on same channel.
        if channel in channel_map:

            # Get addresses of peers.
            addr_a = channel_map[channel].addr
            addr_b = addr

            # Get NAT types of peers.
            nat_type_id_a = channel_map[channel].nat_type_id
            nat_type_id_b = nat_type_id

            sockfd.sendto(addr2bytes(addr_a, nat_type_id_a), addr_b)
            sockfd.sendto(addr2bytes(addr_b, nat_type_id_b), addr_a)
            print("linked", channel)

            # Safely remove channel from queue.
            channel_map.pop(channel, None)

        # Otherwise, add client to the channel_map on its requested channel.
        else:
            channel_map[channel] = ClientInfo(addr, nat_type_id)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: server.py port")
        sys.exit()
    else:
        assert sys.argv[1].isdigit(), "port should be a number!"
        main()
