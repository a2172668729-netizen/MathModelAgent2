"""Imported automatically to block Python socket networking for solver runs."""
import os as _os
import socket as _socket
import subprocess as _subprocess


class _BlockedSocket(_socket.socket):
    def connect(self, address):
        raise PermissionError("network access is disabled by MathModelAgent")

    def connect_ex(self, address):
        raise PermissionError("network access is disabled by MathModelAgent")


def _blocked(*args, **kwargs):
    raise PermissionError("network access is disabled by MathModelAgent")


_socket.socket = _BlockedSocket
_socket.create_connection = _blocked
_subprocess.Popen = _blocked
_subprocess.run = _blocked
_subprocess.call = _blocked
_subprocess.check_call = _blocked
_subprocess.check_output = _blocked
_os.system = _blocked
_os.popen = _blocked
