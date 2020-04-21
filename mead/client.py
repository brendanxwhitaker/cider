#!/usr/bin/env python
# coding:utf-8
""" Start a UDP NAT traversal client. """
import sys
import time
import socket
import struct
from typing import Tuple, Callable
from threading import Thread

# pylint: disable=invalid-name

FullCone = "Full Cone"  # 0
RestrictNAT = "Restrict NAT"  # 1
RestrictPortNAT = "Restrict Port NAT"  # 2
SymmetricNAT = "Symmetric NAT"  # 3
UnknownNAT = "Unknown NAT"  # 4
NATTYPE = (FullCone, RestrictNAT, RestrictPortNAT, SymmetricNAT, UnknownNAT)


class Client:
    """ The UDP client for interacting with the server and other Clients. """

    def __init__(self, server_ip: str, port: int, channel: str) -> None:
        self.master = (server_ip, port)
        self.channel = channel
        self.sockfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target: Tuple[str, int] = ("", 0)
        self.peer_nat_type = ""

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

                if "ECHOED" not in data:
                    self.echo_msg(sock, data)
                else:
                    print("%.10f:" % time.time(), data)

    def echo_msg(self, sock: socket.socket, msg: str) -> None:
        """ Echo message callback. """
        data = "ECHOED: " + msg
        data_bytes = data.encode("ascii")
        sock.sendto(data_bytes, self.target)

    def send_msg(self, sock: socket.socket) -> None:
        """ Send message callback. """
        while True:
            data = sys.stdin.readline()
            print("%.10f:" % time.time(), data)
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
        self.request_for_connection(nat_type_id=NATTYPE[0])

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

    # Create and start the client.
    c = Client(server_ip, port, channel)
    c.main()


if __name__ == "__main__":
    main()
