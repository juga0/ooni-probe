from twisted.internet import protocol, defer, reactor

from ooni.nettest import NetTestCase
from ooni.utils import log


class ProcessDirector(protocol.ProcessProtocol):
    def __init__(self, d, finished=None, timeout=None, stdin=None, readHook=None):
        self.d = d
        self.stderr = ""
        self.stdout = ""
        self.finished = finished
        self.timeout = timeout
        self.stdin = stdin
        self.readHook = readHook
        # FIXME: remove this
        # is this overwritting a class attribute?
        # self.exited = False

        self.timer = None
        self.exit_reason = None

    def cancelTimer(self):
        if self.timeout and self.timer:
            self.timer.cancel()
            self.timer = None

    def close(self, reason=None):
        self.reason = reason
        self.transport.loseConnection()
        # FIXME: remove this
        # if not self.exited:
        #    self.transport.signalProcess('INT')

    def resetTimer(self):
        if self.timeout is not None:
            if self.timer is not None and self.timer.active():
                self.timer.cancel()
            self.timer = reactor.callLater(self.timeout,
                                           self.close,
                                           "timeout_reached")

    def finish(self, exit_reason=None):
        if not self.exit_reason:
            self.exit_reason = exit_reason
        data = {
            "stderr": self.stderr,
            "stdout": self.stdout,
            "exit_reason": self.exit_reason
        }
        self.d.callback(data)

    def shouldClose(self):
        if self.finished is None:
            return False
        return self.finished(self.stdout, self.stderr)

    def connectionMade(self):
        self.resetTimer()
        if self.stdin is not None:
            self.transport.write(self.stin)
            self.transport.closeStdin()

    def outReceived(self, data):
        log.debug("STDOUT: %s" % data)
        self.stdout += data
        if self.shouldClose():
            self.close("condition_met")
        self.handleRead(data,  None)

    def errReceived(self, data):
        log.debug("STDERR: %s" % data)
        self.stderr += data
        if self.shouldClose():
            self.close("condition_met")
        self.handlRead(None,  data)

    def inConnectionLost(self):
        log.debug("inConnectionLost")
        # self.d.callback(self.data())

    def outConnectionLost(self):
        log.debug("outConnectionLost")

    def errConnectionLost(self):
        log.debug("errConnectionLost")

    def processExited(self, reason):
        log.debug("Exited %s" % reason)
        # FIXME: remove this
        # self.exited = True

    def processEnded(self, reason):
        log.debug("Ended %s" % reason)
        self.finish("process_done")

    # arturo suggestion
    def handleRead(self,  stdout,  stderr=None):
        log.debug("ProcessDirector: handleRead stdout: %s, stderr: %s" % (stdout,  stderr))


class ProcessTest(NetTestCase):
    name = "Base Process Test"
    version = "0.1"

    requiresRoot = False
    timeout = 5
    
    # arturo suggestion?
    processDirector = None

    def _setUp(self):
        super(ProcessTest, self)._setUp()

    def processEnded(self, result, command):
        log.debug("Finished %s: %s" % (command, result))
        key = ' '.join(command)
        self.report[key] = {
            'stdout': result['stdout'],
            'stderr': result['stderr'],
            'exit_reason': result['exit_reason']
        }
        return result

    def run(self, command, finished=None, readHook=None):
        d = defer.Deferred()
        d.addCallback(self.processEnded, command)
        # XXX make this into a class attribute

        # arturo suggestion
        self.processDirector = ProcessDirector(d, finished, self.timeout)
        self.processDirector.handleRead = self.handleRead
        
        reactor.spawnProcess(self.processDirector, command[0], command, usePTY=usePTY, path=path, env=env)
        return d

    # arturo suggestion: handleRead as an abstract method
    def handleRead(self,  stdout,  stderr=None):        
        pass

    def stop(self):
        log.debug("ProcessTest: stop")
        self.processDirector.close()
