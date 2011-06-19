"""Process Namespace

Create python processes to execute external commands in that namespace.
Depends on the python-unshare module for creating separate network namespace.
"""

from multiprocessing import Process, JoinableQueue
from subprocess import Popen

import os
import atexit
import signal

from unshare import unshare, CLONE_NEWNET

FOREGROUND = 1
BACKGROUND = 2
SHUTDOWN = 10

def exit_msg(proc):
    """Return human readable exit message"""

    if proc.returncode is None:
        return "[{0}] Running".format(proc.pid)
    elif proc.returncode < 0:
        for name, val in signal.__dict__.iteritems():
            if name.startswith("SIG") and val == -proc.returncode:
                return "[{0}] Killed {1}".format(proc.pid, name)
        return "[{0}] Killed Signal({1})".format(proc.pid, -proc.returncode)
    else:
        return "[{0}] Done {1}".format(proc.pid, proc.returncode)

class ProcNS(object):
    """New process namespace

    New commands can be executed in the context of this process.
    """

    def __init__(self):
        self.main = Process(target=self.boot)
        self.queue = JoinableQueue()

        atexit.register(self.shutdown)        
        self.main.start()

    def boot(self):
        """Start the process namespace
        
        The main function which executes the commands, keeps record of
        background processes, and waits for them to finish.
        """

        procs = {}
        devnull = open(os.devnull, "r+")

        while True:
            todo, args, kwargs = self.queue.get()

            if todo == SHUTDOWN:
                for pid, proc in procs.iteritems():
                    if proc.poll() is None:
                        proc.terminate()
                    proc.wait()
                    print exit_msg(proc)
                self.queue.task_done()
                return

            try:
                if todo == FOREGROUND:
                    proc = Popen(*args, **kwargs)
                    proc.communicate()
                elif todo == BACKGROUND:
                    kwargs["stdin"] = devnull
                    kwargs["stdout"] = devnull
                    kwargs["stderr"] = devnull

                    proc = Popen(*args, **kwargs)
                    print "[{0}] Started".format(proc.pid)

                    procs[proc.pid] = proc
            except OSError as e:
                print "Error executing: {0} {1}".format(args, kwargs)
                print e

            for pid, proc in procs.items():
                if proc.poll() is not None:

                    print exit_msg(proc)
                    del procs[pid]

            self.queue.task_done()

    def call(self, *args, **kwargs):
        """Execute a command in process namespace and wait

        Arguments are same as that of subprocess.Popen. After creating the
        process the caller calls communicate() for it to finish.
        """

        self.queue.put((FOREGROUND, args, kwargs))
        self.queue.join()

    def call_bg(self, *args, **kwargs):
        """Execute a command in process namespace and dont wait

        Arguments are same as that of subprocess.Popen. After creating the
        process it is stored in an internal list and checked for completion at
        the end of every internal loop.

        Note: stdin, stdout, and stderr are redirected to /dev/null
        """

        self.queue.put((BACKGROUND, args, kwargs))
        self.queue.join()

    def shutdown(self):
        """Shutdown the process namespace

        Send terminate to all processes that are still running and close the
        process namespace.
        """

        self.queue.put((SHUTDOWN, None, None))
        self.queue.join()
        self.main.join()

class NetNS(ProcNS):
    """New network namespace

    Commands executed in context of this see a different network namespace.  
    """
    
    def boot(self):
        """Boot into a new network namespace"""

        unshare(CLONE_NEWNET)
        ProcNS.boot(self)

