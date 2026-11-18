#!/usr/bin/env python3
"""
Open Badges 3.0 Credential Signer (eddsa-rdfc-2022)
Signs OB3.0 credentials using Ed25519 with RDF canonicalization (URDNA2015)
"""

import json
import sys
import ssl
import hashlib
import base58
import urllib.request
from datetime import datetime, timezone
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.backends import default_backend
from pyld import jsonld

# Handle SSL certificate issues
ssl._create_default_https_context = ssl._create_unverified_context

_CONTEXT_CACHE = {}


def custom_document_loader(url, options=None):
    """Fetch and cache real JSON-LD contexts from the network."""
    if url not in _CONTEXT_CACHE:
        print(f"[DEBUG] Fetching context: {url}", file=sys.stderr)
        req = urllib.request.Request(url, headers={"Accept": "application/ld+json, application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            _CONTEXT_CACHE[url] = json.loads(response.read().decode("utf-8"))
    
    return {
        "contextUrl": None,
        "documentUrl": url,
        "document": _CONTEXT_CACHE[url],
    }


def sign_credential(credential_json_path: str, private_key_path: str) -> dict:
    """Sign OB3.0 credential with Ed25519 using eddsa-rdfc-2022."""
    
    with open(credential_json_path, 'r') as f:
        credential = json.load(f)
    
    with open(private_key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
    
    if not isinstance(private_key, ed25519.Ed25519PrivateKey):
        raise ValueError("Private key must be Ed25519")
    
    credential_without_proof = {k: v for k, v in credential.items() if k != 'proof'}
    
    issuer = credential_without_proof["issuer"]
    issuer_id = issuer["id"] if isinstance(issuer, dict) else issuer
    
    if issuer_id.startswith("did:key:"):
        verification_method = issuer_id + "#" + issuer_id.split(":")[-1]
    else:
        verification_method = issuer_id + "#key-1"
    
    proof_options = {
        "@context": credential_without_proof["@context"],
        "type": "DataIntegrityProof",
        "cryptosuite": "eddsa-rdfc-2022",
        "created": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "verificationMethod": verification_method,
        "proofPurpose": "assertionMethod",
    }
    
    jsonld_opts = {
        "algorithm": "URDNA2015",
        "format": "application/n-quads",
        "documentLoader": custom_document_loader
    }
    
    doc_nquads = jsonld.normalize(credential_without_proof, jsonld_opts)
    proof_nquads = jsonld.normalize(proof_options, jsonld_opts)
    
    proof_hash = hashlib.sha256(proof_nquads.encode("utf-8")).digest()
    doc_hash = hashlib.sha256(doc_nquads.encode("utf-8")).digest()
    hash_data = proof_hash + doc_hash
    
    print(f"[DEBUG] Proof hash:    {proof_hash.hex()}")
    print(f"[DEBUG] Doc hash:      {doc_hash.hex()}")
    print(f"[DEBUG] Combined(64B): {hash_data.hex()}")
    
    signature_bytes = private_key.sign(hash_data)
    proof_value = "z" + base58.b58encode(signature_bytes).decode('ascii')
    
    proof_options_for_credential = {k: v for k, v in proof_options.items() if k != '@context'}
    proof_options_for_credential["proofValue"] = proof_value
    credential["proof"] = [proof_options_for_credential]
    
    return credential


def main():
    if len(sys.argv) < 2:
        print("Usage: sign_ob3_credential.py <credential.json> [private_key.pem]")
        sys.exit(1)
    
    credential_path = sys.argv[1]
    private_key_path = sys.argv[2] if len(sys.argv) > 2 else "keys/badge_private_key.pem"
    
    try:
        signed_credential = sign_credential(credential_path, private_key_path)
        with open(credential_path, 'w') as f:
            json.dump(signed_credential, f, indent=2)
        print(f"✅ Signed: {credential_path}")
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
