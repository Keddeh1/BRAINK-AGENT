"""Measure one child with wait-based OS resource accounting; no synthetic memory claims."""
import json,resource,subprocess,sys,time
started=time.monotonic()
try:
    child=subprocess.run(sys.argv[1:],capture_output=True,text=True,timeout=10)
    status,stdout,stderr=child.returncode,child.stdout,child.stderr
except subprocess.TimeoutExpired as exc:
    status=124;stdout=(exc.stdout or b'').decode() if isinstance(exc.stdout,bytes) else exc.stdout or '';stderr='child timeout after 10 seconds'
usage=resource.getrusage(resource.RUSAGE_CHILDREN)
print(json.dumps({'exit_code':status,'stdout':stdout,'stderr':stderr,'measurement':{'elapsed_seconds':round(time.monotonic()-started,6),'child_peak_rss_bytes':usage.ru_maxrss*1024,'user_cpu_seconds':usage.ru_utime,'system_cpu_seconds':usage.ru_stime,'minor_page_faults':usage.ru_minflt,'major_page_faults':usage.ru_majflt,'source':'Linux getrusage(RUSAGE_CHILDREN); fresh single-command measurement process','scope':'child process high-water RSS; not combined concurrent/process-tree peak'}}))
