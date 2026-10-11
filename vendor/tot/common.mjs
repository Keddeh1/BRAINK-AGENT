import { createHash } from 'node:crypto';

export const ZERO_ASSESSMENT_RULE = 'ZERO_IS_COMPUTED_ASSESSMENT_ONLY_NOT_ADDRESS_OR_STATE';

export function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

export function sha256(value) {
  return createHash('sha256').update(typeof value === 'string' ? value : canonical(value)).digest('hex');
}

export function rejectStandaloneZero(value, field) {
  const token = String(value ?? '').trim().toUpperCase();
  if (token === '0' || token === 'ZERO') throw new Error(`ZERO_NOT_PERMITTED_AS_${field}`);
}

export function assessOpposingPolarities(positive, negative) {
  if (!Number.isFinite(positive) || !Number.isFinite(negative)) throw new Error('FINITE_POLARITIES_REQUIRED');
  return positive + negative;
}
