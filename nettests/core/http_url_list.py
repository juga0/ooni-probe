# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.internet import defer
from twisted.python import usage
from ooni.templates import httpt

class UsageOptions(usage.Options):
    optParameters = [['content', 'c', None,
                        'The file to read from containing the content of a block page'],
                     ['url', 'u', None, 'Specify a single URL to test.']
                    ]

class HTTPURLList(httpt.HTTPTest):
    """
    Performs GET, POST and PUT requests to a list of URLs specified as
    input and checks if the page that we get back as a result matches that
    of a block page given as input.

    If no block page is given as input to the test it will simply collect the
    responses to the HTTP requests and write them to a report file.
    """
    name = "HTTP URL List"
    author = "Arturo Filastò"
    version = "0.1.3"

    usageOptions = UsageOptions

    inputFile = ['file', 'f', None, 
            'List of URLS to perform GET and POST requests to']

    def setUp(self):
        """
        Check for inputs.
        """
        if self.input:
            self.url = self.input
        elif self.localOptions['url']:
            self.url = self.localOptions['url']
        else:
            raise Exception("No input specified")

    def check_for_content_censorship(self, body):
        """
        If we have specified what a censorship page looks like here we will
        check if the page we are looking at matches it.

        XXX this is not tested, though it is basically what was used to detect
        censorship in the palestine case.
        """
        self.report['censored'] = True

        censorship_page = open(self.localOptions['content'])
        response_page = iter(body.split("\n"))

        for censorship_line in censorship_page.xreadlines():
            response_line = response_page.next()
            if response_line != censorship_line:
                self.report['censored'] = False
                break
        censorship_page.close()

    def processResponseBody(self, body):
        if self.localOptions['content']:
            self.check_for_content_censorship(body)

    def test_get(self):
        return self.doRequest(self.url, method="GET")

    def test_post(self):
        return self.doRequest(self.url, method="POST")

    def test_put(self):
        return self.doRequest(self.url, method="PUT")


