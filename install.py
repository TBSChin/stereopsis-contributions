"""Safety-first installer prototype. Network operations in this release are read-only."""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path, PurePosixPath
import urllib.error
import urllib.parse
import urllib.request

STOCK_PATH = '/home/music/EYESY_OS/engines/python/main.py'
STOCK_31 = '101a68e0759194121b85d2b859c6dd4b30bd4d879d922d69a2c29d4583456386'

def sha(data):
    return hashlib.sha256(data).hexdigest()

class Device:
    def __init__(self, address):
        # No URLs, credentials, paths, or redirects to unintended destinations.
        self.host = str(ipaddress.IPv4Address(address))
        self.base = 'http://' + self.host

    def get(self, path, preview=False):
        url = self.base + (':8081' if preview else '') + path
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                raise ValueError('Device redirects are not accepted')
        with urllib.request.build_opener(NoRedirect).open(url, timeout=8) as response:
            data = response.read(16 * 1024 * 1024 + 1)
        if len(data) > 16 * 1024 * 1024:
            raise ValueError('Device response exceeds safety limit')
        return data

    def read(self, path):
        return self.get('/get_file?' + urllib.parse.urlencode({'fpath': path}))

def inspect(device):
    report = {'stock_engine_sha256': None, 'stock_profile': 'unknown',
              'stereopsis_version': None, 'running_engine': 'unavailable', 'blockers': []}
    try:
        fingerprint = sha(device.read(STOCK_PATH))
        report['stock_engine_sha256'] = fingerprint
        if fingerprint == STOCK_31:
            report['stock_profile'] = 'eyesy-os-3.1-upstream-fingerprint'
        else:
            report['blockers'].append('Unknown stock firmware fingerprint; installation refused.')
    except (OSError, ValueError) as error:
        report['blockers'].append('Cannot verify stock firmware: ' + str(error))
    try:
        state = json.loads(device.get('/state.json', preview=True))
        report['running_engine'] = state.get('engine', 'unknown')
    except (OSError, ValueError):
        pass  # Stock firmware need not expose the Stereopsis preview.
    try:
        raw = json.loads(device.read('/sdcard/stereopsis/INSTALLED.json'))
        report['stereopsis_version'] = raw.get('stereopsis')
    except (OSError, ValueError):
        pass
    report['starting_point'] = 'stereopsis' if report['stereopsis_version'] else 'stock-or-unverified'
    return report

def validate_bundle(root, manifest):
    root = Path(root).resolve()
    seen = set()
    for item in manifest.get('files', []):
        relative = PurePosixPath(item['source'])
        target = PurePosixPath(item['target'])
        if relative.is_absolute() or '..' in relative.parts or '\\' in item['source']:
            raise ValueError('Unsafe package source')
        source = (root / str(relative)).resolve()
        if not source.is_relative_to(root):
            raise ValueError('Package source escapes bundle')
        # Only dedicated add-on directories. Never OS, boot, user scenes/config,
        # stock modes, or upstream engine files in an unapproved package.
        allowed = target.is_relative_to('/sdcard/Modes/Personal Swarms') or target.is_relative_to('/sdcard/personal-swarms')
        if not allowed or '..' in target.parts or '\\' in item['target']:
            raise ValueError('Unsafe install target')
        if str(target).casefold() in seen:
            raise ValueError('Duplicate install target')
        seen.add(str(target).casefold())
        if not source.is_file() or sha(source.read_bytes()) != item['sha256']:
            raise ValueError('Missing or corrupt payload: ' + str(relative))
    return True

def plan(report, manifest):
    blockers = list(report['blockers'])
    if not manifest.get('release_approved', False):
        blockers.append('Development package: hardware validation and redistribution review incomplete.')
    if not manifest.get('files'):
        blockers.append('No approved payload has been packaged.')
    version = report.get('stereopsis_version')
    if version and version not in manifest.get('tested_stereopsis', []):
        blockers.append('Existing Stereopsis version has not been approved for this package.')
    if not version:
        blockers.append('Stock path requires a pinned, verified Stereopsis bootstrap; not packaged yet.')
    blockers.append('Device writes are disabled in this development release.')
    return {'inspection': report, 'actions': [
        {'target': f['target'], 'sha256': f['sha256']} for f in manifest.get('files', [])],
        'installation_allowed': False, 'blockers': blockers}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('address', help='EYESY IPv4 address')
    parser.add_argument('--check', action='store_true', help='Read-only inspection (also the default)')
    parser.add_argument('--json', action='store_true', help='Machine-readable report')
    parser.add_argument('--install', action='store_true', help='Reserved; safely refused until validated')
    args = parser.parse_args()
    if args.install:
        parser.error('Installation is disabled until clean-stock, upgrade, and recovery tests pass. No device changes made.')
    root = Path(__file__).parent
    manifest = json.loads((root / 'manifest.json').read_text())
    validate_bundle(root, manifest)
    result = plan(inspect(Device(args.address)), manifest)
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
