"""Misc routines

Stuff that doesn't really fit in other files
"""

import signal
from signal import SIG_IGN, SIGINT, SIGQUIT

import os
import ctypes
from contextlib import contextmanager

LIBC_DLL = "libc.so.6"
CLONE_NEWNET = 0x40000000

def exit_msg(pid, returncode):
    """Return human readable exit message"""

    if returncode is None:
        return "[%d] Running" % pid
    elif returncode < 0:
        for name, val in signal.__dict__.iteritems():
            if name.startswith("SIG") and val == -returncode:
                return "[%d] Killed %s" % (pid, name)
        return "[%d] Killed Signal(%d)" % (pid, -returncode)
    else:
        return "[%d] Done %d" % (pid, returncode)

def unshare_net():
    """Unshare the network namespace"""

    libc = ctypes.CDLL(LIBC_DLL, use_errno=True)

    unshare = libc.unshare
    unshare.argtypes = [ctypes.c_int]
    unshare.restype = ctypes.c_int

    if unshare(CLONE_NEWNET) == -1:
        raise OSError(os.strerror(ctypes.get_errno()))

@contextmanager
def block_signal():
    """Block SIGINT and SIGQUIT inside a contexts"""

    int_handler = signal.signal(SIGINT, SIG_IGN)
    quit_handler = signal.signal(SIGQUIT, SIG_IGN)

    yield

    signal.signal(SIGINT, int_handler)
    signal.signal(SIGQUIT, quit_handler)

def id_to_tup(id):
    """Create a three byte tuple form and integer id"""

    id = int(id)

    aa = id % 256
    id = (id - aa) / 256
    bb = id % 256
    id = (id - bb) / 256
    cc = id % 256

    return (cc, bb, aa)

def id_to_ip(id):
    """Create an ip from the an integer id"""

    return "10.%d.%d.%d" % id_to_tup(id)

def id_to_mac(id):
    """Create a ethernet address from an integer id"""

    return "00:00:00:%02x:%02x:%02x" % id_to_tup(id)

class Closeable(object):
    """A class that supports the close method

    Can be used instead of using the contextlib.closing method
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        """Needs to be overridden in subclass"""
        pass
