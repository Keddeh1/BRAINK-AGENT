> KEDDEH SYSTEMS · RESEARCH & ENGINEERING
> Author: Codex-assisted engineering draft for Keddeh Systems · Contributions: native source integration, implementation and tests
> Publisher / rights holder: Keddeh Systems · Licence: reserved rights (upstream rights retained)
> Classification: public source documentation · Version: 0.1.0 · Status: engineering draft, no independent model assessment
> Revision date: 2026-10-11 · Evidence: SOURCE-PROVENANCE.json and evidence/

# Tests and evidence

`python3 scripts/native-ci.py` is the executable native CI entrypoint. It runs pinned source hash verification, JavaScript syntax checking, manager/HTTP/capability tests, the original ten native family tests and the original native team canary. Each subprocess has a 120-second CI bound. The worker itself has tighter native limits.

The manager tests exercise immutable retry/conflict rejection, restart persistence, concurrent birth identity, native process execution, independent observer PID, lease expiry/fencing, crash after VFS write, corrupted-object rejection, sector team separation, a composed circuit/shell workload and uncertain cloud mutation reconciliation without replay. HTTP tests reject anonymous mutation, wrong credentials, foreign Origin, hostile Host and traversal. Capability tests reject empty, substring and malformed collection routing.

The original family tests verify rollback, concurrent same-request commit, isolated family context and process death. The native canary verifies bounded role permissions, attempts, crash recovery, artifact integrity and source contracts. Failure injection is expected evidence, not an operational incident.

`evidence/local/ci.json` holds private raw test output and is ignored by Git. Reviewed public summaries are separate. `evidence/independent-review.md` contains reviewer-authored findings and checks; this is independent engineering review, not a qualified different-model assessment receipt.

Live service results are in `evidence/live-boundary.json`: authenticated registry/status, connection actor result and later durable status readback. The live managed connector result does not establish that the repository's standalone bearer transport has been exercised against production. That requires an existing approved credential binding.

Publication, source custody, package execution, cloud deployment and assessment are individually recorded. No single PASS field promotes all of them.


## Operational release validation

The final native CI passed 30 integration/security/MCP/workflow/research tests, 10 original family tests and 60 original team canary assertions. The full research test creates 93 actual sector records and 186 distinct native families, then reads every scoped brief after reopening the manager and verifies repeated import creates no duplicates. Browser validation covers 13 controls and privacy/layout checks, including real source/checkpoint task execution in synthetic owner state.

Independent review reproduced and closed operational observer compatibility, interrupted role identity, stale analyst recommendations, observer working-directory and expanded sector-custody bounds. The reviewer performed concurrent advancement, actual lease-expiry recovery, stateful privacy and targeted sector-recovery checks. The final host checks are separately scoped in their readbacks; actor-run restart/fault tests are not relabelled reviewer repetitions.

---
© 2026 Keddeh Systems. All rights reserved. Source custody, actor execution, durable readback and independent assessment are separate records.
