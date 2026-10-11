"""Owner-operated local manager/administration CLI, not an authenticated network service."""
import argparse,json
from pathlib import Path
from runtime import Runtime,ROLES
p=argparse.ArgumentParser();s=p.add_subparsers(dest='operation',required=True)
a=s.add_parser('instantiate');a.add_argument('root');a.add_argument('instance_key');a.add_argument('--templates',default=str(Path(__file__).parent/'templates'))
a=s.add_parser('enqueue');a.add_argument('root');a.add_argument('team');a.add_argument('manager');a.add_argument('worker');a.add_argument('key');a.add_argument('text')
a=s.add_parser('inspect');a.add_argument('root');a.add_argument('team');a.add_argument('administrator')
a=p.parse_args();r=Runtime(a.root)
if a.operation=='instantiate':result=r.instantiate(a.instance_key,a.templates,set().union(*ROLES.values()))
elif a.operation=='enqueue':result=r.enqueue(a.team,a.manager,a.worker,a.key,a.text)
else:
    r.member(a.team,a.administrator,'inspect');result=r.export_interface(a.team)
print(json.dumps(result,indent=2,sort_keys=True))
