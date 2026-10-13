"""Allowlisted useful workflows, executed under native leases in child processes."""
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
from .manager import Manager, ROOT, bounded_json
from .workflows import Workflows
from .host_adapter import HostStatusAdapter, diagnose

def source_entries():
    m = json.loads((ROOT / 'SOURCE-PROVENANCE.json').read_text())
    return [(r['path'], r['sha256']) for r in m['files']] + [('vendor/braink/' + p, d) for p, d in m['resident']['files'].items()]

def source_check():
    observations = []
    for name, expected in source_entries():
        p = ROOT / name
        if p.is_symlink() or not p.resolve().is_relative_to(ROOT): raise ValueError('SOURCE_PATH_REJECTED')
        actual = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
        observations.append({'path': name, 'expected': expected, 'actual': actual, 'matches': actual == expected})
    return {'checked': len(observations), 'mismatches': [o['path'] for o in observations if not o['matches']],
        'entriesDigest': hashlib.sha256(bounded_json(observations)).hexdigest(), 'entries': observations}

def execute(w, key, role, ref):
    request = json.loads(w.row(key)['request']);kind = request['kind'];inputs = request['inputs']
    envelope = {'taskId': key, 'kind': kind, 'responsibility': role,
        'requestDigest': hashlib.sha256(bounded_json(request)).hexdigest(),
        'workerCodeDigest': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'expertise': 'UNQUALIFIED', 'modelBinding': None, 'assessmentReceipt': None}
    if role == 'delivery':
        if kind == 'service_health':
            observation = HostStatusAdapter().observe(inputs['serviceId'])
            result = {'observation': observation, 'diagnosis': diagnose(observation)}
        elif kind == 'source_reconcile': result = source_check()
        elif kind == 'durable_checkpoint':
            data = bounded_json(inputs['record'])
            result = {'record': inputs['record'], 'bytes': len(data), 'digest': hashlib.sha256(data).hexdigest(),
                'meaning': 'A bounded workload checkpoint; integrity and custody are tested separately.'}
        else: raise ValueError('UNADMITTED_WORKFLOW')
        return {**envelope, 'result': result}
    delivery = json.loads(w.row(key)['delivery']);actor = w.output(delivery['team'], delivery['job'])
    if delivery['team'] == ref['team'] or actor['requestDigest'] != envelope['requestDigest']:
        raise ValueError('ANALYST_SCOPE_OR_REQUEST_MISMATCH')
    findings = [];status = 'SUPPORTED_WITHIN_SCOPE'
    if kind == 'service_health':
        # A separate authenticated observation, not acceptance of an actor PASS flag.
        independent = HostStatusAdapter().observe(inputs['serviceId'])
        facts = independent.get('facts', {})
        expected = ('HEALTHY' if facts.get('healthyNodes') == 10 and facts.get('bootStatus') == 'COMPLETED' else 'DEGRADED') if independent['classification'] == 'OBSERVED' else independent['classification']
        actor_status = actor['result']['diagnosis']['status']
        if expected != actor_status or facts.get('sourceDigest') != actor['result']['observation'].get('facts', {}).get('sourceDigest'):
            status = 'REVIEW_REQUIRED';findings.append('Independent service observation differs from actor diagnosis or source fingerprint.')
        findings.append('Independent observation: ' + expected + '. This tests the current owner service boundary, not external ingress or every service.')
        if expected != 'HEALTHY': status = 'ACTION_REQUIRED'
        result = {'status': status, 'findings': findings, 'independentObservation': independent,
            'nextAction': diagnose(independent)['nextAction']}
    elif kind == 'source_reconcile':
        # Re-open every actual source file in this process; do not trust actor hashes.
        mismatches = []
        for name, expected in source_entries():
            path = ROOT / name
            if path.is_symlink() or not path.resolve().is_relative_to(ROOT): raise ValueError('SOURCE_PATH_REJECTED')
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected: mismatches.append(name)
        if mismatches or actor['result']['mismatches'] or actor['result']['checked'] != len(source_entries()): status = 'REVIEW_REQUIRED'
        result = {'status': status, 'findings': ['Separately reopened and hashed every pinned native source.',
            'Source integrity does not establish security, rights expansion or model expertise.'],
            'checked': len(source_entries()), 'mismatches': mismatches,
            'nextAction': 'Quarantine changed source and compare its admitted commit before deployment.' if mismatches else 'Pinned source matches; retain this task as source-custody evidence.'}
    else:
        actual = actor['result'];expected = bounded_json(inputs['record'])
        if actual.get('record') != inputs['record'] or actual.get('digest') != hashlib.sha256(expected).hexdigest() or actual.get('bytes') != len(expected):
            status = 'REVIEW_REQUIRED'
        job = w.m.runtime.job(delivery['job']);receipt = json.loads(job['result'])
        if job['state'] != 'VERIFIED' or not receipt['verification']['content_matches']: raise ValueError('DELIVERY_READBACK_REQUIRED')
        with w.m.runtime.db() as db:
            events = [r[0] for r in db.execute('SELECT event FROM events WHERE job=? ORDER BY seq', (delivery['job'],))]
        result = {'status': status, 'findings': ['Recomputed checkpoint bytes and digest from original task input.',
            'Fetched delivery output from native VFS after distinct-process observation.'],
            'digest': hashlib.sha256(expected).hexdigest(), 'nativeEvents': events, 'deliveryAttempts': job['attempts'],
            'nextAction': 'Checkpoint retained. Reopen this task after restart to verify the same immutable output.'}
    return {**envelope, 'deliveryArtifactDigest': json.loads(w.m.runtime.job(delivery['job'])['result'])['digest'], 'result': result}

def main():
    root, key, role = sys.argv[1:]
    if role not in {'delivery', 'analyst'}: raise ValueError('ROLE_REJECTED')
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15));resource.setrlimit(resource.RLIMIT_AS, (384*1024*1024,)*2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (64,64))
    w = Workflows(Manager(Path(root)));ref = json.loads(w.row(key)[role]);team = w.m.runtime.team(ref['team'])
    member = next(m for m in team['members'] if m['role'] == 'production')
    if member['adapter'] != 'braink.workflow.' + role + '.v1': raise ValueError('ADAPTER_BINDING_REJECTED')
    claim = w.m.runtime.claim(ref['team'], member['member_id'], 20)
    if claim is None: return
    if claim['id'] != ref['job']: raise ValueError('WORKFLOW_CLAIM_SCOPE')
    if os.environ.get('BRAINK_TEST_FAULT') == 'after-claim': os._exit(74)
    try:
        store = w.m.runtime.member_store(ref['team'], member['member_id'])
        existing = store.resolve_path('/artifacts/' + claim['id'] + '.txt')
        if existing:
            data = store.read_content(existing.digest)
            previous = json.loads(data)
            expected_request = hashlib.sha256(bounded_json(json.loads(w.row(key)['request']))).hexdigest()
            if previous['taskId'] != key or previous['responsibility'] != role or previous['requestDigest'] != expected_request:
                raise ValueError('RECOVERY_ARTIFACT_CONFLICT')
        else: data = bounded_json(execute(w, key, role, ref))
        w.m.runtime.produce(claim, data, os.environ.get('BRAINK_TEST_FAULT') == 'after-write')
    except Exception:
        w.m.runtime.fail(claim, 'BOUNDED_ADAPTER_FAILED; inspect binding and task evidence')
        raise

if __name__ == '__main__': main()
