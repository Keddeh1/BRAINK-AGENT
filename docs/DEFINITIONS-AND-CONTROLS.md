> KEDDEH SYSTEMS · RESEARCH & ENGINEERING
> Author: Codex-assisted engineering draft for Keddeh Systems · Contributions: native source integration, implementation and tests
> Publisher / rights holder: Keddeh Systems · Licence: reserved rights (upstream rights retained)
> Classification: public source documentation · Version: 0.1.0 · Status: engineering draft, no independent model assessment
> Revision date: 2026-10-11 · Evidence: SOURCE-PROVENANCE.json and evidence/

# Definitions, normalization and controls

| Term | Operational definition |
|---|---|
| BRAINK | Native root controller `system://braink`; owns continuity and bounded coordination |
| BRAINK_AGENT | This repository and services-manager integration; not a replacement root identity |
| IL-LLM | Native memory identity `volume://braink/il-llm/sovereign-v1`; its name does not prove an inference binding |
| KEX / VFS | Existing execution and content/binding systems; exact product identities are preserved |
| KEX DNA | Existing estate concept; this manager supplies no replacement DNA engine |
| ToT | Pinned native safety evaluation and receipts; does not authenticate a caller by itself |
| Template | Immutable definition identified by content digest |
| Birth | Native family transaction plus explicit team instantiation and retained binding record |
| Lease | Expiring claim with token and epoch; stale writers are fenced |
| Actor execution | A process/tool returned an observed result |
| Durable readback | Retained bytes or records were fetched and checked after execution |
| Independent assessment | Separate assessed work with an actual report identity; never inferred from actor output |
| Sector | Sourced problem/undertaking record; not a foundry or a credential tenant |
| Expertise | Version-bound applied qualification for a precise capability and scope |

## Naming and normalization

Repository: `BRAINK-AGENT`; product display: `BRAINK_AGENT`; Python module: `braink_agent`. Native URIs and team UUIDs are never normalized into a new project identity.

Caller IDs use `[A-Za-z0-9_-]`, 1–100 characters with derived custody-key limits checked before mutation. Sector IDs are at most 60 characters. Capability identifiers use exact, nonempty, case-sensitive string matching. A typed list is required; a string cannot masquerade as a capability collection. No fuzzy, substring or empty capability admission occurs in the integration adapter.

Structured request identity uses canonical sorted JSON. Changed content under the same immutable request identity is rejected. Native VFS preserves its own canonicalization and continuation/version semantics unchanged. UTC timestamps are evidence metadata, not identity substitutes. Missing evidence is `null` or an explicit blocked state; zero is not used as an absent address/state.

## Control table

| ID | Control | Enforcement | Evidence |
|---|---|---|---|
| C01 | Owner-only mutation | Loopback server, exact Host/Origin, existing bearer binding | HTTP negative tests |
| C02 | Public read-only view | Static contract projection; private overview requires owner | Public route tests |
| C03 | Native source custody | SHA-256 pinned file list | `verify-source.py` |
| C04 | Exact capability admission | `ExactCapabilityStore` | Empty/string/substring regression |
| C05 | Durable identity and purpose | Native family transaction + immutable birth record | Restart/conflict tests |
| C06 | Bounded workers | Native CPU/memory/file bounds, wall timeout, queue bound | Native canary |
| C07 | Stale writer exclusion | Native token, epoch and expiry fencing | Expiry/reclaim tests |
| C08 | Crash recovery | Continuation-based VFS retry/readback | Crash-after-write test |
| C09 | No uncertain replay | Durable dispatch intent + command-status reconciliation | Transport failure test |
| C10 | Separate evidence states | Actor, readback and assessment fields | Independent review |
| C11 | Source-only publication | Explicit Git staging, package checks, provenance scan | Package evidence |
| C12 | Distinct classification axes | Source references retained separately | Sector contract |

Bounds: 16 KiB worker input, 64 KiB artifact, 64 jobs/team including terminal history, three attempts, 0.05–30 second lease, 12 second parent worker timeout. Manager undertakings admit at most 4 KiB of complete request JSON and eight simulated qubits so amplified result custody remains bounded. Larger native engine capacity is not automatically admitted through this manager.


---
© 2026 Keddeh Systems. All rights reserved. Source custody, actor execution, durable readback and independent assessment are separate records.
