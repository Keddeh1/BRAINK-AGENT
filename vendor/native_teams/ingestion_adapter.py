"""Explicit boundary to relayed ingestion v1 contract; preserves all instance identities.
Does not call a registry, grant scope, discover conversations or promote evidence claims.
"""
import argparse,hashlib,json,re
from pathlib import Path
ID=re.compile(r'^[A-Za-z0-9_.:-]{1,160}$')
ROLE_FIELDS={'manager':'workManager','production':'productionOutputManager','administration':'administration','verification':'verifier'}
def identifier(value):
    if not isinstance(value,str) or ID.fullmatch(value) is None:raise ValueError('invalid ingestion identity')
    return value

def reference(value):
    if not isinstance(value,str) or not value.strip() or len(value)>2048:raise ValueError('invalid ingestion reference')
    return value

def map_team(instance,project_id,parent_vfs_root,manager_registry_id=None):
    identifier(project_id);reference(parent_vfs_root)
    if manager_registry_id is not None:
        identifier(manager_registry_id)
        if not manager_registry_id.startswith('dot.'):raise ValueError('explicit dot registry handle required')
    if instance['schema_version']!='keddeh.team-instance.v1':raise ValueError('unrecognized source schema')
    team_id=identifier(instance['team_instance_id']);template_id=identifier(instance['team_template_id'])
    expected_root='teams/'+team_id
    if instance['vfs_root']!=expected_root:raise ValueError('team VFS identity mismatch')
    roles={};members=[];ids=set();roots=set()
    for member in instance['members']:
        role=member['role'];mid=identifier(member['member_id'])
        if role in roles or mid in ids:raise ValueError('duplicate role/member')
        path=reference(member['vfs_root'])
        if path!=expected_root+'/members/'+mid+'/vfs' or path in roots:raise ValueError('member VFS identity mismatch')
        if set(member['permissions'])-set(instance['permissions']):raise ValueError('permission inheritance mismatch')
        registry_identity=manager_registry_id if role=='manager' and manager_registry_id is not None else mid
        roles[role]=registry_identity;ids.add(mid);roots.add(path)
        members.append({'identity':registry_identity,'workerTemplateId':identifier(member['worker_template_id']),'workerInstanceId':mid,'vfsRoot':path,'stateRef':reference(path+'/vfs.sqlite3'),'scopeRef':reference(path+'#/identity.json')})
    if set(roles)!={'manager','production','administration','specialist','verification'}:raise ValueError('five responsibilities required')
    team={field:roles[role] for role,field in ROLE_FIELDS.items()};team['workers']=[roles['specialist']]
    composition={'teamTemplateId':template_id,'teamInstanceId':team_id,'vfsRoot':expected_root,'parentVfsRoot':parent_vfs_root,'projectId':project_id,'evidenceState':'packaged','members':members}
    return {'team':team,'composition':composition}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('export');p.add_argument('--instance-key',required=True);p.add_argument('--project-id',required=True);p.add_argument('--parent-vfs-root',required=True);p.add_argument('--manager-registry-id');a=p.parse_args()
    instances=json.loads(Path(a.export).read_text());instance=next(t for t in instances if t['instance_key']==a.instance_key)
    print(json.dumps(map_team(instance,a.project_id,a.parent_vfs_root,a.manager_registry_id),indent=2))
