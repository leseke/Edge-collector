"""Run the full test suite with external networking blocked.

Loopback TCP is permitted for tests of local-only HTTP services. DNS lookups
and connections to non-loopback addresses remain blocked and are counted.
"""
import ipaddress
import socket
import sys
import unittest

ATTEMPTS = []
_ORIGINAL_CONNECT = socket.socket.connect
_ORIGINAL_CONNECT_EX = socket.socket.connect_ex
_ORIGINAL_GETADDRINFO = socket.getaddrinfo


def _is_loopback_address(address):
    host = address[0] if isinstance(address, tuple) and address else address
    if not isinstance(host, str):
        return False
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _refuse(*a, **k):
    ATTEMPTS.append(repr(a[:2])[:120])
    raise OSError("reseau externe bloque par run_tests_offline")


def _guarded_connect(sock, address):
    if _is_loopback_address(address):
        return _ORIGINAL_CONNECT(sock, address)
    return _refuse(sock, address)


def _guarded_connect_ex(sock, address):
    if _is_loopback_address(address):
        return _ORIGINAL_CONNECT_EX(sock, address)
    return _refuse(sock, address)


def _guarded_getaddrinfo(host, *a, **k):
    if isinstance(host, str) and (host.lower() == "localhost" or _is_loopback_address(host)):
        return _ORIGINAL_GETADDRINFO(host, *a, **k)
    return _refuse(host, *a, **k)


def main():
    socket.socket.connect = _guarded_connect
    socket.socket.connect_ex = _guarded_connect_ex
    socket.getaddrinfo = _guarded_getaddrinfo
    suite = unittest.defaultTestLoader.discover("tests")
    res = unittest.TextTestRunner(verbosity=0).run(suite)
    print(f"Tentatives de connexion reseau externe pendant les tests : {len(ATTEMPTS)}")
    for attempt in ATTEMPTS[:5]:
        print("  ", attempt)
    return 0 if res.wasSuccessful() and not ATTEMPTS else 1


if __name__ == "__main__":
    sys.exit(main())
