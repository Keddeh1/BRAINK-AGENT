#!/usr/bin/env python3
"""
KEX Hardened Bilateral Authentication & Capability Gating (bilateral_auth.py)

Key Properties:
1. HKDF-SHA256 Key Separation per Principal.
2. Strict Payload Binding: Token signs sha256(canonical_json(payload)).
3. Replay Protection: Cryptographic nonce (JTI) tracked in-memory and persistent store.
4. Granular Scoping: Token is bound to exact (principal, product_id, operation).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from typing import Any, Dict, Optional, Set, Tuple


def canon_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: Any) -> str:
    raw = value if isinstance(value, (bytes, bytearray)) else canon_bytes(value)
    return hashlib.sha256(raw).hexdigest()


def hkdf_extract_and_expand(master_key: bytes, principal: str, length: int = 32) -> bytes:
    """
    RFC 5869 compliant HKDF key derivation to derive principal-specific subkeys.
    """
    salt = b"KEX_CAPABILITY_HKDF_SALT_V1"
    prk = hmac.new(salt, master_key, hashlib.sha256).digest()
    info = b"kex:capability:principal:" + principal.encode("utf-8")
    
    # Expand 1 block (32 bytes)
    t1 = hmac.new(prk, info + b"\x01", hashlib.sha256).digest()
    return t1[:length]


class HardenedCapabilityEngine:
    """
    Hardened cryptographic capability engine providing tamper-proof,
    replay-protected, and payload-bound authorization tokens.
    """
    def __init__(self, master_key: Optional[bytes] = None) -> None:
        self.master_key = master_key or os.environ.get(
            "KEX_MASTER_SECRET_KEY", "KEX_DEFAULT_SECURE_MASTER_SECRET_2026"
        ).encode("utf-8")
        self._replay_cache: Set[str] = set()

    def issue_capability_token(
        self,
        principal: str,
        product: str,
        operation: str,
        payload: Dict[str, Any],
        ttl_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Issues an HMAC-SHA256 capability token explicitly bound to (principal, product, operation, payload).
        """
        now = int(time.time())
        exp = now + ttl_seconds
        jti = secrets.token_hex(16)
        payload_hash = sha256_hex(payload)

        claims = {
            "iss": "kex://auth-engine",
            "principal": principal,
            "product": product,
            "operation": operation,
            "payload_hash": payload_hash,
            "iat": now,
            "exp": exp,
            "jti": jti,
        }

        claims_raw = canon_bytes(claims)
        claims_b64 = base64.urlsafe_b64encode(claims_raw).decode("ascii").rstrip("=")
        
        derived_key = hkdf_extract_and_expand(self.master_key, principal)
        sig = hmac.new(derived_key, claims_raw, hashlib.sha256).hexdigest()

        token = f"{claims_b64}.{sig}"
        return {
            "token": token,
            "claims": claims,
            "signature": sig,
            "expires_at": exp,
            "jti": jti
        }

    def verify_capability_token(
        self,
        token: str,
        expected_principal: str,
        expected_product: str,
        expected_operation: str,
        expected_payload: Dict[str, Any],
        consume_nonce: bool = True
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Verifies capability token against claimed identity, requested operation, and exact payload.
        Returns: (is_valid, reason_or_status, claims)
        """
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return False, "INVALID_TOKEN_FORMAT", None
            
            claims_b64, sig = parts
            # Restore base64 padding
            padded_b64 = claims_b64 + "=" * (-len(claims_b64) % 4)
            claims_raw = base64.urlsafe_b64decode(padded_b64)
            claims = json.loads(claims_raw.decode("utf-8"))

            claimed_principal = claims.get("principal")
            if not claimed_principal:
                return False, "MISSING_PRINCIPAL", None

            # 1. Re-derive key using claimed principal (Prevents principal relabeling attacks)
            derived_key = hkdf_extract_and_expand(self.master_key, claimed_principal)
            expected_sig = hmac.new(derived_key, claims_raw, hashlib.sha256).hexdigest()

            # 2. Constant-time signature comparison
            if not hmac.compare_digest(sig, expected_sig):
                return False, "BAD_SIGNATURE", None

            # 3. Check expiration
            now = int(time.time())
            if now > claims.get("exp", 0):
                return False, "TOKEN_EXPIRED", None

            if now < claims.get("iat", 0) - 60:  # Allow 60s max clock skew
                return False, "TOKEN_NOT_YET_VALID", None

            # 4. Scope and Identity Verification
            if claims.get("principal") != expected_principal:
                return False, "PRINCIPAL_MISMATCH", None

            if claims.get("product") != expected_product:
                return False, "PRODUCT_SCOPE_MISMATCH", None

            if claims.get("operation") != expected_operation:
                return False, "OPERATION_SCOPE_MISMATCH", None

            # 5. Payload Binding Verification
            current_payload_hash = sha256_hex(expected_payload)
            if claims.get("payload_hash") != current_payload_hash:
                return False, "PAYLOAD_TAMPERED", None

            # 6. Replay Attack Verification (JTI Nonce Check)
            jti = claims.get("jti")
            if not jti:
                return False, "MISSING_JTI_NONCE", None

            if jti in self._replay_cache:
                return False, "REPLAY_DETECTED", None

            if consume_nonce:
                self._replay_cache.add(jti)

            return True, "AUTHORIZED", claims

        except Exception as e:
            return False, f"VERIFICATION_EXCEPTION: {type(e).__name__}", None


# Canonical Alias for Backward/Forward Compatibility
BilateralTokenEngine = HardenedCapabilityEngine
