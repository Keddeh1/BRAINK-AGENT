"""Build a deterministic source archive; exclude credentials and runtime state."""
from pathlib import Path
import hashlib,io,json,subprocess,tarfile
ROOT=Path(__file__).resolve().parents[1]
def validate_name(name):
    p=Path(name)
    allowed_dirs={'braink_agent','contracts','docs','evidence','runtime','scripts','tests','vendor','web'}
    allowed_roots={'README.md','NOTICE','Makefile','SOURCE-PROVENANCE.json','.gitignore'}
    if p.is_absolute() or '..' in p.parts or (len(p.parts)>1 and p.parts[0] not in allowed_dirs) or (len(p.parts)==1 and name not in allowed_roots):
        raise ValueError('SOURCE_ALLOWLIST_REJECTED')
    if any(part.lower().startswith('.env') or part.lower() in {'.git','.state','.aws','.ssh','credentials','secrets','private'} for part in p.parts):
        raise ValueError('PRIVATE_PATH_REJECTED')
    if p.suffix.lower() in {'.token','.key','.pem','.p12','.sqlite','.sqlite3','.db','.pyc'} or name.startswith('evidence/local/'):
        raise ValueError('PRIVATE_FILE_REJECTED')
def main():
    subprocess.run(['git','diff','--quiet'],cwd=ROOT,check=True)
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    paths=[p for p in paths if p]
    if not paths:raise SystemExit('Stage reviewed source before packaging')
    entries=[]
    for name in sorted(paths):
        path=ROOT/name
        validate_name(name)
        if path.is_symlink():
            raise SystemExit('Forbidden source-package path: '+name)
        entries.append((name,path.read_bytes()))
    output=ROOT/'dist';output.mkdir(exist_ok=True)
    archive=output/'BRAINK_AGENT.tar'
    with tarfile.open(archive,'w') as tar:
        for name,data in entries:
            info=tarfile.TarInfo('BRAINK_AGENT/'+name);info.size=len(data);info.mode=0o644;info.mtime=0
            tar.addfile(info,io.BytesIO(data))
    manifest={'schema':'braink.agent.source-package.v1','sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
              'files':[{'path':name,'sha256':hashlib.sha256(data).hexdigest()} for name,data in entries],
              'deployment':'NOT_PERFORMED','assessmentReceipt':None}
    (output/'package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'archive':str(archive),'sha256':manifest['sha256'],'files':len(entries)}))
if __name__=='__main__':main()
