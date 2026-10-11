"""Cross-module test against the supplied unmodified ingestion package, synthetic data only."""
import argparse,copy,hashlib,io,json,os,sqlite3,sys,tempfile,time,zipfile
from pathlib import Path
from dataclasses import replace
from ingestion_adapter import map_team
p=argparse.ArgumentParser();p.add_argument('--ingestion-source',required=True);p.add_argument('--export',required=True);p.add_argument('--evidence',required=True);a=p.parse_args()
source=Path(a.ingestion_source).resolve();sys.path[:]=[str(source)]+[x for x in sys.path if Path(x).resolve()!=Path(__file__).resolve().parent]
from runtime.account_ingestion.service import AccountData,Principal,Scope,Command,IngestionError
from runtime.account_ingestion.managers import ChatManagers
import jsonschema
instances=json.loads(Path(a.export).read_text());instance=next(x for x in instances if x['instance_key']=='beta')
checks=[];denials=[]
def check(name,value):
    assert value,name
    checks.append(name)
def deny(name,fn,code=None):
    try:fn()
    except IngestionError as exc:
        if code:assert code in str(exc),(name,str(exc))
        denials.append({'name':name,'error':str(exc)});checks.append(name)
    else:raise AssertionError(name)
def command(key,version):return Command(key,version,'Synthetic team-registry interoperability','Reference assignment only','Remove disposable canary state','Local synthetic scope only','local-test-reference-not-a-grant','team-integration-canary')
scope=Scope('tenant-canary','account-canary','workspace-canary','foundry-canary','project-canary','source-canary')
actions=('account_import','account_conversation','account_search','manager_read','manager_update')
principal=Principal('principal-local-canary','owner-local-canary','operator',(scope,),actions,tuple('account-data:'+x for x in actions)+('native.local-artifact-fixture',),('foundry-canary',),time.time()+300)
conversation={'id':'conversation-team-canary','title':'Synthetic nested team roundtrip','mapping':{'root':{'parent':None,'children':[],'message':None}}}
other={**conversation,'id':'conversation-team-canary-other'}
stream=io.BytesIO()
with zipfile.ZipFile(stream,'w') as archive:archive.writestr('conversations.json',json.dumps([conversation,other]))
raw=map_team(instance,scope.project,'vfs://project-canary')
packet=map_team(instance,scope.project,'vfs://project-canary','dot.local-beta')
source_hashes={f:hashlib.sha256((source/f).read_bytes()).hexdigest() for f in ['runtime/account_ingestion/managers.py','runtime/account_ingestion/service.py','runtime/account_ingestion/team-interface.v1.schema.json']}
schema=json.loads((source/'runtime/account_ingestion/team-interface.v1.schema.json').read_text())
jsonschema.Draft7Validator({'$ref':'#/$defs/composition',**schema}).validate(packet['composition']);checks.append('actual ingestion composition schema')
with tempfile.TemporaryDirectory(prefix='keddeh-team-registry-') as td:
    data_root=Path(td)/'private';service=AccountData(data_root);service.import_snapshot(principal,scope,command('import',0),'chatgpt-owner-export',stream.getvalue(),'synthetic.zip')
    managers=ChatManagers(service);discovered=managers.transition(principal,scope,conversation['id'],command('discover',0),'discovered')
    def assign(payload,cmd=command('assign',1),who=principal,sc=scope,cid=conversation['id']):
        return managers.transition(who,sc,cid,cmd,'assigned',manager=payload['team']['workManager'],actor=payload['team']['workers'][0],verifier=payload['team']['verifier'],team=payload['team'],composition=payload['composition'],plan=[{'id':'inspect-reference','dependsOn':[]}],actions=['account_search'],capability_refs=[{'sectorId':'DATA_INFORMATION_GOVERNANCE','functionId':'lineage','capabilityId':'native.local-artifact-fixture'}])
    deny('original direct UUID assignment rejected',lambda:assign(raw),'DOT_MANAGER_REQUIRED')
    check('original failure preserves discovered state',managers.read(principal,scope,conversation['id'])['state']=='discovered')
    bad=copy.deepcopy(packet);bad['composition']['projectId']='other-project'
    deny('cross-project composition rejected',lambda:assign(bad),'COMPOSITION_SCOPE_MISMATCH')
    bad=copy.deepcopy(packet);bad['composition']['members'][1]['vfsRoot']=bad['composition']['members'][0]['vfsRoot']
    deny('duplicate member VFS rejected',lambda:assign(bad),'COMPOSITION_MEMBERS_MISMATCH')
    bad=copy.deepcopy(packet);bad['composition']['unexpected']=True
    deny('unexpected composition field rejected',lambda:assign(bad),'INVALID_COMPOSITION')
    deny('missing registry action grant rejected',lambda:assign(packet,who=replace(principal,tools=tuple(x for x in actions if x!='account_search'))),'ACCESS_DENIED')
    deny('stale expected registry version rejected',lambda:assign(packet,command('stale',0)),'VERSION_CONFLICT')
    assigned=assign(packet);check('assigned reference equals mapped composition',assigned['teamComposition']['reference']==packet['composition'])
    check('native member UUIDs preserved',set(m['workerInstanceId'] for m in assigned['teamComposition']['reference']['members'])==set(m['member_id'] for m in instance['members']))
    check('explicit manager handle is separate from native instance identity',assigned['managerId']=='dot.local-beta' and next(m for m in assigned['teamComposition']['reference']['members'] if m['identity']=='dot.local-beta')['workerInstanceId']==next(m['member_id'] for m in instance['members'] if m['role']=='manager'))
    check('assignment does not confer local verification or execution',assigned['teamComposition']['locallyVerified'] is False and assigned['workerRunning'] is False and assigned['executionId'] is None)
    check('identical command replay is idempotent',assign(packet)==assigned)
    changed=copy.deepcopy(packet);changed['composition']['evidenceState']='independently_verified'
    deny('changed duplicate assignment rejected',lambda:assign(changed),'COMMAND_ID_CONFLICT')
    deny('native admission not invented',lambda:managers.transition(principal,scope,conversation['id'],command('admit-without-native',2),'admitted'),'NATIVE_EVIDENCE_REQUIRED')
    managers.transition(principal,scope,other['id'],command('discover-other',0),'discovered')
    deny('one-to-one manager cannot be assigned to another chat',lambda:assign(packet,command('assign-other',1),cid=other['id']),'MANAGER_ALREADY_ASSIGNED')
    service.close();service=AccountData(data_root);managers=ChatManagers(service)
    reopened=managers.read(principal,scope,conversation['id']);check('registry survives close/reopen exactly',reopened==assigned)
    deny('cross-account registry read rejected',lambda:managers.read(principal,replace(scope,account='other-account'),conversation['id']),'ACCESS_DENIED')
    # Independently reopen SQLite mode=ro without calling the manager read API.
    with sqlite3.connect((data_root/'account-data.sqlite3').as_uri()+'?mode=ro',uri=True) as observer_db:
        row=observer_db.execute('SELECT record FROM chat_managers WHERE chat_key=?',(ChatManagers.key(scope,conversation['id']),)).fetchone()
    check('direct SQLite composition readback matches',json.loads(row[0])['teamComposition']['reference']==packet['composition'])
    service.close()
result={'schema_version':'keddeh.team-ingestion-roundtrip.v1','checks_passed':len(checks),'checks':checks,'denials':denials,'ingestion_declared_commit':'f48a019b5ec3b9b31a4c0672db43a1e2482a143e','ingestion_library_file_id':'libfile_9c5f6ac1aebc8191ade47c9daadbf749','ingestion_archive_sha256':'d2964b2cb661a5c37a3cad1684d5725092f8c0d1b8f0df6f02040511d2e290ae','ingestion_source_sha256':source_hashes,'assignment':packet,'registry_readback':reopened,'native_dispatch_executed':False,'credentials_created':False,'scope':'Actual two-module reference assignment and persistence; synthetic ephemeral principal and data, no native admission or real account ingestion'}
out=Path(a.evidence);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'checks_passed':len(checks),'state':reopened['state'],'locallyVerified':reopened['teamComposition']['locallyVerified'],'evidence':str(out)},indent=2))
