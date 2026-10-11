"""Bounded native CI entrypoint; emits execution evidence, never deployment approval."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[1]
def main():
    with tempfile.TemporaryDirectory(prefix='braink-ci-') as temp:
        commands=[
            [sys.executable,'scripts/verify-source.py'],
            ['node','--check','web/app.js'],
            [sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py','-v'],
            [sys.executable,'tests/braink-family.test.py'],
            [sys.executable,'vendor/native_teams/canary.py','--state',temp+'/native-state','--evidence',temp+'/native-evidence'],
        ]
        records=[]
        for argv in commands:
            started=time.monotonic()
            r=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=120)
            output=(r.stdout+r.stderr).decode(errors='replace')
            records.append({'command':argv,'exitCode':r.returncode,'seconds':round(time.monotonic()-started,3),
                            'output':output,'outputSha256':hashlib.sha256((r.stdout+r.stderr)).hexdigest()})
            print(output,flush=True)
            if r.returncode:break
        evidence={'schema':'braink.agent.ci-execution.v1','state':'PASSED' if all(r['exitCode']==0 for r in records) and len(records)==len(commands) else 'FAILED',
                  'runs':records,'actorExecution':'LOCAL_NATIVE_RUNTIME','durableReadback':'TESTED',
                  'independentAssessmentReceipt':None,'productionDeployment':'NOT_PERFORMED'}
        dest=ROOT/'evidence/local';dest.mkdir(parents=True,exist_ok=True)
        (dest/'ci.json').write_text(json.dumps(evidence,indent=2)+'\n')
        print(json.dumps({k:v for k,v in evidence.items() if k!='runs'}))
        return 0 if evidence['state']=='PASSED' else 1
if __name__=='__main__':raise SystemExit(main())
