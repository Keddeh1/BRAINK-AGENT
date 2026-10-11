"""Schema/source-custody validation; jsonschema is needed only for this development check."""
import hashlib,importlib.metadata,json
from pathlib import Path
import jsonschema
base=Path(__file__).resolve().parent
checks=[]
provenance=json.loads((base/'vendor/provenance.json').read_text())
for filename,expected in provenance['unchangedFiles'].items():
    assert hashlib.sha256((base/'vendor/native_vfs'/filename).read_bytes()).hexdigest()==expected
    checks.append('native source SHA256 '+filename)
for path in sorted((base/'templates').glob('*.json')):
    schema=json.loads((base/'schemas'/('team-template.schema.json' if path.name=='team.json' else 'worker-template.schema.json')).read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(json.loads(path.read_text()));checks.append('template schema '+path.name)
schema=json.loads((base/'schemas/team-instance.schema.json').read_text());jsonschema.Draft202012Validator.check_schema(schema)
for item in json.loads((base/'evidence/reviewed/team-interface.json').read_text()):
    jsonschema.Draft202012Validator(schema).validate(item)
    assert len({m['member_id'] for m in item['members']})==5
    assert all(set(m['permissions'])<=set(item['permissions']) for m in item['members'])
    checks.append('instance schema and inherited permissions '+item['instance_key'])
report={'checks_passed':len(checks),'checks':checks,'jsonschema_version':importlib.metadata.version('jsonschema'),'native_source_commit':provenance['reusedCommit']}
(base/'evidence/reviewed/schema-custody.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
