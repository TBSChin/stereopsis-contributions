import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from desktop import Handler, TOKEN

class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.origin='http://127.0.0.1:%d'%cls.server.server_port
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def test_page_has_token_and_disabled_install(self):
        page=urllib.request.urlopen(self.origin).read().decode()
        self.assertIn(TOKEN,page)
        self.assertIn('Back up & install',page)
        self.assertIn('button disabled',page)
    def test_cross_origin_blocked(self):
        req=urllib.request.Request(self.origin+'/api/check',data=b'{}',headers={'Origin':'https://evil.example','X-Installer-Token':TOKEN})
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(req)
        self.assertEqual(error.exception.code,403)
    def test_no_install_endpoint(self):
        req=urllib.request.Request(self.origin+'/api/install',data=b'{}',headers={'Origin':self.origin,'X-Installer-Token':TOKEN})
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(req)
        self.assertEqual(error.exception.code,404)
    def test_inspection_with_mock_device(self):
        report={'blockers':[],'stereopsis_version':'0.11','stock_profile':'test','running_engine':'stereopsis'}
        with patch('desktop.inspect',return_value=report):
            req=urllib.request.Request(self.origin+'/api/check',data=b'{"address":"192.168.50.4"}',headers={'Origin':self.origin,'X-Installer-Token':TOKEN})
            result=json.loads(urllib.request.urlopen(req).read())
        self.assertFalse(result['installation_allowed'])

if __name__=='__main__':unittest.main()
