"""Execute commands in context of different network namespaces

Provides the NetNS class which can be used execute commands in a different
Linux network namespace. This module depends on the availability of the
unshare function being exported by libc.
"""

from multiprocessing import Process, JoinableQueue
from subprocess import Popen

import signal
from signal import SIGINT, SIGQUIT, SIGKILL, SIG_IGN

from misc import exit_msg, unshare_net, block_signal, Closeable

SHUTDOWN = 1
EXECUTE = 2

DEV_NULL = open("/dev/null", "r+")

class RootNS(Closeable):
    """Root network namespace

    New commands can be executed in context of root network namespace
    """

    def __init__(self):
        self.jobs = {}

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

        killall - If true send SIGKILL all processes before waiting on them.
        """

        if killall:
            for pid, proc in self.jobs.iteritems():
                if proc.poll() is None:
                    proc.send_signal(SIGKILL)
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

        with block_signal():
            self._call(cmd, shell, fg)

        self._wait(False)

    def close(self):
        """Close the context

        Kill any remaining background processes. Wait for them to finish and
        return.
        """

        self._wait(True)

class NetNS(RootNS):
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

        try:
            unshare_net()
        except OSError as e:
            print "Failed to create new network namespace\n%s" % e
            return

        signal.signal(SIGINT, SIG_IGN)
        signal.signal(SIGQUIT, SIG_IGN)

        while True:
            msg = self.queue.get()
            try:
                todo, cmd, shell, fg = msg

                if todo == SHUTDOWN:
                    self._wait(True)
                    return
                else:
                    self._call(cmd, shell, fg)
            finally:
                self.queue.task_done()

            self._wait(False)

    def call(self, cmd, shell=True, fg=True):
        """Execute a command

        Check RootNS.call.
        """

        with block_signal():
            self.queue.put((EXECUTE, cmd, shell, fg))
            self.queue.join()

    def close(self):
        """Close the process namespace

        Check RootNS.close.
        """

        self.queue.put((SHUTDOWN, None, None, None))
        self.queue.join()
        self.main.join()

