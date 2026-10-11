"""Separate observer process: independent expected bytes + read-only SQLite/object readback."""
import argparse,hashlib,json,os,sqlite3,resource
from pathlib import Path
from runtime import Runtime,Denied
p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('team');p.add_argument('verifier');p.add_argument('job');a=p.parse_args()
resource.setrlimit(resource.RLIMIT_CPU,(5,5));resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))
r=Runtime(a.root);r.member(a.team,a.verifier,'verify:members');j=r.job(a.job)
if j['team']!=a.team or j['state']!='PRODUCED':raise Denied('observer job scope')
r.member(a.team,j['worker'],'write:self')
result=json.loads(j['result']);payload=json.loads(j['payload']);store=r.member_store(a.team,j['worker']);base=store.root
with sqlite3.connect((base/'vfs.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
    row=db.execute('SELECT digest,size FROM bindings WHERE path=?',(result['path'],)).fetchone()
assert row and row[0]==result['digest']
d=row[0];content=store._object_path(d).read_bytes()
assert hashlib.sha256(content).hexdigest()==d and len(content)==row[1]
if payload['adapter']=='utf8.uppercase.v1':expected=''.join(ch.upper() for ch in payload['text']).encode('utf-8')
elif payload['adapter']=='utf8.wordcount.v1':
    import re
    expected=(str(len(re.findall(r'\S+',payload['text'])))+'\n').encode('ascii')
else:raise Denied('unqualified observation')
assert content==expected,'artifact differs from independent expected bytes'
history=store.binding_history(result['path']);assert len(history)==1
native=store.verify(d);assert native['verified'];assert store.verify_receipt_chain()['verified']
observation={'pid':os.getpid(),'digest':d,'bytes':len(content),'content_matches':True,'binding_versions':len(history),'native_observer_receipt':native['receipt']['receipt_id'],'verification_scope':'separate-process deterministic readback; no different-model assessment','artifact_text':content.decode()}
print(json.dumps({'job_id':a.job,'state':'OBSERVED',**observation},sort_keys=True))
