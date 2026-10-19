import json
import tempfile
import unittest
from pathlib import Path
from install import Device, inspect, plan, validate_bundle, STOCK_31

class FakeDevice:
    def read(self, path):
        if path.endswith('INSTALLED.json'):
            return b'{"stereopsis":"0.11"}'
        return b'unknown firmware'
    def get(self, path, preview=False):
        return b'{"engine":"stereopsis"}'

class SafetyTests(unittest.TestCase):
    def test_unknown_firmware_refused(self):
        result = plan(inspect(FakeDevice()), {'files':[]})
        self.assertFalse(result['installation_allowed'])
        self.assertTrue(any('Unknown stock' in b for b in result['blockers']))

    def test_even_recognized_device_blocked(self):
        result = plan({'blockers':[], 'stock_engine_sha256':STOCK_31,
                       'stereopsis_version':'0.11'}, {'release_approved':True,'tested_stereopsis':['0.11'],'files':[]})
        self.assertFalse(result['installation_allowed'])

    def test_address_restrictions(self):
        for value in ['http://example.com', '127.0.0.1/path', 'user:password@host']:
            with self.assertRaises(ValueError): Device(value)

    def test_path_and_payload_restrictions(self):
        with tempfile.TemporaryDirectory() as folder:
            for source,target in [('x','/boot/config.txt'),('../x','/sdcard/personal-swarms/x'),
                                  ('x','/sdcard/Modes/Personal Swarms/../../System/x')]:
                with self.assertRaises(ValueError):
                    validate_bundle(folder, {'files':[{'source':source,'target':target,'sha256':'0'*64}]})

    def test_empty_development_manifest_validates(self):
        self.assertTrue(validate_bundle(Path(__file__).parent, {'files':[]}))

if __name__ == '__main__': unittest.main()
