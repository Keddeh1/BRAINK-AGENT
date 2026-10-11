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

## Rollback

Record the previous source commit, package SHA-256 and state backup before switching versions. Stop admission and workers, preserve current state as evidence, select the prior verified package and use its compatible state backup in a new directory. Read back source and durable records before restoring service. Record rollback as a new operation; do not rewrite source history or relabel an old assessment as current. Schema-changing rollback requires a separately tested migration path.


---
© 2026 Keddeh Systems. All rights reserved. Source custody, actor execution, durable readback and independent assessment are separate records.
