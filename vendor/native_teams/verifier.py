"""Verification coordinator CLI; only its owned observer child can supply observations."""
import argparse,json
from runtime import Runtime
p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('team');p.add_argument('verifier');p.add_argument('job');a=p.parse_args()
observation=Runtime(a.root).verify_job(a.team,a.verifier,a.job)
print(json.dumps({'job_id':a.job,'state':'VERIFIED',**observation},sort_keys=True))
