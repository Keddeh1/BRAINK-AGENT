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
