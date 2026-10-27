"""Canonical JSON serialization and Ed25519 cryptographic signing.

WHY:
- Section 3: "Canonical JSON (sorted keys, no whitespace) before any hashing or signing."
  This guarantees that equivalent documents produce identical byte representations across
  different platforms, languages, and serialization libraries.
- Ed25519 (via PyNaCl) provides deterministic signatures without risk of nonce reuse,
  timing attacks, or malleable signatures.
- Packages mandate/, policy/, and audit/ must never import LLM or agent code (P1).
"""

from __future__ import annotations

import json
from typing import Any

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey


def canonical_json_bytes(data: dict[str, Any]) -> bytes:
    """Serialize dictionary to canonical JSON bytes.

    Canonical rules:
    1. Keys sorted alphabetically at all nesting levels.
    2. No whitespace between delimiters (separators=(',', ':')).
    3. UTF-8 encoded.
    4. Non-ASCII preserved without escape sequences (ensure_ascii=False).
    """

    def _normalize(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _normalize(v) for k, v in sorted(obj.items())}
        if isinstance(obj, list):
            return [_normalize(item) for item in obj]
        return obj

    normalized = _normalize(data)
    json_str = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return json_str.encode("utf-8")


def generate_keypair() -> tuple[str, str]:
    """Generate a new Ed25519 keypair.

    Returns:
        tuple of (private_key_hex, public_key_hex).
    """
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key
    return signing_key.encode().hex(), verify_key.encode().hex()


def sign_canonical_payload(payload: dict[str, Any], private_key_hex: str) -> str:
    """Sign canonical JSON representation of payload using Ed25519.

    Any existing 'signature' key in payload is omitted before signing.

    Returns:
        Hex-encoded signature string (64 bytes = 128 hex chars).
    """
    clean_payload = {k: v for k, v in payload.items() if k != "signature"}
    data_bytes = canonical_json_bytes(clean_payload)
    signing_key = SigningKey(bytes.fromhex(private_key_hex))
    signed = signing_key.sign(data_bytes)
    return signed.signature.hex()


def verify_canonical_payload(
    payload: dict[str, Any], signature_hex: str, public_key_hex: str
) -> bool:
    """Verify Ed25519 signature over canonical JSON representation of payload.

    Any existing 'signature' key in payload is omitted before verification.

    Returns:
        True if signature is mathematically valid for payload, False otherwise.
    """
    clean_payload = {k: v for k, v in payload.items() if k != "signature"}
    data_bytes = canonical_json_bytes(clean_payload)
    try:
        verify_key = VerifyKey(bytes.fromhex(public_key_hex))
        signature_bytes = bytes.fromhex(signature_hex)
        verify_key.verify(data_bytes, signature_bytes)
        return True
    except (BadSignatureError, ValueError):
        return False
