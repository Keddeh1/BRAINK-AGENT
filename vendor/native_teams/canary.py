"""Executable canary and hostile-input regression; produces its own checks, not app PASS labels."""
import argparse,concurrent.futures,hashlib,json,os,shutil,sqlite3,subprocess,sys,tempfile,time
from pathlib import Path
from runtime import Runtime,Denied,Fenced,ROLES,MAX_JOBS,MAX_BYTES,scoped_path
BASE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--evidence',required=True);a=p.parse_args()
root=Path(a.state).resolve();out=Path(a.evidence).resolve();out.mkdir(parents=True,exist_ok=True)
if root.exists():raise SystemExit('Use a new disposable state directory; existing state is preserved')
r=Runtime(root);checks=[];runs=[];start=time.monotonic()
def check(name,condition):
    if not condition:raise AssertionError(name)
    checks.append(name)
def denied(name,fn,exc=(Denied,ValueError)):
    try:fn()
    except exc:checks.append(name)
    else:raise AssertionError(name)
def run(script,args,expected=0):
    began=time.monotonic();measured=subprocess.run([sys.executable,str(BASE/'process_runner.py'),sys.executable,str(BASE/script),*map(str,args)],capture_output=True,text=True,timeout=12)
    if measured.returncode:raise AssertionError(measured.stderr)
    sample=json.loads(measured.stdout);result=subprocess.CompletedProcess(script,sample['exit_code'],sample['stdout'],sample['stderr'])
    runs.append({'script':script,'args':list(map(str,args[1:])),'exit_code':result.returncode,'seconds':round(time.monotonic()-began,4),'stdout':result.stdout,'stderr':result.stderr,'measurement':sample['measurement']})
    if result.returncode!=expected:raise AssertionError((script,result.returncode,result.stderr))
    return result
teams=[r.instantiate(k,BASE/'templates',set().union(*ROLES.values())) for k in ['alpha','beta']]
def member(t,role):return next(m['member_id'] for m in t['members'] if m['role']==role)
def enqueue(t,role,key,text='Keddeh local artifact canary'):
    return r.enqueue(t['team_instance_id'],member(t,'manager'),member(t,role),key,text)
def worker(t,role,*flags,expected=0):return run('worker.py',[root,t['team_instance_id'],member(t,role),*flags],expected)
def verify(t,j,expected=0):return run('verifier.py',[root,t['team_instance_id'],member(t,'verification'),j['id']],expected)
A,B=teams;aid=A['team_instance_id'];bid=B['team_instance_id']
admin=run('manager.py',['inspect',root,aid,member(A,'administration')]);check('administration adapter reports instantiated team',json.loads(admin.stdout)['team_instance_id']==aid)
check('stable team and member identities',r.instantiate('alpha',BASE/'templates',set().union(*ROLES.values()))==A)
check('two distinct enclosing team VFS scopes',aid!=bid and (root/A['vfs_root']/'vfs/vfs.sqlite3').exists() and (root/B['vfs_root']/'vfs/vfs.sqlite3').exists())
check('ten distinct member identities',len({m['member_id'] for t in teams for m in t['members']})==10)
check('immutable worker template objects shared across team instances',[m['template_digest'] for m in A['members']]==[m['template_digest'] for m in B['members']] and r.templates.status()['artifacts']==6)
denied('cross-team member rejected',lambda:r.member_store(aid,member(B,'production')))
for path in ['../escape','artifacts/../../escape','/etc/passwd','artifacts\\escape']:
    denied('path rejection '+path,lambda path=path:scoped_path(path))
denied('producer cannot schedule',lambda:r.enqueue(aid,member(A,'production'),member(A,'specialist'),'bad','x'))
denied('verifier cannot produce',lambda:r.claim(aid,member(A,'verification')))
denied('parent permission escalation blocked',lambda:r.instantiate('bad',BASE/'templates',{'inspect'}))
with tempfile.TemporaryDirectory() as td:
    shutil.copytree(BASE/'templates',Path(td)/'templates');f=Path(td)/'templates/production.json';v=json.loads(f.read_text());v['permissions'].append('schedule');f.write_text(json.dumps(v))
    denied('member permission escalation blocked',lambda:r.instantiate('bad',Path(td)/'templates',set().union(*ROLES.values())))
for t in teams:
    for role in ['production','specialist']:
        j=enqueue(t,role,'initial-'+role,'Keddeh '+t['instance_key']+' artifact')
        check('duplicate enqueue '+t['instance_key']+role,enqueue(t,role,'initial-'+role,'Keddeh '+t['instance_key']+' artifact')['id']==j['id'])
        denied('conflicting duplicate '+t['instance_key']+role,lambda t=t,role=role:enqueue(t,role,'initial-'+role,'changed'))
        worker(t,role);verify(t,j)
        check('separate process verified '+t['instance_key']+role,r.job(j['id'])['state']=='VERIFIED')
# Revision identity is content-bound while old instance references remain stable.
with tempfile.TemporaryDirectory() as td:
    shutil.copytree(BASE/'templates',Path(td)/'templates');f=Path(td)/'templates/production.json';v=json.loads(f.read_text());v['version']=2;f.write_text(json.dumps(v))
    revision=Runtime(Path(td)/'state').instantiate('alpha',Path(td)/'templates',set().union(*ROLES.values()))
    check('worker revision changes closure/instance identity',revision['team_instance_id']!=aid)
    check('old instance definition stable',r.team(aid)==A)
# Neither team can resolve the other team's output in its corresponding member store.
other=enqueue(A,'production','cross-scope','alpha secret');worker(A,'production')
result=json.loads(r.job(other['id'])['result'])
check('artifact absent in other member VFS',r.member_store(bid,member(B,'production')).resolve_path(result['path']) is None)
verify(A,other)
denied('same-team producer cannot read specialist VFS',lambda:r.read_member_artifact(aid,member(A,'production'),member(A,'specialist'),'artifacts/unknown.txt'))
check('own member VFS readback',r.read_member_artifact(aid,member(A,'production'),member(A,'production'),result['path'].lstrip('/'))==b'ALPHA SECRET')
link=root/'teams'/aid/'members'/member(A,'production')/'vfs';backup=link.with_name('vfs.saved');link.rename(backup)
try:
    link.symlink_to(root/'teams'/aid/'members'/member(A,'specialist')/'vfs',target_is_directory=True)
    denied('sibling VFS symlink escape blocked',lambda:r.member_store(aid,member(A,'production')))
finally:link.unlink();backup.rename(link)
# Actual abrupt process exits before artifact write and between VFS commit and queue acknowledgement.
for t,role,fault,exitcode in [(A,'production','after-claim',74),(B,'specialist','after-write',75)]:
    j=enqueue(t,role,'restart-'+fault,'restart survives')
    worker(t,role,'--lease','.15','--fault',fault,expected=exitcode)
    check('crashed job remains leased '+fault,r.job(j['id'])['state']=='RUNNING')
    time.sleep(.2)
    r=Runtime(root) # fresh manager runtime; durable queue reopens without resetting state
    worker(t,role);verify(t,j)
    current=r.job(j['id']);check('restart recovers '+fault,current['state']=='VERIFIED' and current['attempts']==2)
    rr=json.loads(current['result']);check('single committed binding after '+fault,len(r.member_store(t['team_instance_id'],member(t,role)).binding_history(rr['path']))==1)
# Explicit fencing: stale claim cannot finish after another claim supersedes it.
j=enqueue(A,'specialist','fence');old=r.claim(aid,member(A,'specialist'),.05);time.sleep(.08);new=r.claim(aid,member(A,'specialist'))
denied('stale epoch/token fenced',lambda:r.produce(old,b'wrong'),(Fenced,));r.produce(new,b'4\n');verify(A,j)
# Two OS processes contend for the same pending job. Exactly one artifact is produced.
j=enqueue(B,'production','concurrent')
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(lambda _:worker(B,'production'),range(2)))
states=[json.loads(x.stdout)['state'] for x in results]
check('atomic claim across two processes',sorted(states)==['NO_WORK','PRODUCED']);verify(B,j)
# Failure budget persists across process restarts.
j=enqueue(A,'production','bounded-failure')
for _ in range(3):worker(A,'production','--fault','fail',expected=76)
worker(A,'production');check('retry budget terminal after three attempts',r.job(j['id'])['state']=='FAILED' and r.job(j['id'])['attempts']==3)
# Corrupt bytes deliberately; independent observer must fail and must not promote queue state.
j=enqueue(B,'specialist','observer-negative','one two');worker(B,'specialist');res=json.loads(r.job(j['id'])['result']);d=res['digest'];obj=root/'teams'/bid/'members'/member(B,'specialist')/'vfs/objects'/d[:2]/d[2:4]/d;original=obj.read_bytes();obj.write_bytes(b'corrupt')
try:
    verify(B,j,expected=1);check('observer rejection leaves PRODUCED',r.job(j['id'])['state']=='PRODUCED')
finally:obj.write_bytes(original)
verify(B,j)
# Resource boundary fixture stays separate from the delivered two-team state.
with tempfile.TemporaryDirectory() as td:
    bounded=Runtime(td);t=bounded.instantiate('bounded',BASE/'templates',set().union(*ROLES.values()))
    for i in range(MAX_JOBS):bounded.enqueue(t['team_instance_id'],member(t,'manager'),member(t,'production'),'q'+str(i),'x')
    denied('queue capacity enforced',lambda:bounded.enqueue(t['team_instance_id'],member(t,'manager'),member(t,'production'),'overflow','x'))
denied('input byte bound',lambda:enqueue(A,'production','large','x'*MAX_BYTES))
j=enqueue(A,'specialist','oversized-output');c=r.claim(aid,member(A,'specialist'))
denied('artifact byte bound',lambda:r.produce(c,b'x'*(MAX_BYTES+1)))
r.produce(c,b'4\n');verify(A,j)
interfaces=[r.export_interface(t['team_instance_id']) for t in teams]
for t in teams:
    for m in t['members']:check('native receipt chain '+t['instance_key']+m['role'],r.member_store(t['team_instance_id'],m['member_id']).verify_receipt_chain()['verified'])
check('shared template receipt chain',r.templates.verify_receipt_chain()['verified'])
with r.db() as db:
    totals=dict(db.execute('SELECT state,count(*) FROM jobs GROUP BY state').fetchall());events=[dict(row) for row in db.execute('SELECT * FROM events ORDER BY seq')]
check('all scheduled jobs terminal',set(totals)<= {'VERIFIED','FAILED'})
check('only injected failure terminal',totals.get('FAILED')==1)
size=sum(f.stat().st_size for f in root.rglob('*') if f.is_file());elapsed=time.monotonic()-start
check('bounded canary disk under 16 MiB',size<16*1024*1024)
check('bounded canary wall time under 45 seconds',elapsed<45)
report={'schema_version':'keddeh.nested-vfs-canary.v1','checks_passed':len(checks),'checks':checks,'job_states':totals,'team_instances':interfaces,'process_runs':runs,'events':events,'resource_observation':{'state_bytes':size,'elapsed_seconds':round(elapsed,3),'max_concurrent_workers':2,'worker_limits':{'cpu_seconds':5,'address_space_bytes':256*1024*1024,'open_files':64,'file_bytes':16*1024*1024},'load_scope':'two canary teams; not production-scale qualification'},'native_dispatch_executed':False,'llm_model_binding':None,'different_model_assessment':None}
(out/'canary.json').write_text(json.dumps(report,indent=2)+'\n');(out/'team-interface.json').write_text(json.dumps(interfaces,indent=2)+'\n')
print(json.dumps({'checks_passed':len(checks),'job_states':totals,'state_bytes':size,'elapsed_seconds':round(elapsed,3),'evidence':str(out/'canary.json')},indent=2))
