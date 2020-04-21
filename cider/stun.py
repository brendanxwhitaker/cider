# coding:utf-8
""" Retrieves NAT information from STUN server. """
# Based on: ``https://pypi.python.org/pypi/pystun``.
import random
import socket
import binascii
import logging
from typing import Tuple
from mypy_extensions import TypedDict

# pylint: disable=too-few-public-methods, invalid-name

__version__ = "0.0.4"
log = logging.getLogger("pystun")


def enable_logging() -> None:
    """ Enables logging. """
    logging.basicConfig()
    log.setLevel(logging.DEBUG)


STUN_SERVERS_LIST = (
    "stun.ekiga.net",
    "stunserver.org",
    "stun.ideasip.com",
    "stun.softjoys.com",
    "stun.voipbuster.com",
)

# stun attributes
MappedAddress = "0001"
ResponseAddress = "0002"
ChangeRequest = "0003"
SourceAddress = "0004"
ChangedAddress = "0005"
Username = "0006"
Password = "0007"
MessageIntegrity = "0008"
ErrorCode = "0009"
UnknownAttribute = "000A"
ReflectedFrom = "000B"
XorOnly = "0021"
XorMappedAddress = "8020"
ServerName = "8022"
SecondaryAddress = "8050"  # Non standard extention

# types for a stun message
BindRequestMsg = "0001"
BindResponseMsg = "0101"
BindErrorResponseMsg = "0111"
SharedSecretRequestMsg = "0002"
SharedSecretResponseMsg = "0102"
SharedSecretErrorResponseMsg = "0112"

dictAttrToVal = {
    "MappedAddress": MappedAddress,
    "ResponseAddress": ResponseAddress,
    "ChangeRequest": ChangeRequest,
    "SourceAddress": SourceAddress,
    "ChangedAddress": ChangedAddress,
    "Username": Username,
    "Password": Password,
    "MessageIntegrity": MessageIntegrity,
    "ErrorCode": ErrorCode,
    "UnknownAttribute": UnknownAttribute,
    "ReflectedFrom": ReflectedFrom,
    "XorOnly": XorOnly,
    "XorMappedAddress": XorMappedAddress,
    "ServerName": ServerName,
    "SecondaryAddress": SecondaryAddress,
}

dictMsgTypeToVal = {
    "BindRequestMsg": BindRequestMsg,
    "BindResponseMsg": BindResponseMsg,
    "BindErrorResponseMsg": BindErrorResponseMsg,
    "SharedSecretRequestMsg": SharedSecretRequestMsg,
    "SharedSecretResponseMsg": SharedSecretResponseMsg,
    "SharedSecretErrorResponseMsg": SharedSecretErrorResponseMsg,
}

dictValToMsgType = {}

dictValToAttr = {}

Blocked = "Blocked"
OpenInternet = "Open Internet"
FullCone = "Full Cone"
SymmetricUDPFirewall = "Symmetric UDP Firewall"
RestrictNAT = "Restrict NAT"
RestrictPortNAT = "Restrict Port NAT"
SymmetricNAT = "Symmetric NAT"
ChangedAddressError = "Meet an error, when do Test1 on Changed IP and Port"


def _initialize() -> None:
    items = list(dictAttrToVal.items())
    for i, _ in enumerate(items):
        dictValToAttr.update({items[i][1]: items[i][0]})
    items = list(dictMsgTypeToVal.items())
    for i, _ in enumerate(items):
        dictValToMsgType.update({items[i][1]: items[i][0]})


def gen_tran_id() -> str:
    """ Generates a transaction ID. """
    a = ""
    for _ in range(32):
        a += random.choice("0123456789ABCDEF")  # RFC3489 128bits transaction ID
    # return binascii.a2b_hex(a)
    return a


class NATParameters(TypedDict):
    """ TypeVar for return value of ``stun_test()``. """

    Resp: bool
    ExternalIP: str
    ExternalPort: int
    SourceIP: str
    SourcePort: int
    ChangedIP: str
    ChangedPort: int


def stun_test(
    sock: socket.socket, host: str, port: int, send_data: str = "",
) -> NATParameters:
    """ Connects to a STUN server to determine NAT parameters. """
    # DEBUG
    print("Type of 'sock':", type(sock))

    nat_parameters: NATParameters = {
        "Resp": False,
        "ExternalIP": "",
        "ExternalPort": 0,
        "SourceIP": "",
        "SourcePort": 0,
        "ChangedIP": "",
        "ChangedPort": 0,
    }
    str_len = "%#04d" % (len(send_data) / 2)
    tranid = gen_tran_id()
    str_data = "".join([BindRequestMsg, str_len, tranid, send_data])
    data = binascii.a2b_hex(str_data)
    recv_corr = False
    while not recv_corr:
        recieved = False
        count = 3
        while not recieved:
            log.debug("sendto %s", str((host, port)))
            try:
                sock.sendto(data, (host, port))
            except socket.gaierror:
                nat_parameters["Resp"] = False
                return nat_parameters
            # pylint: disable=broad-except
            try:
                buf, addr = sock.recvfrom(2048)
                log.debug("recvfrom: %s", str(addr))
                recieved = True
            except Exception:
                recieved = False
                if count > 0:
                    count -= 1
                else:
                    nat_parameters["Resp"] = False
                    return nat_parameters
        msgtype = binascii.b2a_hex(buf[0:2]).decode("ascii")
        bind_resp_msg = dictValToMsgType[msgtype] == "BindResponseMsg"
        tranid_match = (
            tranid.upper() == binascii.b2a_hex(buf[4:20]).decode("ascii").upper()
        )
        if bind_resp_msg and tranid_match:
            recv_corr = True
            nat_parameters["Resp"] = True
            len_message = int(binascii.b2a_hex(buf[2:4]).decode("ascii"), 16)
            len_remain = len_message
            base = 20
            while len_remain:
                attr_type = binascii.b2a_hex(buf[base : (base + 2)]).decode("ascii")
                attr_len = int(
                    binascii.b2a_hex(buf[(base + 2) : (base + 4)]).decode("ascii"), 16
                )
                if attr_type == MappedAddress:  # first two bytes: 0x0001
                    port = int(
                        binascii.b2a_hex(buf[base + 6 : base + 8]).decode("ascii"), 16
                    )
                    ip = ".".join(
                        [
                            str(
                                int(
                                    binascii.b2a_hex(buf[base + 8 : base + 9]).decode(
                                        "ascii"
                                    ),
                                    16,
                                )
                            ),
                            str(
                                int(
                                    binascii.b2a_hex(buf[base + 9 : base + 10]).decode(
                                        "ascii"
                                    ),
                                    16,
                                )
                            ),
                            str(
                                int(
                                    binascii.b2a_hex(buf[base + 10 : base + 11]).decode(
                                        "ascii"
                                    ),
                                    16,
                                )
                            ),
                            str(
                                int(
                                    binascii.b2a_hex(buf[base + 11 : base + 12]).decode(
                                        "ascii"
                                    ),
                                    16,
                                )
                            ),
                        ]
                    )
                    nat_parameters["ExternalIP"] = ip
                    nat_parameters["ExternalPort"] = port
                if attr_type == SourceAddress:
                    port = int(
                        binascii.b2a_hex(buf[base + 6 : base + 8]).decode("ascii"), 16
                    )
                    ip = ".".join(
                        [
                            str(
                                int(
                                    binascii.b2a_hex(buf[base + 8 : base + 9]).decode(
                                        "ascii"
                                    ),
                                    16,
                                )
                            ),
                            str(
                                int(
                                    binascii.b2a_hex(buf[base + 9 : base + 10]).decode(
                                        "ascii"
                                    ),
                                    16,
                                )
                            ),
                            str(
                                int(
                                    binascii.b2a_hex(buf[base + 10 : base + 11]).decode(
                                        "ascii"
                                    ),
                                    16,
                                )
                            ),
                            str(
                                int(
                                    binascii.b2a_hex(buf[base + 11 : base + 12]).decode(
                                        "ascii"
                                    ),
                                    16,
                                )
                            ),
                        ]
                    )
                    nat_parameters["SourceIP"] = ip
                    nat_parameters["SourcePort"] = port
                if attr_type == ChangedAddress:
                    port = int(
                        binascii.b2a_hex(buf[base + 6 : base + 8]).decode("ascii"), 16
                    )
                    ip = ".".join(
                        [
                            str(
                                int(
                                    binascii.b2a_hex(buf[base + 8 : base + 9]).decode(
                                        "ascii"
                                    ),
                                    16,
                                )
                            ),
                            str(
                                int(
                                    binascii.b2a_hex(buf[base + 9 : base + 10]).decode(
                                        "ascii"
                                    ),
                                    16,
                                )
                            ),
                            str(
                                int(
                                    binascii.b2a_hex(buf[base + 10 : base + 11]).decode(
                                        "ascii"
                                    ),
                                    16,
                                )
                            ),
                            str(
                                int(
                                    binascii.b2a_hex(buf[base + 11 : base + 12]).decode(
                                        "ascii"
                                    ),
                                    16,
                                )
                            ),
                        ]
                    )
                    nat_parameters["ChangedIP"] = ip
                    nat_parameters["ChangedPort"] = port
                # if attr_type == ServerName:
                # serverName = buf[(base+4):(base+4+attr_len)]
                base = base + 4 + attr_len
                len_remain = len_remain - (4 + attr_len)
    # s.close()
    return nat_parameters


def get_nat_type(
    sock: socket.socket,
    source_ip: str,
    stun_host: str = "",
    stun_port: int = 3478,
) -> Tuple[str, NATParameters]:
    """ Returns the NAT type. """
    _initialize()
    port = stun_port
    log.debug("Do Test1")
    resp = False
    if stun_host:
        ret = stun_test(sock, stun_host, port)
        resp = ret["Resp"]
    else:
        for stun_server_host in STUN_SERVERS_LIST:
            log.debug("Trying STUN host: %s", stun_server_host)
            ret = stun_test(sock, stun_server_host, port)
            resp = ret["Resp"]
            if resp:
                stun_host = stun_server_host
                break
    if not resp:
        return Blocked, ret
    log.debug("Result: %s", ret)
    ex_ip = ret["ExternalIP"]
    ex_port = ret["ExternalPort"]
    changed_ip = ret["ChangedIP"]
    changed_port = ret["ChangedPort"]
    if ret["ExternalIP"] == source_ip:
        change_request = "".join([ChangeRequest, "0004", "00000006"])
        ret = stun_test(sock, stun_host, port, change_request)
        if ret["Resp"]:
            typ = OpenInternet
        else:
            typ = SymmetricUDPFirewall
    else:
        change_request = "".join([ChangeRequest, "0004", "00000006"])
        log.debug("Do Test2")
        ret = stun_test(sock, stun_host, port, change_request)
        log.debug("Result: %s", ret)
        if ret["Resp"]:
            typ = FullCone
        else:
            log.debug("Do Test1")
            ret = stun_test(sock, changed_ip, changed_port)
            log.debug("Result: %s", ret)
            if not ret["Resp"]:
                typ = ChangedAddressError
            else:
                if ex_ip == ret["ExternalIP"] and ex_port == ret["ExternalPort"]:
                    change_port_request = "".join([ChangeRequest, "0004", "00000002"])
                    log.debug("Do Test3")
                    ret = stun_test(
                        sock,
                        changed_ip,
                        port,
                        change_port_request,
                    )
                    log.debug("Result: %s", ret)
                    if ret["Resp"]:
                        typ = RestrictNAT
                    else:
                        typ = RestrictPortNAT
                else:
                    typ = SymmetricNAT
    return typ, ret


def get_ip_info(
    source_ip: str = "0.0.0.0",
    source_port: int = 54320,
    stun_host: str = "",
    stun_port: int = 3478,
) -> Tuple[str, str, int]:
    """ Returns the NAT type. """
    socket.setdefaulttimeout(2)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((source_ip, source_port))
    nat_type, nat = get_nat_type(
        s, source_ip, stun_host=stun_host, stun_port=stun_port
    )
    external_ip = nat["ExternalIP"]
    external_port = nat["ExternalPort"]
    s.close()
    socket.setdefaulttimeout(None)
    return nat_type, external_ip, external_port


def main() -> None:
    """ Prints the NAT type. """
    nat_type, external_ip, external_port = get_ip_info()
    print("NAT Type:", nat_type)
    print("External IP:", external_ip)
    print("External Port:", external_port)


if __name__ == "__main__":
    main()
