> KEDDEH SYSTEMS · RESEARCH & ENGINEERING
> Author: Codex-assisted engineering draft for Keddeh Systems · Contributions: native source integration, implementation and tests
> Publisher / rights holder: Keddeh Systems · Licence: reserved rights (upstream rights retained)
> Classification: public source documentation · Version: 0.1.0 · Status: engineering draft, no independent model assessment
> Revision date: 2026-10-11 · Evidence: SOURCE-PROVENANCE.json and evidence/

# Deployment and rollback

## Source release

Use the existing `Keddeh1/BRAINK-AGENT` repository. Initial population is authorized. Inspect remote refs immediately before publication; do not force-push or overwrite concurrent changes. The initial commit is direct only while the repository remains empty; otherwise preserve the new head and use a draft PR for reconciliation.

Only selected public native files and newly authored integration are eligible. The mounted private deployment queue and supplied private Site bundles are excluded. Runtime databases, credentials, account allowlists and raw owner readbacks must not enter Git history.

## Production package gate

Run native CI, stage reviewed source, build `dist/BRAINK_AGENT.tar`, then extract **that exact archive** into a fresh directory. Verify every source digest and execute native family birth, worker production and observer readback from the extracted tree. A working checkout does not prove its production bundle is complete. Keep package digest, source commit and test record distinct.

## Keddeh native host

`contracts/native-ci.json` is the CI invocation contract for an existing admitted Keddeh execution host. No GitHub Actions or Railway dependency is added. Local execution of the native CI command is evidence of local tests, not proof that a cloud CI host has accepted the workload.

Install the verified source tree on the selected existing Linux host with Python 3.12+ and Node.js 20+. Run the CLI/server under a dedicated owner-controlled service account with a private persistent state path. Supply existing credentials through protected files; do not publish their values. Bind the loopback control runtime behind an already approved identity/TLS gateway only after that boundary is tested.

This task does not create a host, paid resource, new credential, pending migration or widened grant. Hosted admission/deployment remains a separate explicit native boundary. The existing Keddeh Site is owned by a concurrent deployment task and is not modified here.

## Initial resident deployment — 2026-10-11

The initial source commit `b92535b3b5b118d18fb74ed270fe36ff5d1f5996` was deployed under the existing Keddeh Docker supervisor as `keddeh-braink-agent`. It uses the existing admitted runtime image `sha256:4474575af321d192b019de6675e97312a9bceeb30a95c6e4914cfa2b3ec4bdf9` (Python 3.12.15, Node 24.21.0). All 21 integration/security/MCP tests passed inside that image before launch.

The HTML control runtime is accessible on **the host's loopback** at `http://127.0.0.1:28787`. This is not an internet URL or a new Site deployment. The process uses read-only release source, private persistent state, the existing SERVERSPACE owner credential mounted read-only, `unless-stopped` restart policy, no added Linux capabilities, no privilege escalation, 512 MiB memory, one CPU and 64 process IDs. It has no Docker socket mount. Native cloud credentials are not inferred from the local owner credential.

The exact source archive was checked against all 80 release file hashes before launch. Eleven host checks exercised anonymous/Origin rejection, native identity birth, VFS memory, bounded worker execution, distinct observer readback, container restart and preserved identity/memory/verification records. See [host verification](../evidence/host-verification.json). Those initial checks refer to the initial code commit. The current source release is recorded below.

Owner operators can inspect `docker inspect keddeh-braink-agent`, read status through the existing protected loopback API, and use `docker stop --time 10 keddeh-braink-agent` to stop this manager without touching another family. Restart with `docker start keddeh-braink-agent`. State resides outside the release tree and survives container restart. The owner-private deployment record under `/workspace/braink-setup/braink-agent/deployment.json` binds the exact release and image; it contains no credential value.

A remotely accessible owner control interface requires an existing approved identity/TLS gateway route whose Host, Origin and credential boundaries are tested. No such route has been configured here. The current fixed Host/Origin checks deliberately reject a forwarded foreign host. Standalone cloud MCP transport separately needs an existing authorized native binding; a successful managed-connector call cannot supply or establish that binding.

## Current manager release — 2026-10-13

The resident manager now runs source commit `4df3e437c6a4be67b7de6d05bac901b1a7336c8b`, source archive SHA-256 `63f362cc37744d3bf3c857bece182916159ba4a9ccbe22ccb009361fb821cc01`, with all 104 source-file hashes checked. The update retained the existing state and credential, and mounts a private fixed SERVERSPACE status binding. The existing memory readback survived the update. The predecessor container is stopped and retained for rollback; a private state backup was made before switching releases.

The deployed owner interface runs real service-health, source-reconciliation and workload-checkpoint tasks with separate native delivery/analyst families, leased workers, immutable outputs and separate integrity observation. The live service task authenticated to the actual SERVERSPACE status endpoint. A controlled interruption after output write recovered after the actual 20-second lease expiry, preserved one artifact binding, rejected the stale lease and returned idempotent readback. Full host population and restart results are recorded in [host upgrade readback](../evidence/host-upgrade.json) and [live recovery](../evidence/live-recovery.json).

The owner-private T45 technical directive is retained as a workload checkpoint with transfer status PREPARED. Its full package bytes remain unavailable. No external chat delivery, acknowledgement or integration of those unavailable modules is inferred from this local checkpoint.

## Rollback

Record the previous source commit, package SHA-256 and state backup before switching versions. Stop admission and workers, preserve current state as evidence, select the prior verified package and use its compatible state backup in a new directory. Read back source and durable records before restoring service. Record rollback as a new operation; do not rewrite source history or relabel an old assessment as current. Schema-changing rollback requires a separately tested migration path.


---
© 2026 Keddeh Systems. All rights reserved. Source custody, actor execution, durable readback and independent assessment are separate records.
