import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from braink_agent.manager import Manager, ROOT, NATIVE
from braink_agent.native import Fenced
from braink_agent.adapters import Dispatch, KeddehService

class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.m = Manager(self.root)
    def tearDown(self):
        self.tmp.cleanup()
    def birth(self, key="test"):
        return self.m.birth(key,"Exercise bounded native execution")
    def test_birth_restart_and_changed_request(self):
        first = self.birth()
        again = Manager(self.root).birth("test","Exercise bounded native execution")
        self.assertEqual(first, again)
        self.assertIsNone(first["modelBinding"])
        self.assertEqual(len(first["family"]["receipt_digests"]),27)
        with self.assertRaises(ValueError):
            self.m.birth("test","Changed purpose")
    def test_durable_readback_and_corruption(self):
        r=self.m.remember("one",{"purpose":"test"})
        self.assertEqual(Manager(self.root).recall("one"),{"purpose":"test"})
        with self.assertRaises(ValueError):self.m.remember("one",{"changed":True})
        path=self.m.vfs._object_path(r["digest"]);path.write_bytes(b"damaged")
        with self.assertRaises(RuntimeError):self.m.recall("one")
    def test_execution_and_observer_are_separate(self):
        b=self.birth();tid=b["team"]["team_instance_id"]
        job=self.m.enqueue(tid,"production","one","Native persistence")
        actor=self.m.run(tid,"production")
        self.assertEqual(self.m.runtime.job(job["id"])["state"],"PRODUCED")
        observed=self.m.verify(tid,job["id"])
        self.assertNotEqual(actor["actor_pid"],observed["pid"])
        self.assertEqual(Manager(self.root).runtime.job(job["id"])["state"],"VERIFIED")
        self.assertEqual(self.m.verify(tid,job["id"]),observed)
    def test_claim_fencing_and_recovery(self):
        b=self.birth();t=b["team"];tid=t["team_instance_id"]
        wid=next(m["member_id"] for m in t["members"] if m["role"]=="production")
        self.m.enqueue(tid,"production","one","recover")
        old=self.m.runtime.claim(tid,wid,.05);time.sleep(.07)
        new=self.m.runtime.claim(tid,wid)
        with self.assertRaises(Fenced):self.m.runtime.produce(old,b"WRONG")
        self.m.runtime.produce(new,b"RECOVER")
        self.assertEqual(new["epoch"],2)
    def test_crash_after_vfs_write_reconciles_one_binding(self):
        b=self.birth();t=b["team"];tid=t["team_instance_id"]
        wid=next(m["member_id"] for m in t["members"] if m["role"]=="production")
        job=self.m.enqueue(tid,"production","one","crash-safe")
        r=subprocess.run([sys.executable,str(NATIVE/'worker.py'),str(self.m.runtime.root),tid,wid,'--fault','after-write','--lease','.05'])
        self.assertEqual(r.returncode,75);time.sleep(.07)
        self.m.run(tid,"production");self.m.verify(tid,job["id"])
        result=json.loads(self.m.runtime.job(job["id"])["result"])
        self.assertEqual(len(self.m.runtime.member_store(tid,wid).binding_history(result['path'])),1)
    def test_concurrent_birth_identity(self):
        with ThreadPoolExecutor(max_workers=3) as pool:
            results=list(pool.map(lambda _:Manager(self.root).birth("same","Same purpose"),range(3)))
        self.assertTrue(all(r==results[0] for r in results))
    def test_bounded_queue_and_retry_conflict(self):
        b=self.birth();tid=b["team"]["team_instance_id"]
        self.m.enqueue(tid,"production","same","one")
        with self.assertRaises(ValueError):self.m.enqueue(tid,"production","same","two")
        with self.assertRaises(ValueError):self.m.enqueue(tid,"production","large","x"*16385)
        with self.assertRaises(ValueError):self.m.enqueue(tid,"verification","bad","one")
    def test_sector_separate_native_teams_no_expertise_invention(self):
        s={"id":"fixture","title":"Synthetic fixture","bottleneck":"Test only, no market claim",
           "sources":[{"url":"https://example.org/test","title":"Synthetic fixture","claim":"Test input","accessed":"2026-10-11"}],
           "deliveryPurpose":"Deliver fixture", "analystPurpose":"Challenge fixture", "foundryRefs":[]}
        r=self.m.admit_sector(s)
        self.assertNotEqual(r["deliveryTeam"],r["analystTeam"])
        self.assertEqual(r["expertise"],"REQUIRES_APPLIED_QUALIFICATION")
        self.assertEqual(Manager(self.root).admit_sector(s),r)
        self.assertIsNone(r['assessmentReceipt'])
    def test_composed_native_workload(self):
        circuit=json.loads((ROOT/'runtime/circuits/bell.json').read_text())
        shell=json.loads((ROOT/'runtime/shells/tetrahedron.json').read_text())
        r=self.m.undertake("finite","Validate circuit and finite shell",circuit,shell)
        self.assertEqual(r['actor']['tensor_shell']['signed_volume_times_six'],1)
        self.assertFalse(r['physicalHardware'])
        self.assertEqual(Manager(self.root).undertake("finite","Validate circuit and finite shell",circuit,shell),r)
    def test_oversized_native_result_rejected_before_commit(self):
        with self.assertRaises(ValueError):
            self.m.undertake("oversized","Reject before state",{'schema':'keddeh.quantum.circuit.v1','qubits':13,'gates':[]},None)
        self.assertFalse((self.root/'family.sqlite3').exists())
        with self.assertRaises(ValueError):self.m.birth('x'*100,'Oversized custody key')
        self.assertFalse((self.root/'family.sqlite3').exists())
        shell=json.loads((ROOT/'runtime/shells/tetrahedron.json').read_text())
        shell['identity']='a'*30000
        with self.assertRaises(ValueError):self.m.undertake('large-shell','Reject amplification',None,shell)
        self.assertFalse((self.root/'family.sqlite3').exists())
    def test_family_database_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            target=Path(outside)/'victim.sqlite3'
            (self.root/'family.sqlite3').symlink_to(target)
            with self.assertRaises(ValueError):self.birth()
            self.assertFalse(target.exists())
    def test_remote_uncertainty_never_replays(self):
        class Transport:
            def __init__(self):self.calls=[]
            def call(self,name,args):
                self.calls.append(name)
                if name=='agent_dispatch':raise TimeoutError()
                return {"commandId":args['commandId'],"status":"ACTOR_RECORDED"}
        t=Transport();s=KeddehService(t)
        r=Dispatch("cmd","skill://teams/local.manager.v1","ns",0,{"op":"inspect"},
            {"objective":"test","reason":"test","evidence":[],"expectedEffect":"read","rollback":"none","impact":{}})
        self.assertEqual(self.m.dispatch(s,r)['state'],'UNCERTAIN_RECONCILE_REQUIRED')
        Manager(self.root).dispatch(s,r)
        self.assertEqual(t.calls,['agent_dispatch'])
        result=self.m.reconcile(s,"cmd")
        self.assertIsNone(result['assessment'])
        self.assertEqual(t.calls,['agent_dispatch','command_status'])

if __name__=='__main__':unittest.main()
