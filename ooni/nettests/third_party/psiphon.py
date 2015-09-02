from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.python import usage
from twisted.web.client import ProxyAgent, readBody
from ooni.templates.process import ProcessTest, ProcessDirector
from ooni.utils import log
from ooni.errors import handleAllFailures, TaskTimedOut
import os.path
from os import getenv

class UsageOptions(usage.Options):
    optParameters = [
        ['url', 'u', None, 'Specify a single URL to test.'],]

class PsiphonProcessDirector(ProcessDirector):
    """
    This Process Director monitors Psiphon during its
    bootstrap and fires a callback if bootstrap is
    successful or an errback if it fails to bootstrap
    before timing out.
    """

    def __init__(self, d, timeout=None):
        log.debug("PsiphonProcessDirector:__init__")
        self.d = d
        self.stderr = ""
        self.stdout = ""
        self.finished = None
        self.timeout = timeout
        self.stdin = None
        self.timer = None
        self.exit_reason = None
        self.bootstrapped = defer.Deferred()

    def outReceived(self, data):
        log.debug("PsiphonProcessDirector:outReceived")
        self.stdout += data
        # output received, see if we have bootstrapped
        if not self.bootstrapped.called and "Your SOCKS proxy is now running at 0.0.0.0:1080" in self.stdout:
            log.debug("Bootstrap Detected")
            self.cancelTimer()
            self.bootstrapped.callback("bootstrapped")


class PsiphonTest(ProcessTest):

    """
    This class tests Psiphon (https://psiphon3.com).

    test_psiphon_circumvent
      Starts Psiphon on Linux iand
      determine if it bootstraps successfully or not.
      Then, make a HTTP request for http://google.com
      and records the response body or failure string.

    """

    name = "Psiphon Circumvention Tool Test"
    description = "Bootstraps Psiphon and does a HTTP GET for the specified URL"
    author = "juga"
    version = "0.0.1"
    timeout = 20
    usageOptions = UsageOptions
    #requiredOptions = ['url']
    # FIXME: url should be required

    def setUp(self):
        log.debug("PsiphonTest:setUp")
        self.command = ["psi_start.sh"]
        self.d = defer.Deferred()
        self.processDirector = PsiphonProcessDirector(self.d, timeout=self.timeout)
        self.d.addCallback(self.processEnded, self.command)
        if self.localOptions['url']:
            self.url = self.localOptions['url']
        else:
            self.url = 'http://google.com'
            # FIXME: use http://wtfismyip.com/text

    def runPsiphon(self):
        """
        runs the Psiphon command
        
        """
        log.debug("PsiphonTest:runPsiphon")
        paths = filter(os.path.exists,[os.path.join(os.path.expanduser(x), self.command[0]) for x in getenv('PATH').split(':')])
        log.debug("paths: %s" % (', ').join(paths))
        log.debug("Spawning Psiphon")
        reactor.spawnProcess(self.processDirector, paths[0], self.command)

    def test_psiphon_circumvent(self):
        log.debug("PsiphonTest:test_psiphon_circumvent")
        proxyEndpoint=TCP4ClientEndpoint(reactor, '127.0.0.1',1080 )
        agent = ProxyAgent(proxyEndpoint, reactor)

        def addResultToReport(result):
            log.debug("PsiphonTest:addResultToReport")
            self.report['body'] = result
            self.report['success'] = True

        def addFailureToReport(failure):
            log.debug("PsiphonTest:addFailureToReport")
            self.report['failure'] = handleAllFailures(failure)
            self.report['success'] = False

        def doRequest(noreason):
            """
            Do an HTTP request using Psiphon

            """
            log.debug("PsiphonTest:doRequest")
            log.debug("Doing HTTP request via Psiphon (127.0.0.1:1080) for %s" % self.url)
            request = agent.request("GET", self.url)
            request.addCallback(readBody)
            request.addCallback(addResultToReport)
            request.addCallback(self.processDirector.close)
            return request

        self.processDirector.bootstrapped.addCallback(doRequest)
        self.processDirector.bootstrapped.addErrback(addFailureToReport)
        self.runPsiphon()
        return self.d
