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
    """Convert an address pair to a hash."""
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

    # A,B with addr_A,addr_B,pool=100
    # temp state {100:(nat_type_id, addr_A, addr_B)}
    # final state {addr_A:addr_B, addr_B:addr_A}
    symmetric_chat_clients: Dict[Tuple[str, int], Tuple[str, Tuple[str, int]]] = {}
    ClientInfo = namedtuple("ClientInfo", "addr, nat_type_id")
    poolqueue: Dict[str, ClientInfo] = {}
    while True:
        data_bytes, addr = sockfd.recvfrom(1024)
        data = data_bytes.decode("ascii")
        if data.startswith("msg "):
            # forward symmetric chat msg, act as TURN server
            try:
                sockfd.sendto(data_bytes[4:], symmetric_chat_clients[addr][1])
                print(
                    (
                        "msg successfully forwarded to {0}".format(
                            symmetric_chat_clients[addr][1]
                        )
                    )
                )
                print((data[4:]))
            except KeyError:
                print("something is wrong with symmetric_chat_clients!")
        else:
            # help build connection between clients, act as STUN server
            print("connection from %s:%d" % addr)
            pool, nat_type_id = data.strip().split()
            ok_msg_bytes = ("ok {0}".format(pool)).encode("ascii")
            sockfd.sendto(ok_msg_bytes, addr)
            print(
                (
                    "pool={0}, nat_type={1}, ok sent to client".format(
                        pool, NATTYPE[int(nat_type_id)]
                    )
                )
            )
            data_bytes, addr = sockfd.recvfrom(2)
            data = data_bytes.decode("ascii")
            if data != "ok":
                continue

            print("request received for pool:", pool)

            try:
                addr_a, addr_b = poolqueue[pool].addr, addr
                nat_type_id_a, nat_type_id_b = poolqueue[pool].nat_type_id, nat_type_id
                sockfd.sendto(addr2bytes(addr_a, nat_type_id_a), addr_b)
                sockfd.sendto(addr2bytes(addr_b, nat_type_id_b), addr_a)
                print("linked", pool)
                del poolqueue[pool]
            except KeyError:
                poolqueue[pool] = ClientInfo(addr, nat_type_id)

            if (pool, 0) in symmetric_chat_clients:
                if nat_type_id == "3" or symmetric_chat_clients[(pool, 0)][0] == "3":
                    # at least one is symmetric NAT
                    recorded_client_addr = symmetric_chat_clients[(pool, 0)][1]
                    symmetric_chat_clients[addr] = ("", recorded_client_addr)
                    symmetric_chat_clients[recorded_client_addr] = ("", addr)
                    print("Hurray! symmetric chat link established.")
                    del symmetric_chat_clients[(pool, 0)]
                else:
                    # Neither of the clients are symmetric NATs.
                    del symmetric_chat_clients[(pool, 0)]
            else:
                symmetric_chat_clients[(pool, 0)] = (nat_type_id, addr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: server.py port")
        sys.exit()
    else:
        assert sys.argv[1].isdigit(), "port should be a number!"
        main()
