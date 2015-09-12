from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.web.client import readBody
from twisted.python import usage

from txsocksx.http import SOCKS5Agent

from ooni.errors import handleAllFailures, TaskTimedOut
from ooni.utils import log
from ooni.templates import process
from ooni.templates.process import ProcessTest# , ProcessDirector



class UsageOptions(usage.Options):
    log.debug("UsageOptions")
    optParameters = [
        ['url', 'u', None, 'Specify a single URL to test.'],]

class SocksProxyTest(process.ProcessTest):
    
    """
    This class tests a socks proxy
    
    test_socks_proxy:
      Starts a socks proxy, check if it bootstraps successfully
      (print a line in stderr).
      Then, perform an HTTP request using the proxy
      
    """
    
    # TODO: kill the ssh process before test finish
    
    name = "Socks proxy Test"
    description = "Bootstraps a socks proxy and does a HTTP GET for the specified URL"
    author = "juga"
    version = "0.0.1"
    #timeout = 20
    usageOptions = UsageOptions
    #requiredOptions = ['url']
    
    def setUp(self):
        log.debug('SocksProxyTest: setUp')
        if self.localOptions['url']:
            self.url = self.localOptions['url']
        else:
            self.url = 'https://wtfismyip.com/text'
            # FIXME: use http://google.com?

        # FIXME: this would be the psiphon script in the case of testing psiphon
        # for this to work, user must have an ssh key without passphrase
        x = """#!/bin/bash
/usr/bin/ssh -v -C -D  127.0.0.1:1080 -N -p 22 user@localhost
"""
        import tempfile
        import stat
        import os
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(x)
        f.close()
        os.chmod(f.name, os.stat(f.name).st_mode | stat.S_IEXEC)
        log.debug('executable name: %s' % f.name)
        self.command = [f.name]
        
    @defer.inlineCallbacks
    def test_socks_proxy(self):
        log.debug('SocksProxyTest: test_socks_proxy')
        bootstrapped = defer.Deferred()
        def checkBootstrapped(pd):
            log.debug("SocksProxyTest: test_socks_proxy: checkBootstrapped")
            if 'Entering interactive session.' in pd.stderr:
                if not bootstrapped.called:
                    bootstrapped.callback(None)
        #finished = self.run("/usr/bin/ssh -v -C -D  127.0.0.1:1080 -N -p 22 user@localhost".split(), readHook=checkBootstrapped)
        # using self.command instead of hardcode the command
        finished = self.run(self.command,  readHook=checkBootstrapped)
        serverEndpoint = TCP4ClientEndpoint(reactor, '127.0.0.1', 1080)
        agent = SOCKS5Agent(reactor, proxyEndpoint=serverEndpoint)
        
        def addResultToReport(result):
            log.debug("SocksProxyTest: test_socks_proxy: addResultToReport")
            self.report['body'] = result
            self.report['success'] = True

        def addFailureToReport(failure):
            log.debug("SocksProxyTest: test_socks_proxy: addFailureToReport")
            self.report['failure'] = handleAllFailures(failure)
            self.report['success'] = False

        def doRequest(noreason):
            log.debug("SocksProxyTest: test_socks_proxy: doRequest")
            log.debug("Doing HTTP request via sockx proxy for %s" % self.url)
            request = agent.request("GET", self.url)
            request.addCallback(readBody)
            request.addCallback(addResultToReport)
            request.addCallback(self.processDirector.close)
            return request

        bootstrapped.addCallback(doRequest)
        bootstrapped.addErrback(addFailureToReport)
        yield bootstrapped
