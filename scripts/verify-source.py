"""Verify the exact selected native bytes, including second-order dependencies."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'SOURCE-PROVENANCE.json').read_text())
for record in manifest['files']:
    assert hashlib.sha256((ROOT/record['path']).read_bytes()).hexdigest()==record['sha256'],record['path']
for path,digest in manifest['resident']['files'].items():
    assert hashlib.sha256((ROOT/'vendor/braink'/path).read_bytes()).hexdigest()==digest,path
print(json.dumps({'state':'SOURCE_BYTES_VERIFIED','files':len(manifest['files'])+len(manifest['resident']['files']),
                  'assessmentReceipt':None}))
