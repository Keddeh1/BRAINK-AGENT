"""Separate operational VFS integrity observer; semantic findings belong to analyst."""
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
from .manager import Manager, bounded_json
from .workflows import Workflows

def main():
    resource.setrlimit(resource.RLIMIT_CPU, (5,5));resource.setrlimit(resource.RLIMIT_AS, (256*1024*1024,)*2)
    queue_root, team, verifier, job_id = sys.argv[1:]
    w = Workflows(Manager(Path(queue_root).parent));r = w.m.runtime
    r.member(team, verifier, 'verify:members');job = r.job(job_id)
    if job['team'] != team or job['state'] != 'PRODUCED': raise ValueError('OBSERVER_SCOPE')
    member = r.member(team, job['worker'], 'write:self');payload = json.loads(job['payload'])
    packet = json.loads(payload['text']);role = packet['responsibility']
    if member['adapter'] != 'braink.workflow.' + role + '.v1' or payload['adapter'] != member['adapter']:
        raise ValueError('OBSERVER_ADAPTER')
    task = w.row(packet['taskId']);ref = json.loads(task[role])
    if ref != {'team': team, 'job': job_id}: raise ValueError('OBSERVER_TASK_BINDING')
    result = json.loads(job['result']);store = r.member_store(team, job['worker'])
    binding = store.resolve_path(result['path'])
    if binding is None or binding.digest != result['digest']: raise ValueError('OBSERVER_BINDING')
    content = store.read_content(binding.digest);value = json.loads(content)
    if value['taskId'] != packet['taskId'] or value['responsibility'] != role or value['requestDigest'] != hashlib.sha256(bounded_json(json.loads(task['request']))).hexdigest():
        raise ValueError('OBSERVER_CONTENT_BINDING')
    if value['expertise'] != 'UNQUALIFIED' or value['assessmentReceipt'] is not None or value['modelBinding'] is not None:
        raise ValueError('UNQUALIFIED_CLAIM_REQUIRED')
    if len(store.binding_history(result['path'])) != 1: raise ValueError('IMMUTABLE_BINDING_REQUIRED')
    native = store.verify(binding.digest)
    if not native['verified'] or not store.verify_receipt_chain()['verified']: raise ValueError('NATIVE_READBACK_REJECTED')
    print(json.dumps({'pid': os.getpid(), 'digest': binding.digest, 'bytes': len(content), 'content_matches': True,
        'native_observer_receipt': native['receipt']['receipt_id'], 'binding_versions': 1,
        'verification_scope': 'separate-process native byte integrity and immutable task binding; semantic analyst findings remain separate'}))

if __name__ == '__main__': main()
