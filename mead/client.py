#!/usr/bin/env python
# coding:utf-8
""" Start a UDP NAT traversal client. """
import sys
import time
import socket
import struct
from typing import Tuple, Callable
from threading import Thread

import multiprocessing as mp
from multiprocessing.connection import Connection

# pylint: disable=invalid-name

FullCone = "Full Cone"  # 0
RestrictNAT = "Restrict NAT"  # 1
RestrictPortNAT = "Restrict Port NAT"  # 2
SymmetricNAT = "Symmetric NAT"  # 3
UnknownNAT = "Unknown NAT"  # 4
NATTYPE = (FullCone, RestrictNAT, RestrictPortNAT, SymmetricNAT, UnknownNAT)


class Client:
    """ The UDP client for interacting with the server and other Clients. """

    def __init__(
        self,
        server_ip: str,
        port: int,
        channel: str,
        funnel: Connection,
        spout: Connection,
    ) -> None:
        self.master = (server_ip, port)
        self.channel = channel
        self.sockfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # If testing with server and both clients on localhost, use ``127.0.0.1``.
        self.target: Tuple[str, int] = ("", 0)
        self.peer_nat_type = ""

        self.funnel = funnel
        self.spout = spout

    def request_for_connection(self, nat_type_id: str = "0") -> None:
        """ Send a request to the server for a connection. """
        # Create a socket.
        self.sockfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Send channel and NAT type to server, requesting a connection.
        msg = (self.channel + " {0}".format(nat_type_id)).encode("ascii")
        self.sockfd.sendto(msg, self.master)

        # Wait for ``ok``, acknowledgement of request.
        data, _ = self.sockfd.recvfrom(len(self.channel) + 3)
        if data.decode("ascii") != "ok " + self.channel:
            print("unable to request!")
            sys.exit(1)

        # Confirm we've received the ``ok``, tell server to connect us to channel.
        self.sockfd.sendto("ok".encode("ascii"), self.master)

        # Wait for a partner.
        print("request sent, waiting for partner in channel '%s'..." % self.channel)
        data, _ = self.sockfd.recvfrom(8)

        # Decode the partner's address and NAT type.
        self.target, peer_nat_type_id = bytes2addr(data)
        print((self.target, peer_nat_type_id))
        self.peer_nat_type = NATTYPE[peer_nat_type_id]

        # Get target address and port.
        addr, port = self.target
        print("connected to %s:%s with NAT type: %s" % (addr, port, self.peer_nat_type))

    def recv_msg(self, sock: socket.socket) -> None:
        """ Receive message callback. """
        while True:
            data_bytes, addr = sock.recvfrom(1024)
            data = data_bytes.decode("ascii")
            if addr in (self.target, self.master):
                self.funnel.send(data)

    def send_msg(self, sock: socket.socket) -> None:
        """ Send message callback. """
        while True:
            data = self.spout.recv()
            data_bytes = data.encode("ascii")
            sock.sendto(data_bytes, self.target)

    @staticmethod
    def chat_fullcone(
        send: Callable[[socket.socket], None],
        recv: Callable[[socket.socket], None],
        sock: socket.socket,
    ) -> None:
        """ Start the send and recv threads. """
        ts = Thread(target=send, args=(sock,))
        ts.setDaemon(True)
        ts.start()
        tr = Thread(target=recv, args=(sock,))
        tr.setDaemon(True)
        tr.start()

    def main(self) -> None:
        """ Start a chat session. """
        # Connect to the server and request a channel.
        self.request_for_connection(nat_type_id="0")

        # Chat with peer.
        print("FullCone chat mode")
        self.chat_fullcone(self.send_msg, self.recv_msg, self.sockfd)

        # Let the threads run.
        while True:
            try:
                time.sleep(0.5)
            except KeyboardInterrupt:
                print("exit")
                sys.exit()


def bytes2addr(bytes_address: bytes) -> Tuple[Tuple[str, int], int]:
    """Convert a hash to an address pair."""
    if len(bytes_address) != 8:
        raise ValueError("invalid bytes_address")
    host = socket.inet_ntoa(bytes_address[:4])

    # Unpack returns a tuple even if it contains exactly one item.
    port = struct.unpack("H", bytes_address[-4:-2])[0]
    nat_type_id = struct.unpack("H", bytes_address[-2:])[0]
    target = (host, port)
    return target, nat_type_id


def get_stdin(in_funnel: Connection) -> None:
    """ Send stdin from shell through client to peer. """
    while 1:
        data = sys.stdin.readline().replace("\n", "")
        in_funnel.send(data)


def recv_stdout(out_spout: Connection) -> None:
    """ Print received messages. """
    while 1:
        data = out_spout.recv()
        print("PUBLIC: stdout:", data)


def main() -> None:
    """ Run the client as a standlone script. """
    # Set defaults.
    server_ip = "127.0.0.1"
    port = 8000
    channel = "100"

    # Parse command-line arguments.
    if len(sys.argv) != 4:
        print("usage: %s <host> <port> <channel>" % sys.argv[0])
        sys.exit(65)
    server_ip = sys.argv[1]
    port = int(sys.argv[2])
    channel = sys.argv[3].strip()

    # Create pipe for communication.
    in_funnel, in_spout = mp.Pipe()
    out_funnel, out_spout = mp.Pipe()

    p_out = mp.Process(target=recv_stdout, args=(out_spout,))
    p_out.start()

    # Create and start the client.
    c = Client(server_ip, port, channel, out_funnel, in_spout)
    p_client = mp.Process(target=c.main)
    p_client.start()

    get_stdin(in_funnel)


if __name__ == "__main__":
    main()
