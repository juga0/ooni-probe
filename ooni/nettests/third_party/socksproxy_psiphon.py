from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.web.client import readBody
from twisted.python import usage

from txsocksx.http import SOCKS5Agent

from ooni.errors import handleAllFailures, TaskTimedOut
from ooni.utils import log
from ooni.templates import process
from ooni.templates.process import ProcessTest,  ProcessDirector



class UsageOptions(usage.Options):
    log.debug("UsageOptions")
    optParameters = [
        ['url', 'u', None, 'Specify a single URL to test.'],
        ['psiphonpath', 'p', None, 'Specify psiphon python client path.'],]


#    # TO USE PSIPHONPROCESSDIRECTOR
#    # HAVE TO OVERWRITE COMPLETELY CLOSE!!!!!!!!!!!!!!!!!!!
#class PsiphonProcessDirector(ProcessDirector):
#    def close(self, reason=None):
#        log.debug("ProcessDirector: close")
#        self.reason = reason
#        self.transport.loseConnection()


class PsiphonTest(process.ProcessTest):
    
    """
    This class tests Psiphon python client
    
    test_psiphon:
      Starts a Psiphon, check if it bootstraps successfully
      (print a line in stderr).
      Then, perform an HTTP request using the proxy
    """

    name = "Psiphon Test"
    description = "Bootstraps a Psiphon and does a HTTP GET for the specified URL"
    author = "juga"
    version = "0.0.1"
    timeout = 20
    usageOptions = UsageOptions
    #requiredOptions = ['url']

#    # TO USE PSIPHONPROCESSDIRECTOR
#    # HAVE TO OVERWRITE COMPLETELY RUN!!!!!!!!!!!!!!!!!!!
#    def run(self, command, finished=None,  readHook=None, usePTY=0, path=None, env={}):
#        log.debug("PsiphonTesT: run")
#        d = defer.Deferred()
#        d.addCallback(self.processEnded, command)
#        # XXX make this into a class attribute
#        self.processDirector = PsiphonProcessDirector(d, finished, self.timeout,  readHook=readHook)
#        reactor.spawnProcess(self.processDirector, command[0], command, usePTY=usePTY, path=path, env=env)
#        return d



    def setUp(self):
        log.debug('PsiphonTest: setUp')
        self.bootstrapped = defer.Deferred()
        if self.localOptions['url']:
            self.url = self.localOptions['url']
        else:
            self.url = 'https://wtfismyip.com/text'
            # FIXME: use http://google.com?
        if self.localOptions['psiphonpath']:
            self.psiphonpath = self.localOptions['psiphonpath']
        else:
            # FIXME: search for pyclient path instead of assuming is in the home?
            from os import path,  getenv
            self.psiphonpath = path.join(getenv('HOME'), 'psiphon-circumvention-system/pyclient')
            log.debug('psiphon path: %s' % self.psiphonpath)

        x = """#!/usr/bin/env python
from psi_client import connect
connect(False)
"""

        import tempfile
        import stat
        import os
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(x)
        f.close()
        os.chmod(f.name, os.stat(f.name).st_mode | stat.S_IEXEC)
        log.debug('executable file name: %s' % f.name)
        self.command = [f.name]
        log.debug('command: %s' % ''.join(self.command))

    def handleRead(self, stdout, stderr):
        log.debug("PsiphonTest: test_psiphon: checkBootstrapped")
        #if 'Your Psiphon is now running at ' in pd.stderr:
        if 'Press Ctrl-C to terminate.' in self.processDirector.stdout:
            if not self.bootstrapped.called:
                self.bootstrapped.callback(None)

    @defer.inlineCallbacks
    def test_psiphon(self):
        log.debug('PsiphonTest: test_psiphon')

        # FIXME: do this in a twisted way
        import os.path
        if not os.path.exists(self.psiphonpath):
            log.debug('psiphon path does not exists, is it installed')
        else:
            log.debug('psiphon path is correct')

        # TODO: check the path exixst before running
        finished = self.run(self.command, usePTY=1,
                        path=self.psiphonpath,
                        env=dict(PYTHONPATH=self.psiphonpath))

        def addResultToReport(result):
            log.debug("PsiphonTest: test_psiphon: addResultToReport")
            self.report['success'] = True

        def addFailureToReport(failure):
            log.debug("PsiphonTest: test_psiphon: addFailureToReport")
            self.report['failure'] = handleAllFailures(failure)
            self.report['success'] = False

        self.bootstrapped.addCallback(addResultToReport)
        
        @self.bootstrapped.addCallback
        def send_sigint(r):
            log.debug('PsiphonTest:send_sigint')
#            self.processDirector.close()
            self.processDirector.transport.signalProcess('INT')
        self.bootstrapped.addErrback(addFailureToReport)
        yield self.bootstrapped
