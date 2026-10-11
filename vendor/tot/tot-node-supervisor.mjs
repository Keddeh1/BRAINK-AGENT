import { ToTSafetyKernel } from './tot-safety-kernel.mjs';
import { ZERO_ASSESSMENT_RULE } from './common.mjs';

export class ToTNode {
  #kernel;
  #id;
  #targetUri;
  #authority;
  #nodeType;
  #state;
  #uptimeStart;
  #selfHealCount = 0;
  #lastReceiptDigest = null;
  #lastError = null;
  #metadata = {};

  constructor(kernel, options = {}) {
    if (!kernel || !(kernel instanceof ToTSafetyKernel)) {
      throw new Error('TOT_SAFETY_KERNEL_REQUIRED_FOR_NODE');
    }
    this.#kernel = kernel;
    this.#id = String(options.id || '').trim();
    this.#targetUri = String(options.targetUri || '').trim();
    this.#authority = String(options.authority || 'tot://system/supervisor').trim();
    this.#nodeType = String(options.nodeType || 'GENERIC_SERVER_NODE').trim();
    this.#state = 'INITIALIZING';
    this.#uptimeStart = Date.now();
    this.#metadata = options.metadata || {};

    if (!this.#id) throw new Error('NODE_ID_REQUIRED');
    if (!this.#targetUri) throw new Error('TARGET_URI_REQUIRED');

    // Evaluate node instantiation under ToT
    const receipt = this.#kernel.evaluate({
      action: 'BOOT_NODE',
      target: this.#targetUri,
      authority: this.#authority,
      requestedState: 'BOUND',
      mutating: true,
      evidence: [`node_id:${this.#id}`, `node_type:${this.#nodeType}`, `init_timestamp:${this.#uptimeStart}`],
      invariants: ['CONTINUOUS_UPTIME_MANDATE', ZERO_ASSESSMENT_RULE]
    });

    if (receipt.decision === 'ALLOW') {
      this.#state = 'BOUND';
      this.#lastReceiptDigest = receipt.digest;
    } else {
      this.#state = 'DENIED';
      this.#lastError = receipt.reasons.join(',');
    }
  }

  get id() { return this.#id; }
  get targetUri() { return this.#targetUri; }
  get authority() { return this.#authority; }
  get nodeType() { return this.#nodeType; }
  get state() { return this.#state; }
  get selfHealCount() { return this.#selfHealCount; }
  get lastReceiptDigest() { return this.#lastReceiptDigest; }
  get uptimeSeconds() { return Math.floor((Date.now() - this.#uptimeStart) / 1000); }
  get lastError() { return this.#lastError; }
  get metadata() { return { ...this.#metadata }; }

  setMetadata(key, val) {
    this.#metadata[key] = val;
  }

  transition(action, requestedState, mutating = false, evidence = [], invariants = []) {
    const receipt = this.#kernel.evaluate({
      action: String(action),
      target: this.#targetUri,
      authority: this.#authority,
      requestedState: requestedState != null ? String(requestedState) : null,
      mutating: Boolean(mutating),
      evidence: Array.isArray(evidence) ? evidence : [String(evidence)],
      invariants: Array.isArray(invariants) ? invariants : [String(invariants)]
    });

    this.#lastReceiptDigest = receipt.digest;

    if (receipt.decision === 'ALLOW') {
      if (requestedState != null) {
        this.#state = String(requestedState);
      }
    } else {
      this.#lastError = receipt.reasons.join(',');
    }

    return receipt;
  }

  recordSelfHeal(reason) {
    this.#selfHealCount++;
    return this.transition('SELF_HEAL_REHYDRATION', 'REHYDRATING', true, [
      `heal_reason:${reason}`,
      `heal_iteration:${this.#selfHealCount}`,
      `heal_timestamp:${Date.now()}`
    ], ['CONTINUOUS_UPTIME_MANDATE', ZERO_ASSESSMENT_RULE]);
  }

  recordFault(errMessage) {
    this.#lastError = String(errMessage);
    return this.transition('FAULT_OBSERVED', 'DEGRADED', false, [
      `error_msg:${errMessage.substring(0, 150)}`,
      `observed_at:${Date.now()}`
    ]);
  }

  snapshot() {
    return {
      id: this.#id,
      target_uri: this.#targetUri,
      authority: this.#authority,
      node_type: this.#nodeType,
      state: this.#state,
      uptime_seconds: this.uptimeSeconds,
      self_heal_count: this.#selfHealCount,
      last_receipt_digest: this.#lastReceiptDigest,
      last_error: this.#lastError,
      metadata: this.#metadata
    };
  }
}

export class ToTSupervisorRegistry {
  #kernel;
  #nodes = new Map();
  #watchdogTimer = null;

  constructor(kernel) {
    if (!kernel || !(kernel instanceof ToTSafetyKernel)) {
      throw new Error('TOT_SAFETY_KERNEL_REQUIRED_FOR_REGISTRY');
    }
    this.#kernel = kernel;
  }

  get kernel() { return this.#kernel; }

  registerNode(options = {}) {
    const node = new ToTNode(this.#kernel, options);
    this.#nodes.set(node.id, node);
    return node;
  }

  getNode(id) {
    return this.#nodes.get(id) || null;
  }

  hasNode(id) {
    return this.#nodes.has(id);
  }

  getAllNodes() {
    return Array.from(this.#nodes.values()).map(n => n.snapshot());
  }

  evaluateGlobal(action, target, authority, mutating, evidence, requestedState = null, invariants = []) {
    return this.#kernel.evaluate({
      action,
      target,
      authority,
      mutating,
      evidence,
      requestedState,
      invariants
    });
  }

  startWatchdog(intervalMs = 4000) {
    if (this.#watchdogTimer) clearInterval(this.#watchdogTimer);
    this.#watchdogTimer = setInterval(() => {
      this.auditAllNodes();
    }, intervalMs);
  }

  stopWatchdog() {
    if (this.#watchdogTimer) {
      clearInterval(this.#watchdogTimer);
      this.#watchdogTimer = null;
    }
  }

  auditAllNodes() {
    const results = [];
    for (const [id, node] of this.#nodes.entries()) {
      const snap = node.snapshot();
      // Record periodic audit heartbeat under ToT
      const receipt = node.transition('UPTIME_AUDIT_TICK', null, false, [
        `node_state:${snap.state}`,
        `uptime:${snap.uptime_seconds}`,
        `self_heals:${snap.self_heal_count}`
      ]);
      results.push({ id, status: snap.state, receipt_digest: receipt.digest });
    }
    return results;
  }

  getTelemetry() {
    const all = this.getAllNodes();
    const onlineCount = all.filter(n => n.state === 'BOUND' || n.state === 'ACTIVE' || n.state === 'ONLINE').length;
    const receipts = this.#kernel.receipts();

    return {
      schema: 'kex.tot.architecture.telemetry.v1',
      total_registered_nodes: all.length,
      online_nodes_count: onlineCount,
      all_nodes_up: onlineCount === all.length && all.length > 0,
      total_safety_receipts: receipts.length,
      latest_receipt_digest: receipts.at(-1)?.digest || null,
      zero_assessment_rule: ZERO_ASSESSMENT_RULE,
      nodes: all,
      recent_receipts: receipts.slice(-10)
    };
  }
}
