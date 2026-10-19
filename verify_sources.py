"""Validate downloaded source integrity and syntax; not a hardware test."""
import ast,hashlib,json
from pathlib import Path
root=Path(__file__).parent
def check():
    for line in (root/'SHA256SUMS').read_text().splitlines():
        digest,name=line.split('  ',1)
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
    for file in root.rglob('*.py'):
        ast.parse(file.read_text(encoding='utf-8'))
    groups={False:set(),True:set()}
    modes=list((root/'Modes').iterdir())
    for mode in modes:
        kernel=mode/'swarm.c'
        if kernel.exists():
            groups['Triangle' in mode.name].add(hashlib.sha256(kernel.read_bytes()).hexdigest())
    catalog=root/'curated-modes.json'
    expected=sum(r['status']=='bundled' for r in json.loads(catalog.read_text())['modes']) if catalog.exists() else 22
    assert len(modes)==expected,(len(modes),expected)
    assert all(len(group)==1 for group in groups.values()),'Mixed native renderer revisions'
    assert (root/'Modes/Swarm - Text/Futura_Heavy_Oblique.otf').is_file()
    print('PASS: hashes, Python syntax, %d modes, coherent round/triangle kernels, bundled font.'%expected)
    print('This does not replace integration testing on EYESY.')
if __name__=='__main__':check()
