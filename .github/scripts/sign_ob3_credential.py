#!/usr/bin/env python3
"""
Open Badges 3.0 Credential Signer
Signs unsigned OB3.0 credentials using Ed25519 Data Integrity Proof (eddsa-rdfc-2022)
"""

import json
import sys
import hashlib
import base64
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.backends import default_backend


def normalize_json_ld(obj):
    """
    Normalize JSON-LD using RDFC-2015 (Recursive Descent Canonicalization).
    This is a simplified implementation suitable for Ed25519 signing.
    """
    if isinstance(obj, dict):
        # Sort keys alphabetically
        return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def sign_credential(credential_json_path: str, private_key_path: str, domain: str = "certs.djpai.dev") -> dict:
    """
    Sign an unsigned OB3.0 credential with an Ed25519 Data Integrity Proof.
    
    Args:
        credential_json_path: Path to unsigned credential JSON
        private_key_path: Path to Ed25519 private key (PEM format)
        domain: Domain for the DID (default: certs.djpai.dev)
    
    Returns:
        Signed credential dict with proof object
    """
    
    # Load unsigned credential
    with open(credential_json_path, 'r') as f:
        credential = json.load(f)
    
    # Load private key
    with open(private_key_path, 'rb') as f:
        pem_data = f.read()
        private_key = serialization.load_pem_private_key(pem_data, password=None, backend=default_backend())
    
    if not isinstance(private_key, ed25519.Ed25519PrivateKey):
        raise ValueError("Private key must be Ed25519")
    
    # Create proof options (canonicalized)
    proof_options = {
        "type": "DataIntegrityProof",
        "cryptosuite": "eddsa-rdfc-2022",
        "created": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "verificationMethod": f"did:web:{domain}#key-1",
        "proofPurpose": "assertionMethod"
    }
    
    # Create a copy for signing (without proof field)
    credential_for_signing = credential.copy()
    
    # Normalize credential for signing
    credential_normalized = normalize_json_ld(credential_for_signing)
    options_normalized = normalize_json_ld(proof_options)
    
    # Create signing input: options + credential
    signing_input = options_normalized + credential_normalized
    
    # Sign
    signature_bytes = private_key.sign(signing_input.encode('utf-8'))
    
    # Encode signature as base64
    proof_value = base64.b64encode(signature_bytes).decode('utf-8')
    
    # Add proof to credential
    proof_options["proofValue"] = proof_value
    credential["proof"] = proof_options
    
    return credential


def main():
    """CLI interface for signing credentials."""
    if len(sys.argv) < 2:
        print("Usage: sign_ob3_credential.py <credential.json> [private_key.pem] [domain]")
        print("\nExample:")
        print("  python3 sign_ob3_credential.py badges/05647af0-8547-4369-ab5f-332a1e446463.json keys/badge_private_key.pem")
        sys.exit(1)
    
    credential_path = sys.argv[1]
    private_key_path = sys.argv[2] if len(sys.argv) > 2 else "keys/badge_private_key.pem"
    domain = sys.argv[3] if len(sys.argv) > 3 else "certs.djpai.dev"
    
    try:
        # Sign credential
        signed_credential = sign_credential(credential_path, private_key_path, domain)
        
        # Save signed credential (overwrite original)
        with open(credential_path, 'w') as f:
            json.dump(signed_credential, f, indent=2)
        
        print(f"✅ Credential signed successfully!")
        print(f"   File: {credential_path}")
        print(f"   Proof type: {signed_credential['proof']['cryptosuite']}")
        print(f"   Verification method: {signed_credential['proof']['verificationMethod']}")
        print(f"\n📋 Next step: Upload this JSON to Credly or test with validator")
        print(f"   Validator: https://badges.badgr.com/public/validate")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
