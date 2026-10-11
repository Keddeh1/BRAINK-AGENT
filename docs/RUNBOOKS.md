> KEDDEH SYSTEMS · RESEARCH & ENGINEERING
> Author: Codex-assisted engineering draft for Keddeh Systems · Contributions: native source integration, implementation and tests
> Publisher / rights holder: Keddeh Systems · Licence: reserved rights (upstream rights retained)
> Classification: public source documentation · Version: 0.1.0 · Status: engineering draft, no independent model assessment
> Revision date: 2026-10-11 · Evidence: SOURCE-PROVENANCE.json and evidence/

# Operations and recovery runbooks

## Start and inspect

Run `python3 -m braink_agent --state /absolute/private/state serve`. Without an existing owner token file, only public views are accessible over HTTP. The local CLI's `status` command is available to the trusted operating-system owner. Bind existing UI and native cloud credentials separately, outside the checkout.

Inspect source hashes with `make check`, runtime state with `status`, and retained records through `recall`. Do not treat a populated registry as proof that every service has executed.

## Execute a team job

Birth a family with a stable key and explicit purpose. Copy its returned native team ID. Enqueue a stable job key for `production` or `specialist`. Run one worker. The job first becomes `PRODUCED`. Invoke `verify` using the job ID to launch the separate observer; only actual artifact/receipt agreement advances it to `VERIFIED`.

Native IDs come from results. Never invent or transplant IDs between teams. A changed payload under the same job key fails. There are at most 64 retained jobs per team including terminal history; create an explicitly versioned new undertaking or archive under a separately reviewed retention plan when full.

## Worker failure / lease expiry

A failed adapter consumes one of three attempts. A process dying after claim leaves the lease until expiry. The next native claim recovers expired work or makes the third failure terminal. Do not manually reset the epoch, token, attempt count or SQLite rows. A crash after artifact commit reconciles through the same native continuation ID; it does not append a duplicate binding.

If an artifact is corrupted, verification remains unsuccessful. Preserve evidence, stop new writes to affected state, restore a verified backup to a separate directory and compare native history before switching. Never rewrite a failure as success.

## Remote timeout

Find the stable command ID in `manager.sqlite3` through `remote_status`/the SDK. Call `cloud_reconcile`, which asks the existing native `command_status`. Do not re-dispatch the command to discover whether it ran. Missing readback leaves uncertainty unresolved. A separate result observation is not an independent assessment receipt.

## Interrupted birth or sector admission

Repeat the identical birth or source-attributed sector record. Native family retry reads the committed result; team identity stays content-bound; VFS continuation rejects changed content. Partial multi-store custody can then complete. Use a new explicit revision identity for changed purpose/source; migration is not implicit.

## Backup / restore

Stop the server and workers before a filesystem backup so all manager, family, queue and VFS stores represent one quiescent boundary. Copy the complete state directory, including SQLite WAL/sidecars and object trees, to protected owner storage. Restore into a new private directory, verify source and receipt chains, run readback, then explicitly switch the service state path. No automated backup provider or retention promise is configured by this repository.


---
© 2026 Keddeh Systems. All rights reserved. Source custody, actor execution, durable readback and independent assessment are separate records.
