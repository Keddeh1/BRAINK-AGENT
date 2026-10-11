#!/usr/bin/env python3
"""KEDDEH Systems enterprise companion runtime.

HTML remains the active portable carrier. This process is a loopback/host adapter that
persists enterprise state, serves readback, and executes only declared product operations.
It does not convert local receipts into external/provider proof.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, os, sqlite3, threading, time, uuid
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "config" / "product_registry.json"
CARRIER_PATH = ROOT / "KEDDEH_ENTERPRISE_SYSTEMS_V1.html"
STATE_SCHEMA = "kex.keddeh.enterprise.state.v1"
QUALIFIED_EVIDENCE = {"OBSERVED", "SOURCE_VERIFIED", "IMPLEMENTED", "TESTED", "VALIDATED", "EXECUTION_OBSERVED"}
ACTIVE = (-3, -2, 1, 2, 3)

def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha(obj: Any) -> str:
    raw = obj if isinstance(obj, (bytes, bytearray)) else canon(obj).encode()
    return hashlib.sha256(raw).hexdigest()

def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def initial_state() -> dict[str, Any]:
    return {
        "schema": STATE_SCHEMA, "generation": 1, "continuations": {}, "claims": {}, "relations": [],
        "evidence": [], "promotions": {}, "vfs": {"/README.enterprise": "KEDDEH Enterprise resident VFS"},
        "identity": {"principals": {"operator": {"scopes": ["enterprise:read", "enterprise:operate", "governance:write"]}}},
        "casepath": {"matters": {}}, "claimpath": {"claims": {}}, "workbook": {"sheets": {"Sheet1": {}}},
        "cloud": {"nodes": {}, "deployments": {}}, "mesh": {"nodes": {}, "edges": []}, "domain": {"zones": {}},
        "agents": {"skills": {}, "tasks": {}}, "reflection": {"rules": {}}, "quantum": {"last": None},
        "matrix": {"objects": {}, "relations": []}, "os": {"processes": {}}, "checkpoints": {}, "kapps": {},
    }

import queue

class EnterpriseStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path); self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.subscribers: list[queue.Queue] = []
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA mmap_size=268435456")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA cache_size=-64000")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ledger(
          seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, kind TEXT NOT NULL, subject TEXT NOT NULL,
          classification TEXT NOT NULL, detail TEXT NOT NULL, previous_digest TEXT, digest TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS nonces(
          jti TEXT PRIMARY KEY, consumed_at TEXT NOT NULL, expires_at INTEGER NOT NULL
        );
        """)
        self.registry = json.loads(REGISTRY_PATH.read_text())
        self.products = {p["id"]: p for p in self.registry["products"]}
        if self.conn.execute("SELECT 1 FROM kv WHERE key='state'").fetchone() is None:
            self._save(initial_state())
    def close(self):
        with self.lock: self.conn.close()
    def subscribe(self) -> queue.Queue:
        with self.lock:
            q = queue.Queue(maxsize=256)
            self.subscribers.append(q)
            return q
    def unsubscribe(self, q: queue.Queue):
        with self.lock:
            if q in self.subscribers:
                self.subscribers.remove(q)
    def broadcast(self, event_type: str, data: Any):
        with self.lock:
            payload = f"event: {event_type}\ndata: {json.dumps(data, sort_keys=True)}\n\n".encode("utf-8")
            dead = []
            for q in self.subscribers:
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    dead.append(q)
            for d in dead:
                if d in self.subscribers:
                    self.subscribers.remove(d)
    def consume_nonce(self, jti: str, expires_at: int) -> bool:
        with self.lock:
            try:
                self.conn.execute("INSERT INTO nonces(jti, consumed_at, expires_at) VALUES(?,?,?)", (jti, utc(), expires_at))
                return True
            except sqlite3.IntegrityError:
                return False
    def is_nonce_consumed(self, jti: str) -> bool:
        with self.lock:
            return self.conn.execute("SELECT 1 FROM nonces WHERE jti=?", (jti,)).fetchone() is not None
    def _load(self) -> dict[str, Any]:
        row = self.conn.execute("SELECT value FROM kv WHERE key='state'").fetchone()
        return json.loads(row[0]) if row else initial_state()
    def _save(self, state: dict[str, Any]):
        self.conn.execute("INSERT INTO kv(key,value) VALUES('state',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (canon(state),))
    def state(self) -> dict[str, Any]:
        with self.lock: return copy.deepcopy(self._load())
    def append_ledger(self, kind: str, subject: str, detail: Any, classification="EXECUTION_OBSERVED") -> dict[str, Any]:
        with self.lock:
            row=self.conn.execute("SELECT digest FROM ledger ORDER BY seq DESC LIMIT 1").fetchone(); prev=row[0] if row else None
            core={"at":utc(),"kind":kind,"subject":subject,"classification":classification,"detail":detail,"previous_digest":prev}
            dig=sha(core)
            cur=self.conn.execute("INSERT INTO ledger(at,kind,subject,classification,detail,previous_digest,digest) VALUES(?,?,?,?,?,?,?)",
                (core["at"],kind,subject,classification,canon(detail),prev,dig))
            receipt = {"seq":cur.lastrowid,**core,"digest":dig}
            self.broadcast("LEDGER_RECEIPT", receipt)
            return receipt
    def verify_ledger(self) -> dict[str, Any]:
        rows=self.conn.execute("SELECT seq,at,kind,subject,classification,detail,previous_digest,digest FROM ledger ORDER BY seq").fetchall()
        prev=None
        for row in rows:
            seq,at,kind,subject,classification,detail,previous_digest,digest=row
            core={"at":at,"kind":kind,"subject":subject,"classification":classification,"detail":json.loads(detail),"previous_digest":previous_digest}
            if previous_digest != prev or sha(core) != digest:
                return {"status":"FAIL","seq":seq,"count":len(rows)}
            prev=digest
        return {"status":"PASS","count":len(rows),"head":prev}
    def ledger(self, limit=100) -> list[dict[str, Any]]:
        rows=self.conn.execute("SELECT seq,at,kind,subject,classification,detail,previous_digest,digest FROM ledger ORDER BY seq DESC LIMIT ?",(int(limit),)).fetchall()
        return [{"seq":r[0],"at":r[1],"kind":r[2],"subject":r[3],"classification":r[4],"detail":json.loads(r[5]),"previous_digest":r[6],"digest":r[7]} for r in reversed(rows)]
    def events(self, limit=100) -> list[dict[str, Any]]:
        return self.ledger(limit)
    def product(self, pid: str) -> dict[str, Any]:
        if pid not in self.products: raise KeyError(f"unknown product: {pid}")
        return copy.deepcopy(self.products[pid])
    def operate(self, pid: str, op: str, payload: dict[str, Any]) -> dict[str, Any]:
        product=self.product(pid)
        if op not in product.get("operations",[]): raise ValueError(f"operation not declared: {op}")
        with self.lock:
            st=self._load(); result=self._dispatch(st,pid,op,payload); st["generation"]=int(st.get("generation",0))+1; self._save(st)
            receipt=self.append_ledger("OPERATE",pid,{"operation":op,"payload":payload,"result":result})
            return {"ok":True,"product":pid,"operation":op,"result":result,"receipt":receipt,"generation":st["generation"]}
    def _dispatch(self, s: dict[str,Any], pid: str, op: str, p: dict[str,Any]) -> Any:
        if op == "status": return {"product":self.product(pid),"generation":s["generation"]}
        if pid=="system://braink":
            if op=="start_continuation":
                cid=str(p.get("id") or uuid.uuid4()); s["continuations"][cid]={"id":cid,"coordinate":str(p.get("coordinate") or "il-llm://braink/root"),"observer":str(p.get("observer") or "operator"),"logical_time":1,"route":[],"return_route":[],"state":p.get("state") or {}}; return copy.deepcopy(s["continuations"][cid])
            if op=="advance_continuation":
                c=s["continuations"][str(p["id"])]; c["coordinate"]=str(p["coordinate"]); c["logical_time"]+=1
                if p.get("via"): c["route"].append(str(p["via"])); c["state"].update(p.get("state_patch") or {}); return copy.deepcopy(c)
            if op=="resolve_capability":
                q=str(p["capability"]).lower(); m=[x for x in self.products.values() if any(q in c.lower() for c in x["capabilities"]) or any(q in o.lower() for o in x["operations"])]; return {"status":"RESOLVED" if m else "UNKNOWN","matches":[x["id"] for x in m]}
        if pid=="volume://braink/il-llm/sovereign-v1":
            if op=="register_claim":
                cid=str(p["id"]); old=s["claims"].get(cid); c={"id":cid,"subject":str(p.get("subject") or cid),"predicate":str(p.get("predicate") or "ASSERTS"),"object":p.get("object"),"source":str(p["source"]),"status":str(p.get("status") or "OBSERVED"),"scope":str(p.get("scope") or "global"),"epoch":p.get("epoch"),"session":p.get("session")};
                if old and old.get("object") != c.get("object"): c["status"]="CONFLICTED"
                s["claims"][cid]=c; return copy.deepcopy(c)
            if op=="relate": r={k:p.get(k) for k in ("source","predicate","target","scope","observer","evidence","epoch")}; s["relations"].append(r); return copy.deepcopy(r)
            if op=="resolve_claim":
                cid=str(p["id"]); c=s["claims"].get(cid)
                if not c:return {"status":"UNRESOLVED","id":cid}
                ev=[e for e in s["evidence"] if e["subject"]==cid and (not p.get("epoch") or e.get("epoch")==p.get("epoch")) and (not p.get("session") or e.get("session")==p.get("session"))]
                qual=[e for e in ev if e["classification"] in QUALIFIED_EVIDENCE]; return {"status":"CONFLICTED" if c.get("status")=="CONFLICTED" else ("RESOLVED" if qual else "OBSERVED_UNQUALIFIED"),"claim":c,"qualified_evidence":qual}
        if pid in {"runtime://kex/core","app://kex/active-state"} and op in {"transition","apply_state"}:
            a,b=int(p["from"]),int(p["to"])
            if a not in ACTIVE or b not in ACTIVE:return {"status":"REJECT","reason":"ZERO_OR_OUTSIDE_ACTIVE_CORRIDOR"}
            return {"status":"PASS","from":a,"to":b,"topological_distance":abs(ACTIVE.index(a)-ACTIVE.index(b)),"scalar_delta":b-a}
        if pid=="app://kex-one" and op in {"map_origin","inverse_origin"}: return {"input":p["value"],"output":float(p["value"])+(1 if op=="map_origin" else -1)}
        if pid=="volume://kex/ssd":
            if op=="mount_volume": path=f"/volumes/{p['name']}/.volume";s["vfs"][path]=canon({"name":p["name"],"mounted_at":utc()});return {"mounted":True,"path":path}
            if op=="write_file": path=str(p["path"]);s["vfs"][path]=p.get("content") if isinstance(p.get("content"),str) else canon(p.get("content"));return {"written":True,"path":path}
            if op=="read_file": path=str(p["path"]);return {"found":path in s["vfs"],"path":path,"content":s["vfs"].get(path)}
            if op=="list_files": prefix=str(p.get("prefix") or "/");return {"files":sorted(k for k in s["vfs"] if k.startswith(prefix))}
        if pid=="app://braink/workbook":
            if op=="create_sheet": s["workbook"]["sheets"].setdefault(str(p["name"]),{});return {"status":"READY","name":p["name"]}
            if op=="write_cell": sh=str(p.get("sheet") or "Sheet1");cell=str(p["cell"]).upper();s["workbook"]["sheets"].setdefault(sh,{})[cell]={"value":p.get("value"),"kind":str(p.get("kind") or "VALUE")};return s["workbook"]["sheets"][sh][cell]
            if op=="read_cell": return s["workbook"]["sheets"].get(str(p.get("sheet") or "Sheet1"),{}).get(str(p["cell"]).upper(),{"status":"EMPTY"})
        if pid=="app://casepath":
            matters=s["casepath"]["matters"]
            if op=="create_matter": mid=str(p.get("id") or uuid.uuid4());matters[mid]={"id":mid,"story":str(p.get("story") or ""),"fields":p.get("fields") or {},"package":None};return matters[mid]
            x=matters[str(p["id"])]
            if op=="append_story": x["story"]+=("\n" if x["story"] else "")+str(p["text"]);return x
            if op=="answer_field": x["fields"][str(p["field"])]=p.get("value");return x
            if op=="assess_gaps": req=p.get("required") or ["what_happened","when","where","people","outcome"];return {"gaps":[k for k in req if k not in x["fields"]]}
            if op=="select_package": x["package"]=str(p["package"]);x["documents"]=p.get("documents") or [];return x
            if op=="update_section79_pool":
                pool=float(p.get("net_pool",0.0)); app_pct=float(p.get("contributions_applicant",50.0)); resp_pct=float(p.get("contributions_respondent",50.0)); s75_adj=float(p.get("s75_adjustments",0.0))
                final_app=app_pct+s75_adj; final_resp=resp_pct-s75_adj
                x["section_79"]={"net_pool":pool,"applicant_share_pct":final_app,"applicant_share_dollar":round(pool*(final_app/100.0),2),"respondent_share_pct":final_resp,"respondent_share_dollar":round(pool*(final_resp/100.0),2),"s75_adjustment_pct":s75_adj,"updated_at":utc()}
                return x["section_79"]
            if op=="record_parenting_matrix":
                x["parenting_matrix"]={"schedule_type":str(p.get("schedule_type","5-2-2-5")),"applicant_overnights":int(p.get("applicant_overnights",7)),"respondent_overnights":int(p.get("respondent_overnights",7)),"changeover":str(p.get("changeover_location","School / Neutral Venue")),"school_holidays":str(p.get("school_holidays","50/50 Equal Division")),"recorded_at":utc()}
                return x["parenting_matrix"]
            if op=="generate_affidavit_evidence_bundle":
                ev_items=p.get("evidence_items",[]); ev_digests=[sha(item) for item in ev_items]; bundle_root=sha("::".join(ev_digests)) if ev_digests else sha(x["id"])
                x["affidavit_bundle"]={"deponent":str(p.get("deponent","Self-Represented Party")),"court":str(p.get("court","Federal Circuit and Family Court of Australia")),"filing_date":str(p.get("filing_date",utc())),"evidence_count":len(ev_items),"evidence_merkle_root":bundle_root,"sealed_receipt_at":utc()}
                return x["affidavit_bundle"]
        if pid=="app://claimpath":
            claims=s["claimpath"]["claims"]
            if op=="create_claim": cid=str(p.get("id") or uuid.uuid4());claims[cid]={"id":cid,"story":str(p.get("story") or ""),"fields":p.get("fields") or {},"evidence":[],"service":None};return claims[cid]
            x=claims[str(p["id"])]
            if op=="append_story": x["story"]+=("\n" if x["story"] else "")+str(p["text"]);return x
            if op=="add_evidence": e={"id":str(p.get("evidence_id") or uuid.uuid4()),"kind":str(p.get("kind") or "DOCUMENT"),"source":str(p["source"]),"status":str(p.get("status") or "OBSERVED")};x["evidence"].append(e);return e
            if op=="assess_gaps": req=p.get("required") or ["event","loss","counterparty","evidence_basis"];return {"gaps":[k for k in req if k not in x["fields"]],"evidence_count":len(x["evidence"])}
            if op=="select_service": x["service"]=str(p["service"]);return x
        if pid=="cloud://keddeh/k-cloud":
            if op=="register_node": nid=str(p["id"]);s["cloud"]["nodes"][nid]={"id":nid,"capabilities":p.get("capabilities") or [],"state":str(p.get("state") or "READY")};return s["cloud"]["nodes"][nid]
            if op=="deploy_kapp": did=str(p.get("id") or uuid.uuid4());node=str(p["node"]); assert node in s["cloud"]["nodes"];s["cloud"]["deployments"][did]={"id":did,"node":node,"package":str(p["package"]),"state":"ADMITTED_LOCAL","external_receipt":None};return s["cloud"]["deployments"][did]
            if op=="deployment_status": return s["cloud"]["deployments"].get(str(p["id"]),{"status":"NOT_FOUND"})
        if pid=="mesh://keddeh/software-nodes":
            if op=="register_node": nid=str(p["id"]);s["mesh"]["nodes"][nid]={"id":nid,"revision":1,"capabilities":p.get("capabilities") or []};return s["mesh"]["nodes"][nid]
            if op=="connect_nodes": e={"a":str(p["a"]),"b":str(p["b"]),"state":"CONNECTED"};s["mesh"]["edges"].append(e);return e
            if op=="gossip": src=s["mesh"]["nodes"][str(p["source"])];src["revision"]+=1;return {"source":src["id"],"revision":src["revision"]}
        if pid=="domain://keddeh/space":
            if op=="define_zone": z=str(p["zone"]).lower();s["domain"]["zones"].setdefault(z,{"zone":z,"records":{},"routes":{},"public_readback":None});return s["domain"]["zones"][z]
            z=s["domain"]["zones"][str(p["zone"]).lower()]
            if op=="set_record": z["records"][str(p["name"])]=str(p.get("value") or "");return z
            if op=="bind_route": z["routes"][str(p["host"])]=str(p["service"]);return z
            if op=="resolve_name": return {"status":"RESOLVED_RESIDENT","record":z["records"].get(str(p.get("name") or "")),"service":z["routes"].get(str(p.get("host") or p.get("name") or "")),"public_readback":z["public_readback"]}
        if pid=="runtime://braink/agent-skill-fabric":
            if op=="register_skill": sid=str(p["id"]);s["agents"]["skills"][sid]={"id":sid,"name":str(p["name"]),"capabilities":p.get("capabilities") or []};return s["agents"]["skills"][sid]
            if op=="create_task": tid=str(p.get("id") or uuid.uuid4());s["agents"]["tasks"][tid]={"id":tid,"goal":str(p["goal"]),"required_capability":str(p.get("required_capability") or ""),"state":"CREATED"};return s["agents"]["tasks"][tid]
            if op=="resolve_task_capability": t=s["agents"]["tasks"][str(p["id"])];q=t["required_capability"].lower();m=[x["id"] for x in s["agents"]["skills"].values() if any(q in str(c).lower() for c in x["capabilities"])];t["matches"]=m;t["state"]="RESOLVED" if m else "UNKNOWN";return t
        if pid=="runtime://braink/self-reflection":
            if op=="register_rule": rid=str(p["id"]);s["reflection"]["rules"][rid]={"id":rid,"pattern":str(p["pattern"]),"replacement":str(p.get("replacement") or ""),"meaning":str(p.get("meaning") or rid)};return s["reflection"]["rules"][rid]
            if op=="scan_text":
                import re
                hits=[]
                for r in s["reflection"]["rules"].values():
                    hits += [{"rule":r["id"],"match":m.group(0),"index":m.start(),"replacement":r["replacement"]} for m in re.finditer(r["pattern"],str(p.get("text") or ""),re.I)]
                return {"status":"CORRECTION_REQUIRED" if hits else "CONFORMANT","hits":hits}
        if pid=="runtime://keddeh/quantum-computer":
            import math
            v=[float(x) for x in p.get("vector",[1,0])]
            if len(v)!=2:raise ValueError("two real amplitudes required")
            if op=="normalise_vector":
                n=math.hypot(*v); v=[x/n for x in v]
            elif op=="hadamard_1q": v=[(v[0]+v[1])/math.sqrt(2),(v[0]-v[1])/math.sqrt(2)]
            s["quantum"]["last"]={"operation":op,"vector":v,"model":"DETERMINISTIC_REAL_AMPLITUDE_SUBSET","physical_hardware":False};return s["quantum"]["last"]
        if pid=="runtime://keddeh/quantum-matrix":
            if op=="matrix_put": oid=str(p["id"]);s["matrix"]["objects"][oid]={"id":oid,"kind":str(p.get("kind") or "STATE"),"value":p.get("value")};return s["matrix"]["objects"][oid]
            if op=="matrix_relate": r={"source":str(p["source"]),"predicate":str(p["predicate"]),"target":str(p["target"])};s["matrix"]["relations"].append(r);return r
        if pid=="runtime://keddeh/algebra-cores":
            if op=="distance": a,b=int(p["a"]),int(p["b"]);return {"topological":abs(ACTIVE.index(a)-ACTIVE.index(b)),"scalar":b-a}
            if op=="corridor_add":
                a,b=int(p["a"]),int(p["b"]); total=a+b
                if total==0:return {"kind":"BALANCED","typed_zero":"CANCELLATION","operands":[a,b],"recoverable":True}
                return {"kind":"ACTIVE" if total in ACTIVE else "SYMBOLIC_RESULT","value":total,"active":total in ACTIVE}
        if pid=="runtime://keddeh/identity":
            principals=s["identity"]["principals"]
            if op=="create_principal": principals.setdefault(str(p["id"]),{"scopes":[]});return principals[str(p["id"])]
            if op=="grant_scope": x=principals.setdefault(str(p["id"]),{"scopes":[]});scope=str(p["scope"]); x["scopes"] += [] if scope in x["scopes"] else [scope];return x
            if op=="check_scope": return {"allowed":str(p["scope"]) in principals.get(str(p["id"]),{}).get("scopes",[])}
        if pid=="runtime://keddeh/governance-proof":
            if op=="append_evidence": e={"id":str(p.get("id") or uuid.uuid4()),"subject":str(p["subject"]),"producer":str(p.get("producer") or "enterprise-runtime"),"classification":str(p.get("classification") or "OBSERVED"),"payload_digest":str(p.get("payload_digest") or sha(p.get("payload") or {})),"epoch":p.get("epoch"),"session":p.get("session"),"environment":str(p.get("environment") or "local-companion")};s["evidence"].append(e);return e
            if op=="promote_property":
                ev=[e for e in s["evidence"] if e["id"] in p.get("evidence",[]) and e["subject"]==str(p["subject"])];ok=len(ev)==len(p.get("evidence",[]))>0 and all(e["classification"] in QUALIFIED_EVIDENCE for e in ev);key=f"{p['subject']}#{p['property']}";s["promotions"][key]={"status":"PROMOTED_PROPERTY_SCOPED" if ok else "REJECTED_UNQUALIFIED","evidence":p.get("evidence",[]),"environment":str(p.get("environment") or "local-companion")};return s["promotions"][key]
        if pid=="runtime://k-app/packager" and op=="package_product":
            prod=self.product(str(p["product"]));manifest={"schema":"kex.kapp.v1","product":prod["id"],"name":prod["name"],"capabilities":prod["capabilities"],"routes":prod["routes"],"operations":prod["operations"],"proof_boundary":prod["proof_boundary"]};manifest["integrity"]=sha(manifest);s["kapps"][manifest["integrity"]]=manifest;return manifest
        if pid in {"os://keddeh/k-os","os://keddeh/bos","os://keddeh/hybrid","runtime://keddeh/recovery"}:
            if op=="register_process": pid2=str(p.get("pid") or uuid.uuid4());s["os"]["processes"][pid2]={"pid":pid2,"name":str(p["name"]),"state":str(p.get("state") or "RUNNING")};return s["os"]["processes"][pid2]
            if op=="process_list": return {"processes":list(s["os"]["processes"].values())}
            if op=="checkpoint": name=str(p.get("name") or uuid.uuid4());s["checkpoints"][name]={"name":name,"state":{"os":copy.deepcopy(s["os"]),"continuations":copy.deepcopy(s["continuations"]),"vfs":copy.deepcopy(s["vfs"])} };return {"status":"COMMITTED","name":name}
            if op=="restore_checkpoint": c=s["checkpoints"][str(p["name"])];s["os"]=copy.deepcopy(c["state"]["os"]);s["continuations"]=copy.deepcopy(c["state"]["continuations"]);s["vfs"]=copy.deepcopy(c["state"]["vfs"]);return {"status":"RESTORED","name":c["name"]}
            if op=="service_graph": return {"status":"HOST_ADAPTER_REQUIRES_HTML_BOOT_FABRIC_READBACK"}
        if pid in {"server://keddeh/global-presence","runtime://keddeh/api-bridge"} and op=="route": return {"status":"HOST_ADAPTER_ROUTE_MODEL","host":p.get("host"),"path":p.get("path"),"external_readback":None}
        if pid=="app://kex/computer" and op in {"workspace_status","spawn_workspace"}: return {"status":"HTML_CARRIER_BINDING_REQUIRED","operation":op}
        if pid=="runtime://kex/btc/mainnet/resident-v1":
            from core.stratum_substrate_engine import StratumSubstrateEngine
            engine = StratumSubstrateEngine.get_instance()
            if op in {"btc_status", "status"}:
                telemetry = engine.get_telemetry()
                shm_path = Path("/Users/ak/Desktop/00_LIVE_SYSTEMS/_actual/kex_compute/server_room_telemetry.shm")
                if shm_path.exists():
                    try:
                        from core.advanced_shm_bridge import MemorySemanticBridge
                        cl_shm = MemorySemanticBridge(shm_path)
                        telemetry["cluster_shm"] = cl_shm.get_stats()
                    except Exception:
                        pass
                return {"status": "ACTIVE_SUBSTRATE", "telemetry": telemetry, "live_core_claim": True}
            if op == "btc_route":
                return {"status": "ROUTED", "stratum_target": "solo.ckpool.org:3333", "substrate_engine": "libkex_continuous_stream.dylib"}
            if op == "execute_batch":
                header_prefix = bytes.fromhex(str(p.get("header_prefix_hex") or "00"*76))
                target_int = int(p.get("target_int") or (0x00000000FFFF0000000000000000000000000000000000000000000000000000))
                nonce_count = int(p.get("nonce_count") or 1000000)
                virtual_workers = int(p.get("virtual_workers") or 8)
                found, hashes, dt = engine.execute_batch(header_prefix, target_int, start_nonce=int(p.get("start_nonce") or 0), nonce_count=nonce_count, virtual_workers=virtual_workers)
                job_id = str(p.get("job_id") or "DIRECT_SUBSTRATE_BATCH")
                receipt = engine.record_cycle_receipt(hashes, dt, found is not None, job_id)
                return {"status": "BATCH_COMPLETE", "receipt": receipt, "share_found": found is not None}
            if op == "submit_stats":
                return {"status": "RECORDED", "telemetry": engine.get_telemetry()}
        if op in {"list_packages","deployment_status","process_list","service_graph"}: return {"status":"EMPTY_OR_UNRESOLVED"}
        raise ValueError(f"handler not implemented for {pid}::{op}")

from core.bilateral_auth import HardenedCapabilityEngine

@dataclass
class RuntimeContext:
    store: EnterpriseStore
    token: str | None
    auth: HardenedCapabilityEngine = HardenedCapabilityEngine()

class Handler(BaseHTTPRequestHandler):
    server_version="KEDDEHEnterprise/1.0"
    def log_message(self, fmt, *args): return
    @property
    def ctx(self) -> RuntimeContext: return self.server.ctx  # type: ignore[attr-defined]
    def _send(self, code:int, body:Any, ctype="application/json"):
        raw=body if isinstance(body,(bytes,bytearray)) else (body.encode() if isinstance(body,str) else json.dumps(body,sort_keys=True).encode())
        self.send_response(code);self.send_header("Content-Type",ctype);self.send_header("Content-Length",str(len(raw)));self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff");self.send_header("Access-Control-Allow-Origin","*");self.send_header("Access-Control-Allow-Headers","*");self.send_header("Access-Control-Allow-Methods","GET, POST, OPTIONS");self.end_headers();self.wfile.write(raw)
    def _json_body(self, max_bytes=1_048_576):
        n=int(self.headers.get("Content-Length") or 0)
        if n<0 or n>max_bytes: raise ValueError("request body too large")
        raw=self.rfile.read(n); return json.loads(raw or b"{}")
    def _extract_token(self, body: dict[str, Any]) -> str | None:
        auth_hdr = self.headers.get("Authorization") or ""
        if auth_hdr.startswith("Bearer "):
            return auth_hdr[7:].strip()
        return body.get("capability_token")
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
    def do_GET(self):
        u=urlparse(self.path); q=parse_qs(u.query)
        if u.path=="/": return self._send(200,CARRIER_PATH.read_bytes(),"text/html; charset=utf-8")
        if u.path=="/health": return self._send(200,{"status":"READY","products":len(self.ctx.store.products),"ledger":self.ctx.store.verify_ledger(),"carrier":CARRIER_PATH.name})
        if u.path=="/api/products": return self._send(200,{"products":list(self.ctx.store.products.values())})
        if u.path=="/api/product":
            try:return self._send(200,self.ctx.store.product(q.get("id",[""])[0]))
            except KeyError as e:return self._send(404,{"error":str(e)})
        if u.path=="/api/state": return self._send(200,self.ctx.store.state())
        if u.path=="/api/ledger": return self._send(200,{"verification":self.ctx.store.verify_ledger(),"events":self.ctx.store.ledger(int(q.get("limit",["100"])[0]))})
        if u.path in {"/api/stream", "/api/ledger/stream"}:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            sub_q = self.ctx.store.subscribe()
            try:
                # Send initial connection event
                init_event = f"event: CONNECTED\ndata: {json.dumps({'status': 'STREAM_ACTIVE', 'server_time': utc()})}\n\n".encode("utf-8")
                self.wfile.write(init_event)
                self.wfile.flush()
                
                while True:
                    try:
                        msg = sub_q.get(timeout=15.0)
                        self.wfile.write(msg)
                        self.wfile.flush()
                    except queue.Empty:
                        # Keep-alive heartbeat
                        ping = f"event: HEARTBEAT\ndata: {json.dumps({'time': utc()})}\n\n".encode("utf-8")
                        self.wfile.write(ping)
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                self.ctx.store.unsubscribe(sub_q)
            return
        if u.path=="/api/resolve":
            cid=q.get("id",[""])[0]; st=self.ctx.store.state(); c=st["claims"].get(cid); return self._send(200,{"status":"RESOLVED" if c else "UNRESOLVED","claim":c})
        return self._send(404,{"error":"not_found"})
    def do_POST(self):
        if self.path!="/api/operate": return self._send(404,{"error":"not_found"})
        try:
            body=self._json_body()
            token=self._extract_token(body)
            product=str(body.get("product") or "")
            operation=str(body.get("operation") or "")
            payload=body.get("payload") or {}
            principal=str(body.get("principal") or "operator")

            # Capability Token Verification & Granular Scoping Gate
            if token:
                # 1. Verify token signature, expiry, principal, product, operation, and payload hash
                valid, reason, claims = self.ctx.auth.verify_capability_token(
                    token=token,
                    expected_principal=principal,
                    expected_product=product,
                    expected_operation=operation,
                    expected_payload=payload,
                    consume_nonce=False
                )
                if not valid or not claims:
                    return self._send(403, {"ok": False, "error": f"CAPABILITY_GATING_REJECTED: {reason}"})
                
                # 2. Persist & check nonce in SQLite database (Crash-proof replay resistance)
                jti = claims.get("jti", "")
                exp = claims.get("exp", 0)
                if not self.ctx.store.consume_nonce(jti, exp):
                    return self._send(403, {"ok": False, "error": "REPLAY_DETECTED_PERSISTENT_NONCE"})
            else:
                # Loopback fallback for local unauthenticated dev
                is_loopback = self.client_address[0] in {"127.0.0.1", "::1"}
                if self.ctx.token and not is_loopback:
                    return self._send(403, {"ok": False, "error": "MUTATION_NOT_AUTHORIZED_MISSING_CAPABILITY_TOKEN"})

            result=self.ctx.store.operate(product, operation, payload)
            return self._send(200, result)
        except (ValueError,KeyError,AssertionError,json.JSONDecodeError) as e:return self._send(400,{"ok":False,"error":str(e)})
        except Exception as e:return self._send(500,{"ok":False,"error":type(e).__name__})

def serve(host:str,port:int,state_path:Path,token:str|None=None):
    if host not in {"127.0.0.1","::1","localhost"} and not token: raise SystemExit("Refusing non-loopback bind without KEDDEH_ENTERPRISE_TOKEN")
    store=EnterpriseStore(state_path)
    ThreadingHTTPServer.allow_reuse_address = True
    server=ThreadingHTTPServer((host,port),Handler);server.ctx=RuntimeContext(store,token)  # type: ignore[attr-defined]
    try: server.serve_forever()
    finally: server.server_close();store.close()

def selftest(state_path:Path):
    if state_path.exists(): state_path.unlink()
    st=EnterpriseStore(state_path)
    checks={}
    checks["product_count_28"]=len(st.products)==28
    checks["unique_product_ids"]=len(st.products)==len(set(st.products))
    r=st.operate("system://braink","start_continuation",{"id":"t","coordinate":"il-llm://braink/enterprise"});checks["continuation"]=r["result"]["logical_time"]==1
    st.operate("volume://kex/ssd","write_file",{"path":"/x","content":"y"});checks["vfs_roundtrip"]=st.operate("volume://kex/ssd","read_file",{"path":"/x"})["result"]["content"]=="y"
    st.operate("app://braink/workbook","write_cell",{"sheet":"Sheet1","cell":"A1","value":"1A"});checks["workbook"]=st.operate("app://braink/workbook","read_cell",{"sheet":"Sheet1","cell":"A1"})["result"]["value"]=="1A"
    checks["typed_zero"]=st.operate("runtime://keddeh/algebra-cores","corridor_add",{"a":-2,"b":2})["result"]["kind"]=="BALANCED"
    checks["distance_separation"]=st.operate("runtime://keddeh/algebra-cores","distance",{"a":-2,"b":1})["result"]=={"topological":1,"scalar":3}
    st.operate("app://casepath","create_matter",{"id":"m"});checks["casepath"]=st.operate("app://casepath","assess_gaps",{"id":"m"})["result"]["gaps"]!=[]
    st.operate("app://claimpath","create_claim",{"id":"c"});checks["claimpath"]=st.operate("app://claimpath","add_evidence",{"id":"c","source":"file://e"})["result"]["source"]=="file://e"
    st.operate("runtime://keddeh/governance-proof","append_evidence",{"id":"e1","subject":"claim1","classification":"TESTED","payload":{"pass":True}});checks["promotion"]=st.operate("runtime://keddeh/governance-proof","promote_property",{"subject":"claim1","property":"tested","evidence":["e1"]})["result"]["status"]=="PROMOTED_PROPERTY_SCOPED"
    checks["ledger_pass"]=st.verify_ledger()["status"]=="PASS"
    before=st.state();st.close();st=EnterpriseStore(state_path);checks["restart_rehydrate"]=st.state()["generation"]==before["generation"] and "/x" in st.state()["vfs"]
    checks["ledger_restart_pass"]=st.verify_ledger()["status"]=="PASS";st.close()
    return {"status":"PASS" if all(checks.values()) else "FAIL","passed":sum(checks.values()),"total":len(checks),"checks":checks}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--host",default="127.0.0.1");ap.add_argument("--port",type=int,default=8871);ap.add_argument("--state",type=Path,default=ROOT/"state"/"enterprise.sqlite3");ap.add_argument("--selftest",action="store_true")
    args=ap.parse_args()
    if args.selftest: print(json.dumps(selftest(args.state),indent=2));return
    serve(args.host,args.port,args.state,os.environ.get("KEDDEH_ENTERPRISE_TOKEN"))
if __name__=="__main__": main()
