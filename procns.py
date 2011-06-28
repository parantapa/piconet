"""Execute commands in context of different network namespaces

Provides the ProcNS class which can be used execute commands in a different
Linux network namespace. This module depends on the availability of the
unshare function being exported by libc.
"""

from multiprocessing import Process, JoinableQueue
from subprocess import Popen

import signal
from signal import SIG_IGN, SIGINT, SIGQUIT

import ctypes

SHUTDOWN = 1
EXECUTE = 2

DEV_NULL = open("/dev/null", "r+")

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

    libc = ctypes.cdll.LoadLibrary(LIBC_DLL)
    libc.unshare(CLONE_NEWNET)

class RootNS(object):
    """Root network namespace

    New commands can be executed in context of root network namespace
    """

    def __init__(self):
        self.jobs = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        
    def _call(self, cmd, shell=True, fg=True):
        """Execute a command

        cmd   - The command to be executed.
        shell - If true execute as a shell command.
        fg    - If true run in foreground.
        """

        if fg:
            stdin, stdout, stderr = None, None, None
        else:
            stdin, stdout, stderr = DEV_NULL, DEV_NULL, DEV_NULL

        try:
            proc = Popen(cmd, shell=shell, stdin=stdin,
                    stdout=stdout, stderr=stderr)
        except OSError as e:
            print "Error executing: %s\n%s" % (cmd, e)
            return

        if fg:
            proc.communicate()
        else:
            print "[%d] Started" % proc.pid
            self.jobs[proc.pid] = proc

    def _wait(self, killall=False):
        """Wait for any finished background process

        killall - If true terminate all processes before waiting on them.
        """

        if killall:
            for pid, proc in self.jobs.iteritems():
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait()

        for pid, proc in self.jobs.items():
            if proc.poll() is not None:
                print exit_msg(proc.pid, proc.returncode)
                del self.jobs[pid]

    def call(self, cmd, shell=True, fg=True):
        """Execute a command

        cmd   - The command to be executed.
        shell - If true execute the command in a shell.
        fg    - If true execute the command in foreground.
        """

        int_handler = signal.signal(SIGINT, SIG_IGN)
        quit_handler = signal.signal(SIGQUIT, SIG_IGN)

        try:
            self._call(cmd, shell, fg)
        finally:
            signal.signal(SIGINT, int_handler)
            signal.signal(SIGQUIT, quit_handler)

        self._wait(False)

    def close(self):
        """Close the context

        Kill any remaining background processes. Wait for them to finish and
        return.
        """

        self._wait(True)

class ProcNS(RootNS):
    """New network namespace

    New commands can be executed in context of a new network namespace.
    """

    def __init__(self):
        RootNS.__init__(self)
        
        self.queue = JoinableQueue()
        self.main = Process(target=self._mainloop)
        self.main.start()

    def _mainloop(self):
        """Start a process with new network namespace

        This function unshares it's network namespace and loops to execute
        commands sent to it.
        """

        unshare_net()

        signal.signal(SIGINT, SIG_IGN)
        signal.signal(SIGQUIT, SIG_IGN)

        while True:
            todo, cmd, shell, fg = self.queue.get()

            if todo == SHUTDOWN:
                self._wait(True)
                self.queue.task_done()
                return
            else:
                self._call(cmd, shell, fg)
                self.queue.task_done()
                
            self._wait(False)

    def call(self, cmd, shell=True, fg=True):
        """Execute a command

        Check RootNS.call.
        """

        int_handler = signal.signal(SIGINT, SIG_IGN)
        quit_handler = signal.signal(SIGQUIT, SIG_IGN)

        try:
            self.queue.put((EXECUTE, cmd, shell, fg))
            self.queue.join()
        finally:
            signal.signal(SIGINT, int_handler)
            signal.signal(SIGQUIT, quit_handler)

    def close(self):
        """Close the process namespace

        Check RootNS.close.
        """

        self.queue.put((SHUTDOWN, None, None, None))
        self.queue.join()
        self.main.join()

