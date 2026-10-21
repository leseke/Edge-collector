"""Execute TOUTE la suite avec le reseau coupe (sockets bloques).
python -m tools.run_tests_offline
Tout test tentant une connexion echoue ; le nombre de tentatives est affiche."""
import socket
import sys
import unittest

ATTEMPTS = []


def _refuse(*a, **k):
    ATTEMPTS.append(repr(a[:2])[:120])
    raise OSError("reseau coupe par run_tests_offline")


def main():
    socket.socket.connect = _refuse
    socket.socket.connect_ex = _refuse
    socket.create_connection = _refuse
    socket.getaddrinfo = _refuse
    suite = unittest.defaultTestLoader.discover("tests")
    res = unittest.TextTestRunner(verbosity=0).run(suite)
    print(f"Tentatives de connexion reseau pendant les tests : {len(ATTEMPTS)}")
    for a in ATTEMPTS[:5]:
        print("  ", a)
    return 0 if res.wasSuccessful() and not ATTEMPTS else 1


if __name__ == "__main__":
    sys.exit(main())
