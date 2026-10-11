import { canonical, rejectStandaloneZero, sha256, ZERO_ASSESSMENT_RULE } from './common.mjs';

export class ToTSafetyKernel {
  #receipts = [];

  evaluate(input) {
    const action = String(input?.action ?? '').trim();
    const target = String(input?.target ?? '').trim();
    const authority = String(input?.authority ?? '').trim();
    const requestedState = input?.requestedState == null ? null : String(input.requestedState);
    const mutating = input?.mutating === true;
    const evidence = Array.isArray(input?.evidence) ? input.evidence.map(String).filter(Boolean) : [];
    const invariants = Array.isArray(input?.invariants) ? input.invariants.map(String) : [];
    const reasons = [];

    if (!action) reasons.push('ACTION_REQUIRED');
    if (!target) reasons.push('TARGET_REQUIRED');
    else rejectStandaloneZero(target, 'ADDRESS');
    if (!authority) reasons.push('AUTHORITY_REQUIRED');
    if (requestedState !== null) rejectStandaloneZero(requestedState, 'STATE');
    if (mutating && evidence.length === 0) reasons.push('MUTATION_EVIDENCE_REQUIRED');
    if (invariants.includes('CAPABILITY_ESCALATION')) reasons.push('CAPABILITY_ESCALATION_REJECTED');

    const decision = reasons.length === 0 ? 'ALLOW' : 'DENY';
    const previous = this.#receipts.at(-1)?.digest ?? null;
    const body = {
      schema: 'kex.tot.safety.receipt.v1',
      action,
      target,
      authority,
      mutating,
      requestedState,
      assessment: input?.assessment ?? null,
      evidence,
      invariants,
      decision,
      reasons,
      zeroAssessmentRule: ZERO_ASSESSMENT_RULE,
      previousDigest: previous,
    };
    const receipt = { ...body, digest: sha256(canonical(body)) };
    this.#receipts.push(receipt);
    return receipt;
  }

  receipts() { return this.#receipts.map(x => ({ ...x })); }
}
