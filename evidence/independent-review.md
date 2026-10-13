> KEDDEH SYSTEMS · ENGINEERING REVIEW
> Author: independent reviewer agent execution context · Contributions: adversarial probes and package reproduction
> Publisher / rights holder: Keddeh Systems · Licence: reserved rights · Classification: public engineering evidence
> Version: 0.1.0 · Status: independent engineering review, not model assessment · Date: 2026-10-11

# Independent implementation review

Review date: 2026-10-11. Reviewer: separate agent execution context. This is an implementation review, not a different-model assessment, qualified domain assessment, signed approval or production-deployment receipt. Synthetic local state only; no cloud mutations or publication performed by this reviewer.

## Independently executed checks

- `python -m unittest discover -s tests -p 'test_*.py' -v`: 16 tests passed (6.661 seconds).
- `python tests/braink-family.test.py`: 10 tests passed (0.342 seconds).
- `python scripts/verify-source.py`: 37 selected native source files matched declared hashes.
- `node --check web/app.js`: passed.
- Inspected manager, resident correction, adapters, loopback HTTP server, browser control code, native birth transaction, native computation bounds and storage containment.

Hash matching establishes equality with the manifest, not independent verification of publication rights. Source records identify public upstream repositories; private Site source is not part of the inspected implementation. No independent live-cloud or repository-publication verification is claimed here.

## Findings and retest status

### R1 — P2, corrected and independently retested: malformed capability data restores substring routing

Location: `braink_agent/resident.py`, `exact_store_class`.

Reproduction: register a native skill with `capabilities: "non-clinical-reporting"` (a string), create a task requiring `clinical`, then resolve it through `ExactCapabilityStore`. Observed `state: RESOLVED, matches: ["bad"]`. The native registration accepts arbitrary capability container types; `query in s["capabilities"]` becomes substring matching for strings. The nominal list-of-string case is correctly exact, but the malformed case bypasses that guarantee.

Require a validated list of nonempty exact capability identifiers both at admission and when consuming stored/native product data. Reject malformed legacy values rather than interpreting them. Exposure is an owner-local integration/store API boundary, not an unauthenticated remote exploit.

### R2 — P2, corrected and independently retested: family database bypasses owner-root symlink containment

Location: `braink_agent/manager.py`, `birth` and `undertake` family store opening.

Reproduction: initialize an owner root, create `owner/family.sqlite3` as a symlink to an absent sibling `outside.sqlite3`, call `birth("test", "Synthetic containment check")`. Birth succeeded and the external SQLite database was created. Manager SQLite and VFS paths use native `sqlite_paths` checks; the family store did not.

Apply static containment to family SQLite and its journal/WAL/SHM paths before opening. The documented static containment is not a hostile-same-UID race sandbox; this finding concerns an already-present symlink.

### R3 — P2, corrected and independently retested: admitted computation commits but permanently fails custody

Location: `braink_agent/manager.py`, `undertake` and `remember`.

Reproduction: call `undertake("large", "Synthetic bounded circuit", {"schema":"keddeh.quantum.circuit.v1","qubits":13,"gates":[]}, None)` twice. Both attempts raise `ValueError: BYTE_BOUND`; native VFS nevertheless contains one committed family result. Native computation admits up to 16 qubits while generic custody encoding admits only 65,536 bytes. A valid small input produces an output that cannot complete manager custody, including on retry.

Align computation admission and custody output bounds or durably store a bounded receipt/reference with explicit full-result readback. Preserve retry identity and do not label the partial outcome as completed.

## Observed boundaries

Public HTTP routes expose static contracts; owner state requires a configured bearer credential and same-origin checks. The listener is loopback only, Host is restricted and CSP prevents framing. Browser output uses text nodes rather than interpolated HTML. Namespace isolation is not separate credential tenancy.

Remote dispatch records intent before transport, does not replay uncertain IDs, rejects conflicting retries and keeps remote readback separate from assessment. Its observations do not establish independent remote truth, expert qualification or successful deployment.

Sector admission produces different delivery and analyst native team identities and durable source-attributed records. It explicitly leaves expertise unqualified and market outcome undemonstrated. This structure does not itself demonstrate useful expert delivery or analyst findings.

The reviewed native workers and numerical workload are deterministic. They do not imply an LLM binding, quantum hardware or qualified professional expertise. Packaging, final documentation and any later integration changes require a follow-up check.

## Follow-up checks

After the first fixes, all 18 repository unittests passed independently (8.286 seconds). R1 now rejects a string capability container with `EXACT_CAPABILITY_LIST_REQUIRED`. R2 rejects the preexisting family DB symlink before creating an external file. The original R3 circuit input now rejects before creating family state (`MANAGER_CIRCUIT_BOUND_1_TO_8_QUBITS`).

At the intermediate review, R3 remained open for general output amplification: load `runtime/shells/tetrahedron.json`, set `identity` to 30,000 ASCII characters, call `undertake` with that shell and no circuit. This is below the 32 KiB request bound but again commits native family state before `BYTE_BOUND` at custody. Native output contains repeated admitted request and shell metadata.

A related R3 identity bound reproducer uses `birth("x" * 100, "Synthetic identity bound")`: initial ID validation succeeds but the derived `birth-` custody ID exceeds its 100-character limit. Observed `INVALID_ID` after one team was created. Derived identifiers need validation before commits.

### R4 — P2, corrected and independently retested: source package filter misses `.env` files

Independently reproduced in an isolated temporary Git repository containing only a copy of the package script and a synthetic `.env` fixture. After staging both files, `python scripts/package.py` returned zero and `BRAINK_AGENT.tar` contained `BRAINK_AGENT/.env`. `Path('.env').suffix` is empty, so the forbidden suffix set does not reject the intended filename. Environment-specific variants need equivalent protection. No real credential was used or found by this check. Reject sensitive basenames/patterns before archive creation and test with synthetic fixtures.

## Final correction and packaged-runtime review

All four reproduced findings are closed for the reviewed implementation. This does not constitute a guarantee that no other defects exist.

- R3: complete undertaking input is capped at 4,096 encoded bytes and simulated circuits at 8 qubits. The 30,000-character shell identity now raises `BYTE_BOUND` before `family.sqlite3` exists or any team is created. Both 100-character birth and undertaking key reproducers now reject `INVALID_ID` with no family DB and zero teams. Derived custody identifiers are checked before actuation.
- R4: packaging uses a source directory/root allowlist and rejects sensitive path components, environment filenames and database/key file types. Package regression tests reject `.env`, `.env.production`, nested environment variants, keys, local evidence, private directories and traversal.

Independently extracted and executed the actual `dist/BRAINK_AGENT.tar` artifact. Archive SHA-256:

`728ddb01e5f4e8dcd84ef37bbd9e27609c03e2c3e38bf95d32f5281310200508`

All 77 members were regular files with no absolute/traversal paths. Each extracted file matched its package-manifest SHA-256. A separate path inspection found no environment files, credential/private directories, database state, key/token files, Python caches or local runtime evidence.

Executed from the extracted package, outside the checkout:

- Source verification: all 37 pinned native file hashes passed.
- Manager/server/capability/package unittest suite: 20 tests passed in 6.449 seconds.
- Native family suite: 10 tests passed in 0.377 seconds.
- Browser JavaScript syntax check: passed.
- Additional packaged flow: created native family with durable custody, enqueued a synthetic production job, observed `PRODUCED`, verified it with a separate observer process, reopened the manager and observed `VERIFIED`. Repeated birth returned identical committed result. Actor and observer process IDs differed. Independent assessment receipt remained null.

This archive necessarily contains the earlier version of this review report; rebuilding to include this final report changes the archive hash. Any later implementation change requires appropriate revalidation. The report does not independently assert live cloud readiness, GitHub remote readback, public deployment, publication rights, market impact or qualified model/domain expertise.


© 2026 Keddeh Systems. All rights reserved.

## Subsequent local stdio MCP boundary review

Inspected `braink_agent/mcp.py` and its test after the archive review above. No material additional finding in the reviewed scope. The fixed tool allowlist forwards to the same manager boundaries; authority comes from the invoking OS account. It opens no public listener and does not infer cloud credentials or expert qualification. Request lines are capped at 100,000 bytes and tool output at 2 MiB.

Independently ran the focused MCP unittest (one passed) and an actual stdio subprocess: malformed JSON returned a parse error and the process continued; initialize succeeded; initialized notification produced no response; arbitrary shell tool was rejected; native birth succeeded and status read back one team. This module was added after the 77-file archive identified above and is not covered by that archive hash. No deployment claim follows from this local protocol check.

## Subsequent owner-local host deployment review

Independently inspected the running deployment without reading credential values or mutating service state. No material additional issue found in this scope. All 80 release files matched Git commit `b92535b3b5b118d18fb74ed270fe36ff5d1f5996` byte-for-byte; the running container used image `sha256:4474575af321d192b019de6675e97312a9bceeb30a95c6e4914cfa2b3ec4bdf9`. Source verification executed inside that container passed all 37 pinned native hashes.

Observed controls: listener only at `127.0.0.1:28787`; non-root UID/GID; read-only root filesystem, source and existing owner credential mounts; private writable state directory mode 0700; all capabilities dropped; no-new-privileges; no privileged mode or Docker socket mount. Host networking is enabled, so this is not an isolated network sandbox. Health returned 200 with cloud `NOT_PROBED`; anonymous owner access returned 401; foreign Host returned 421. No public ingress or cloud credential binding is established by these checks.

Read-only SQLite integrity checks passed for manager, family, memory and queue databases. Persisted state contained one team, one `VERIFIED` job and five memory artifacts. The saved result had distinct actor/observer process IDs, matching digests and successful content observation. Admitted sector count was zero; research rows must not be reported as imported. Reviewed `host-verification.json`, which records 11 host checks and persistence after container restart; this reviewer independently observed the resulting stored state but did not repeat the restart or those mutations. No qualified independent-model assessment is asserted.

## Operational workflow review — implementation in progress

Inspected the initial operational templates, host adapter, workflow coordinator/worker and manager/server integration. No cloud call or persistent host mutation was performed. Three reproducible findings were sent to the implementer:

- **R5, P1, open:** a synthetic durable-checkpoint workflow produces its delivery artifact but inherited `verify_job` launches the legacy observer, which rejects new operational adapter IDs with `unqualified observation`. `advance` raises; workflow remains `DELIVERY_RUNNING` with job `PRODUCED`. The unchanged observer only knows uppercase/word-count semantics. New outputs need an explicitly scoped operational observer; native integrity observation must remain distinct from analyst semantic work.
- **R6, P2, open:** birth with the same key/purpose first as `delivery`, then as `analyst`, raises a custody `BindingConflict` but leaves two teams. Operational role is absent from the immutable family request and conflict is detected after creating the second team. Validate the immutable birth responsibility before team mutation.
- **R7, P2, open:** the service-health analyst independently observes degraded health after the actor observed healthy health, but copies the actor's next action. A synthetic injected observation reproduced `ACTION_REQUIRED` alongside `No recovery action indicated by this observation.` Derive the analyst action from its independent observation.

The host adapter accepts only a configured loopback service path, disables environment proxies and redirects, reads an existing private credential and retains selected response fields rather than the raw response. These observations do not establish credential isolation between local workers. Workflow delivery and analyst use distinct native identities and processes; until observed execution and fixes are reviewed, their existence is not evidence of successful analysis. Neither role has a model binding or qualified expertise.

## Operational workflow corrections and independent recovery checks

**R5–R7 are now corrected and independently retested.** Operational output uses a separate observer that checks native bytes, immutable task/role/request binding and native receipt custody, with an explicit integrity-only scope. Legacy deterministic jobs retain their original observer. The analyst still performs separate source reopening, checkpoint recomputation or health re-observation; integrity verification does not imply independent model assessment.

An additional **R8, P2** was reproduced and corrected during this follow-up: operational observation failed when an SDK caller changed working directory outside the checkout. The observer process now starts with the explicit source root; the same outside-checkout workflow completed on recheck.

The first R6 correction covered committed birth packets only. A synthetic interruption after delivery-team creation but before birth custody allowed an analyst retry to create a second team. The final durable birth-intent correction rejects that role change with `BIRTH_INTENT_CONFLICT`, retains one team, and allows the original delivery request to finish with that same team. R7 recheck produced `ACTION_REQUIRED` and an inspection/recovery recommendation from the analyst's own degraded observation.

Independently executed:

- All 27 current unittests passed in 17.661 seconds, including six operational-workflow tests.
- Four concurrent advances of one task: one completed, three returned nonblocking queued snapshots; final state was complete with exactly one delivery attempt and one analyst attempt.
- Actual wall-clock lease expiry after an injected post-VFS-write process exit: retained recovery state, waited approximately 20 seconds without editing expiry, resumed after restart, completed on delivery attempt two and retained exactly one immutable artifact binding.
- Stateful HTTP privacy check after a synthetic private checkpoint completed: public HTML, public API and health output did not contain the private marker; anonymous owner GET and workflow-read POST both returned 401.
- Synthetic authenticated health boundary and failure classes passed in the workflow suite. This is not a new live SERVERSPACE observation or deployment verification.

No remaining reproduced functional blocker in these reviewed operational modules. These uncommitted changes and checks are separate from the earlier deployed commit, archive hash and live-host review. No newly added research-import module or research rows were assessed by this follow-up.

## Research normalization and targeted sector-admission review

Independently ran the catalogue verifier against manifest SHA-256 `27522df847e298311df2873db7f9fd9b157afd43e89378eea9dadb6443dd6222`: all 13 declared file hashes/lengths passed. Observed 93 unique normalized rows, 186 distinct proposed team identifiers, 94 unique composite source identifiers, exact technical-sector IDs S01–S29 and 18 distinct foundry names. Public-source namespaces `ai_data`, `compute` and `edge_adoption` remain separate from `technical_sector` references. Three distinct specialized-child relationships retain their pending market-validation status. Proposed mappings remain unadopted; no qualification or market outcome is inferred.

Targeted recovery test using one actual normalized row: interrupted before analyst birth, reopened manager, rejected a changed bottleneck with `SECTOR_INTENT_CONFLICT`, then resumed the original record successfully with exactly two teams. Both role-specific research briefs read back their exact record, purpose and role; native receipt chains verified. Repeated admission returned the same record. This reviewer did not repeat the full 93-row/186-birth integration run or revalidate the research's external market claims.

**R9, P2, open:** generic `admit_sector` accepts a 65,500-byte JSON record but its added brief/result envelope exceeds the 65,536-byte custody bound. Synthetic filler added to one real row reproduced `BYTE_BOUND` after two team births, zero completed sectors, and the same failure on retry. Preflight the expanded records or lower the admitted record bound before durable intent/birth. The fixed research catalogue is unaffected by this reproducer: its largest normalized record was 8,317 bytes, with purposes at most 264 bytes and at most two source references per row.

## Final research-bound recheck and pending-source screening

**R9 is corrected and independently retested.** The same 65,500-byte record now rejects `BYTE_BOUND` on both attempts before any birth or sector intent is retained: zero teams, zero sectors, zero birth intents and zero sector intents. The fixed 93-row catalogue continues to normalize successfully under the 32 KiB admission limit.

Reviewed the pending integration, documentation, UI/test and packaging changes. Pinned native `vendor/`, `runtime/` and `SOURCE-PROVENANCE.json` bytes had no changes relative to the public research handoff commit. All 104 tracked/nonignored candidate files passed the package path allowlist, with no symlink or runtime-state path rejection. A targeted content screen found no private-key headers, common GitHub/AWS/Slack credential patterns or private Google document/file links. This limited screen is evidence against accidental inclusion, not a universal secret detector or independent grant of publication rights. The research files remained hash-pinned to the approved public derivative.

No remaining reproduced implementation blocker in the reviewed changes. The implementer reports completion of the full 93-sector/186-team integration test; this reviewer independently exercised targeted admission/recovery cases rather than duplicating that run. Host deployment of these new changes remains a separate verification boundary.

## Upgraded live host and completed population — 2026-10-13

Independently inspected the upgraded host read-only. All 104 release files matched commit `4df3e437c6a4be67b7de6d05bac901b1a7336c8b`; archive SHA-256 matched `63f362cc37744d3bf3c857bece182916159ba4a9ccbe22ccb009361fb821cc01`. The running container retained the admitted image, non-root identity, read-only root/source/credential mounts, dropped capabilities and no-new-privileges. Its new private binding was mode 0600, selected the admitted loopback SERVERSPACE status path and referenced the read-only existing credential mount. No credential values were printed. The listener remained `127.0.0.1:28787`; health returned serving and anonymous owner access returned 401. Host networking remains enabled, not a network-isolation sandbox.

The prior container was stopped and retained for rollback, and the pre-upgrade backup was mode 0700. All 18 pre-upgrade content-addressed objects were still byte-identical in current state. In-container verification passed all 37 native hashes; manager and queue SQLite integrity checks passed.

Independently read retained results for the initial four completed workflows without replaying their actors: authenticated health delivery reported `HEALTHY` with ten healthy nodes and the analyst retained a separate observation; source delivery and analyst each checked 37 files with zero mismatches; both checkpoint workflows retained verified delivery/analyst artifacts. Object digests were recomputed, actor/observer process IDs differed and recorded content observations agreed. Private checkpoint text was not emitted.

After admission finished, independently checked all **93 sector records, 186 distinct actual sector teams and 186 scoped briefs** directly from read-only storage. Every brief object hash, current binding, source digest, role, purpose and original research record matched its sector record. All qualification statuses remained `UNQUALIFIED`; assessment receipts remained null. This establishes actual native admission and retained research memory, not market validation or expert delivery.

Read `live-recovery.json` and independently inspected the resulting live recovery record: complete service-health workflow, verified delivery on attempt two, one binding version, and persisted event sequence `ENQUEUED → CLAIMED → LEASE_EXPIRED → CLAIMED → PRODUCED → VERIFIED`. The implementer performed the live interruption, real lease wait, stale-lease rejection and duplicate advance checks; this reviewer did not repeat those mutations. The final container restart and its resulting readback are a subsequent check, not asserted by this snapshot.

No new material issue found within this review. Private Library handoffs and alternate birth-schema integration remain outside the verified bytes; no Site modification, public ingress, qualified model binding or independent-model assessment is established here.
