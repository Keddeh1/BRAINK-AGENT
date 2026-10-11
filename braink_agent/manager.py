"""Owner-local orchestration; native runtime owns identities, leases and VFS."""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import asdict
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
from typing import Any
from .native import ROOT, NATIVE, Runtime, ROLES, ScopedVFSStore, ArtifactWrite, canonical_json
from .adapters import KeddehService, Dispatch
from .resident import exact_store_class

def bounded_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
        raise ValueError("INVALID_ID")
    return value

def bounded_json(value: Any, limit: int = 65536) -> bytes:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if len(data) > limit:
        raise ValueError("BYTE_BOUND")
    return data

spec = importlib.util.spec_from_file_location("braink_family", ROOT / "runtime/braink_family.py")
family = importlib.util.module_from_spec(spec)
spec.loader.exec_module(family)

class Manager:
    def __init__(self, root: Path):
        self.root = Path(root).absolute()
        if self.root.resolve() != self.root:
            raise ValueError("STATE_SYMLINK_REJECTED")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.runtime = Runtime(self.root / "teams")
        self.vfs = ScopedVFSStore(self.root, self.root / "memory")
        with self.database() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sectors(id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS remote_requests(id TEXT PRIMARY KEY, request TEXT NOT NULL,
                  state TEXT NOT NULL, actor TEXT, readback TEXT, assessment TEXT);
            """)

    @contextmanager
    def database(self):
        from storage import sqlite_paths
        path = self.root / "manager.sqlite3"
        sqlite_paths(self.root, path)
        db = sqlite3.connect(path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def owner_lock(self):
        # Serializes complete multi-store admission/reconciliation across processes.
        path = self.root / "owner.lock"
        if path.is_symlink():
            raise ValueError("LOCK_SYMLINK_REJECTED")
        with path.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def remember(self, key: str, value: dict) -> dict:
        bounded_id(key)
        data = bounded_json(value)
        record, receipt = self.vfs.write(ArtifactWrite("/records/" + key + ".json", data,
            "BRAINK_AGENT", media_type="application/json", continuation_id=key, expected_version=0))
        actual = self.vfs.read_content(record.digest)
        if actual != data or not self.vfs.verify_receipt_chain()["verified"]:
            raise RuntimeError("READBACK_REJECTED")
        return {"digest": record.digest, "receipt": receipt.receipt_id,
                "state": "DURABLE_READBACK", "assessmentReceipt": None}

    def control(self, action: str, target: str, evidence: list[str]) -> dict:
        packet = {"action": action, "target": target, "authority": "system://braink",
                  "mutating": True, "evidence": evidence,
                  "invariants": ["OWNER_AUTHORITY_BOUND", "NO_MODEL_CLAIM_WITHOUT_BINDING"]}
        result = subprocess.run(["node", str(ROOT / "scripts/tot-evaluate.mjs")],
            input=bounded_json(packet), capture_output=True, timeout=5, check=True)
        receipt = json.loads(result.stdout)
        if receipt.get("decision") != "ALLOW":
            raise ValueError("TOT_DENIED")
        self.remember("tot-" + receipt["digest"], receipt)
        return receipt

    def recall(self, key: str) -> dict:
        bounded_id(key)
        record = self.vfs.resolve_path("/records/" + key + ".json")
        if record is None:
            raise KeyError(key)
        return json.loads(self.vfs.read_content(record.digest))

    def birth(self, key: str, purpose: str) -> dict:
        bounded_id(key)
        bounded_id("birth-" + key)
        if not isinstance(purpose, str) or not 1 <= len(purpose.encode()) <= 4096:
            raise ValueError("PURPOSE_REQUIRED")
        with self.owner_lock():
            self.control("BIRTH_LOCAL_FAMILY", "system://braink/" + key, [purpose])
            from storage import sqlite_paths
            sqlite_paths(self.root, self.root / "family.sqlite3")
            store = exact_store_class(family.resident_module())(self.root / "family.sqlite3")
            try:
                result = family.run_family(store, "braink-agent-" + key, purpose,
                    {"learning_sequence": ["propose", "review", "compare", "validate", "commit_or_reject"],
                     "model_binding": None, "expertise": "UNQUALIFIED_UNTIL_EVIDENCE"})
            finally:
                store.close()
            team = self.runtime.instantiate(key, NATIVE / "templates", set().union(*ROLES.values()))
            packet = {"key": key, "purpose": purpose, "family": result,
                      "team": team, "modelBinding": None, "qualification": "DETERMINISTIC_ADAPTERS_ONLY"}
            custody = self.remember("birth-" + key, packet)
            return {**packet, "custody": custody}

    def enqueue(self, team_id: str, role: str, key: str, text: str) -> dict:
        team = self.runtime.team(team_id)
        if role not in {"production", "specialist"}:
            raise ValueError("EXECUTABLE_ROLE_REQUIRED")
        members = {m["role"]: m["member_id"] for m in team["members"]}
        self.control("ENQUEUE", "team://" + team_id, [key, role])
        return self.runtime.enqueue(team_id, members["manager"], members[role], key, text)

    def undertake(self, key: str, purpose: str, circuit: dict | None, shell: dict | None) -> dict:
        """Compose admitted finite computation, memory, capability and VFS via native code."""
        bounded_id(key)
        bounded_id("undertaking-" + key)
        # Native result embeds its request/continuation and repeats shell identity.
        # Bound the complete request before committing any native state.
        bounded_json({"purpose": purpose, "circuit": circuit, "shell": shell}, 4096)
        if circuit is not None and (not isinstance(circuit, dict) or type(circuit.get("qubits")) is not int or not 1 <= circuit["qubits"] <= 8):
            raise ValueError("MANAGER_CIRCUIT_BOUND_1_TO_8_QUBITS")
        if not isinstance(purpose, str) or not 1 <= len(purpose) <= 4096:
            raise ValueError("PURPOSE_BOUND")
        with self.owner_lock():
            self.control("NATIVE_FAMILY_UNDERTAKING", "system://braink/" + key, [purpose])
            from storage import sqlite_paths
            sqlite_paths(self.root, self.root / "family.sqlite3")
            store = exact_store_class(family.resident_module())(self.root / "family.sqlite3")
            try:
                result = family.run_family(store, "undertaking-" + key, purpose,
                    {"execution": "FINITE_NATIVE_COMPUTATION", "model_binding": None}, circuit=circuit, shell=shell)
            finally:
                store.close()
            custody = self.remember("undertaking-" + key, result)
        return {"actor": result, "custody": custody, "physicalHardware": False, "assessmentReceipt": None}

    def run(self, team_id: str, role: str) -> dict:
        if role not in {"production", "specialist"}:
            raise ValueError("EXECUTABLE_ROLE_REQUIRED")
        team = self.runtime.team(team_id)
        worker = next(m for m in team["members"] if m["role"] == role)
        self.control("EXECUTE_BOUNDED_WORKER", "team://" + team_id, [worker["member_id"]])
        process = subprocess.run([sys.executable, str(NATIVE / "worker.py"),
            str(self.runtime.root), team_id, worker["member_id"]], capture_output=True, timeout=12)
        if process.returncode:
            raise RuntimeError("WORKER_FAILED_RECONCILE_NATIVE_QUEUE")
        return json.loads(process.stdout)

    def verify(self, team_id: str, job_id: str) -> dict:
        team = self.runtime.team(team_id)
        if self.runtime.job(job_id)["team"] != team_id:
            raise ValueError("TEAM_SCOPE_MISMATCH")
        verifier = next(m for m in team["members"] if m["role"] == "verification")
        job = self.runtime.job(job_id)
        if job["state"] == "VERIFIED":
            return json.loads(job["result"])["verification"]
        return self.runtime.verify_job(team_id, verifier["member_id"], job_id)

    def sectors(self) -> list[dict]:
        with self.database() as db:
            return [json.loads(r[0]) for r in db.execute("SELECT body FROM sectors ORDER BY id")]

    def admit_sector(self, record: dict) -> dict:
        """Immutable source-attributed sector; native births preserve distinct scopes.

        Instantiation and custody are resumable by the immutable sector digest.
        Research labels cannot qualify expertise or assign a foundry.
        """
        required = {"id", "title", "bottleneck", "sources", "deliveryPurpose", "analystPurpose", "foundryRefs"}
        if not required <= record.keys():
            raise ValueError("SECTOR_FIELDS_REQUIRED")
        sid = bounded_id(record["id"])
        if len(sid) > 60:
            raise ValueError("SECTOR_ID_BOUND")
        for field in ("title", "bottleneck", "deliveryPurpose", "analystPurpose"):
            if not isinstance(record[field], str) or not 1 <= len(record[field].encode()) <= 4096:
                raise ValueError("SECTOR_TEXT_BOUND")
        if not isinstance(record["sources"], list) or not 1 <= len(record["sources"]) <= 32:
            raise ValueError("ATTRIBUTED_SOURCES_REQUIRED")
        for source in record["sources"]:
            if not isinstance(source, dict) or not all(isinstance(source.get(k), str) and source[k]
                    for k in ("url", "title", "claim", "accessed")) or not source["url"].startswith("https://"):
                raise ValueError("SOURCE_ATTRIBUTION_REQUIRED")
        if not isinstance(record["foundryRefs"], list) or any(not isinstance(x, str) for x in record["foundryRefs"]):
            raise ValueError("FOUNDRY_REFERENCES_REQUIRED")
        # No invented foundry mapping: supplied references remain unadmitted claims.
        data = bounded_json(record)
        digest = hashlib.sha256(data).hexdigest()
        with self.database() as db:
            prior = db.execute("SELECT body FROM sectors WHERE id=?", (sid,)).fetchone()
        if prior:
            old = json.loads(prior[0])
            if old["sourceDigest"] != digest:
                raise ValueError("SECTOR_ID_CONFLICT")
            return old
        delivery = self.birth("sector-" + sid + "-delivery", record["deliveryPurpose"])
        analyst = self.birth("sector-" + sid + "-analyst", record["analystPurpose"])
        result = {"record": record, "sourceDigest": digest,
                  "deliveryTeam": delivery["team"]["team_instance_id"],
                  "analystTeam": analyst["team"]["team_instance_id"],
                  "expertise": "REQUIRES_APPLIED_QUALIFICATION", "assessmentReceipt": None,
                  "foundryMapping": "UNADMITTED_REFERENCES", "marketOutcome": "NOT_DEMONSTRATED"}
        self.remember("sector-" + sid, result)
        with self.database() as db:
            db.execute("INSERT OR IGNORE INTO sectors VALUES(?,?)", (sid, json.dumps(result, sort_keys=True)))
            actual = json.loads(db.execute("SELECT body FROM sectors WHERE id=?", (sid,)).fetchone()[0])
        if actual != result:
            raise ValueError("SECTOR_CONCURRENT_CONFLICT")
        return result

    def dispatch(self, service: KeddehService, request: Dispatch) -> dict:
        bounded_id(request.command_id)
        body = bounded_json(asdict(request)).decode()
        with self.database() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM remote_requests WHERE id=?", (request.command_id,)).fetchone()
            if old:
                db.execute("ROLLBACK")
                if old["request"] != body:
                    raise ValueError("COMMAND_ID_CONFLICT")
                return dict(old)  # Never re-dispatch an uncertain request.
            db.execute("INSERT INTO remote_requests VALUES(?,?,'DISPATCH_INTENT',NULL,NULL,NULL)",
                       (request.command_id, body))
            db.execute("COMMIT")
        try:
            actor = service.dispatch(request)
            encoded = bounded_json(actor, 2 * 1024 * 1024).decode()
            state = "ACTOR_RETURNED"
        except Exception:
            encoded, state = None, "UNCERTAIN_RECONCILE_REQUIRED"
        with self.database() as db:
            db.execute("UPDATE remote_requests SET state=?,actor=? WHERE id=?", (state, encoded, request.command_id))
        return self.remote_status(request.command_id)

    def remote_status(self, command_id: str) -> dict:
        bounded_id(command_id)
        with self.database() as db:
            row = db.execute("SELECT * FROM remote_requests WHERE id=?", (command_id,)).fetchone()
        if row is None:
            raise KeyError(command_id)
        return dict(row)

    def reconcile(self, service: KeddehService, command_id: str) -> dict:
        self.remote_status(command_id)
        observation = service.readback(command_id)
        # Keep readback as an observation; never promote arbitrary remote JSON to assessment.
        encoded = bounded_json(observation, 2 * 1024 * 1024).decode()
        with self.database() as db:
            db.execute("UPDATE remote_requests SET readback=? WHERE id=?", (encoded, command_id))
        return self.remote_status(command_id)

    def overview(self) -> dict:
        with self.runtime.db() as db:
            teams = [self.runtime.export_interface(r[0]) for r in db.execute("SELECT id FROM teams ORDER BY id")]
        return {"name": "BRAINK_AGENT", "teams": teams, "sectors": self.sectors(),
                "modelBinding": None, "assessmentReceipt": None,
                "authority": "owner-local; storage scopes are not credential tenancy"}
