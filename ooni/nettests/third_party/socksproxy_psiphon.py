from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.web.client import readBody
from twisted.python import usage

from txsocksx.http import SOCKS5Agent

from ooni.errors import handleAllFailures, TaskTimedOut
from ooni.utils import log
from ooni.templates import process, httpt
from ooni.templates.process import ProcessTest


class UsageOptions(usage.Options):
    log.debug("UsageOptions")
    optParameters = [
        ['url', 'u', None, 'Specify a single URL to test.'],
        ['psiphonpath', 'p', None, 'Specify psiphon python client path.'],
        ['socksproxy', 's', None, 'Specify psiphon socks proxy ip:port.'],]


class PsiphonTest(httpt.HTTPTest,  process.ProcessTest):
    
    """
    This class tests Psiphon python client
    
    test_psiphon:
      Starts a Psiphon, check if it bootstraps successfully
      (print a line in stderr).
      Then, perform an HTTP request using the proxy
    """

    name = "Psiphon Test"
    description = "Bootstraps a Psiphon and \
                does a HTTP GET for the specified URL"
    author = "juga"
    version = "0.0.1"
    timeout = 20
    usageOptions = UsageOptions
    # FIXME: url should not be required, so this should be eliminated
    #requiredOptions = ['url']

    # FIXME: even if we inherit first from HTTPTest, its _setUp is not
    #  being called,only the one from ProcessTest
    def setUp(self):
        log.debug('PsiphonTest: setUp')
        log.debug(str(PsiphonTest.__mro__))

        self.bootstrapped = defer.Deferred()
        if self.localOptions['url']:
            self.url = self.localOptions['url']
        else:
            # FIXME: use http://google.com?
            self.url = 'https://wtfismyip.com/text'

        #log.debug('PsiphonTest:setUp, socksproxy')
        #log.debug(self.localOptions.get('socksproxy',  ''))

        # FIXME: is this the correct way to pass socksproxy?
        if self.localOptions['socksproxy']:
            self.socksproxy = self.localOptions['socksproxy']
        else:
            self.socksproxy = '127.0.0.1:1080'

        if self.localOptions['psiphonpath']:
            self.psiphonpath = self.localOptions['psiphonpath']
        else:
            # FIXME: search for pyclient path instead of assuming is in the
            # home?
            # psiphon is not installable and to run it manually, it has to be 
            # run from the psiphon directory, so it wouldn't make sense to
            # nstall it in the PATH
            from os import path,  getenv
            self.psiphonpath = path.join(
                getenv('HOME'), 
                 'psiphon-circumvention-system/pyclient')
            log.debug('psiphon path: %s' % self.psiphonpath)

        x = """#!/usr/bin/env python
from psi_client import connect
connect(False)
"""

        import tempfile
        import stat
        import os
        # FIXME: import os globally?
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(x)
        f.close()
        os.chmod(f.name, os.stat(f.name).st_mode | stat.S_IEXEC)
        log.debug('executable file name: %s' % f.name)
        self.command = [f.name]
        log.debug('command: %s' % ''.join(self.command))

    def handleRead(self, stdout, stderr):
        log.debug("PsiphonTest: test_psiphon: checkBootstrapped")
        if 'Press Ctrl-C to terminate.' in self.processDirector.stdout:
            if not self.bootstrapped.called:
                self.bootstrapped.callback(None)

    @defer.inlineCallbacks
    def test_psiphon(self):
        log.debug('PsiphonTest: test_psiphon')

        # FIXME: do this in a twisted way
        import os.path
        if not os.path.exists(self.psiphonpath):
            log.debug('psiphon path does not exists, is it installed?')
        else:
            log.debug('psiphon path is correct')

        finished = self.run(self.command, usePTY=1,
                        path=self.psiphonpath,
                        env=dict(PYTHONPATH=self.psiphonpath))

        def addResultToReport(result):
            # FIXME: to remove, this is not being used anymore
            log.debug("PsiphonTest: test_psiphon: addResultToReport")
            self.report['success'] = True

        def addFailureToReport(failure):
            log.debug("PsiphonTest: test_psiphon: addFailureToReport")
            self.report['failure'] = handleAllFailures(failure)
            self.report['success'] = False

        def calldoRequest(result,  url):
            return self.doRequest(self.url)
        self.bootstrapped.addCallback(calldoRequest,  self.url)
        # in case of not doing the  calldoRequest, can just call addResultToReport
        #self.bootstrapped.addCallback(addResultToReport)

        @self.bootstrapped.addCallback
        def send_sigint(r):
            log.debug('PsiphonTest:send_sigint')
            # FIXME: is this needed?
            # self.processDirector.close()
            # FIXME: this is sending Ctrl-C to the python psiphon process, 
            # but psiphon is not killing anymore 
            self.processDirector.transport.signalProcess('INT')
        self.bootstrapped.addErrback(addFailureToReport)
        yield self.bootstrapped

    def processResponseBody(self, body):
        # FIXME: this is not being called
        # what should be added to the report?
        log.debug("PsiphonTest: processResponseBody: addResultToReport")
        self.report['body'] = body
        self.report['success'] = True

    def tearDown(selfs):
        # FIXME: this is not being called
        log.debug("PsiphonTest: tearDown")
        import os
        os.remove(self.command[0])      


