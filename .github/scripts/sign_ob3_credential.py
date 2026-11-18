#!/usr/bin/env python3
"""
Open Badges 3.0 Credential Signer (eddsa-rdfc-2022)
Signs OB3.0 credentials using Ed25519 with RDF canonicalization (URDNA2015)
"""

import json
import sys
import hashlib
import base58
from datetime import datetime, timezone
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.backends import default_backend

try:
    from pyld import jsonld
    HAS_PYLD = True
except ImportError:
    HAS_PYLD = False


# Pre-cached JSON-LD contexts to avoid network calls
CACHED_CONTEXTS = {
    "https://www.w3.org/ns/credentials/v2": {
        "@context": {
            "@version": 1.1,
            "@vocab": "https://www.w3.org/ns/credentials#",
            "id": "@id",
            "type": "@type"
        }
    },
    "https://purl.imsglobal.org/spec/ob/v3p0/context-3.0.3.json": {
        "@context": {
            "Achievement": "https://w3id.org/openbadges#Achievement",
            "Assertion": "https://w3id.org/openbadges#Assertion",
            "BadgeClass": "https://w3id.org/openbadges#BadgeClass"
        }
    }
}


def custom_document_loader(url, options=None):
    """Custom document loader with cached contexts."""
    if url in CACHED_CONTEXTS:
        return {"contextUrl": url, "document": CACHED_CONTEXTS[url], "documentUrl": url}
    
    # For uncached URLs, try network
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=5) as response:
            doc = json.loads(response.read().decode('utf-8'))
            return {"contextUrl": url, "document": doc, "documentUrl": url}
    except Exception as e:
        print(f"⚠️  Could not load context from {url}: {e}", file=sys.stderr)
        raise


def sign_credential(credential_json_path: str, private_key_path: str) -> dict:
    """
    Sign an OB3.0 credential with Ed25519 using eddsa-rdfc-2022 cryptosuite.
    Uses RDF canonicalization (URDNA2015).
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
    
    # Create a copy without proof
    credential_without_proof = {k: v for k, v in credential.items() if k != 'proof'}
    
    # Extract verification method
    if credential_without_proof["issuer"]["id"].startswith("did:key:"):
        verification_method = credential_without_proof["issuer"]["id"] + "#" + credential_without_proof["issuer"]["id"].split(":")[-1]
    else:
        verification_method = credential_without_proof["issuer"]["id"] + "#key-1"
    
    # Create proof options WITH @context
    proof_options = {
        "@context": credential_without_proof["@context"],
        "type": "DataIntegrityProof",
        "cryptosuite": "eddsa-rdfc-2022",
        "created": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "verificationMethod": verification_method,
        "proofPurpose": "assertionMethod",
    }
    
    if HAS_PYLD:
        try:
            # Use RDF canonicalization with custom document loader
            jsonld_opts = {
                "algorithm": "URDNA2015",
                "format": "application/n-quads",
                "documentLoader": custom_document_loader
            }
            
            doc_nquads = jsonld.normalize(credential_without_proof, jsonld_opts)
            proof_nquads = jsonld.normalize(proof_options, jsonld_opts)
            
        except Exception as e:
            print(f"⚠️  RDF canonicalization failed, using JSON normalization: {e}", file=sys.stderr)
            doc_nquads = json.dumps(credential_without_proof, sort_keys=True, separators=(',', ':'))
            proof_nquads = json.dumps(proof_options, sort_keys=True, separators=(',', ':'))
    else:
        # Fallback: simple JSON normalization
        doc_nquads = json.dumps(credential_without_proof, sort_keys=True, separators=(',', ':'))
        proof_nquads = json.dumps(proof_options, sort_keys=True, separators=(',', ':'))
    
    # Hash both (raw 32-byte digests)
    proof_hash = hashlib.sha256(proof_nquads.encode("utf-8")).digest()
    doc_hash = hashlib.sha256(doc_nquads.encode("utf-8")).digest()
    
    # Concatenate: proof hash FIRST, doc hash SECOND
    hash_data = proof_hash + doc_hash
    
    # Debug output
    print(f"[DEBUG] Proof hash:    {proof_hash.hex()}")
    print(f"[DEBUG] Doc hash:      {doc_hash.hex()}")
    print(f"[DEBUG] Combined(64B): {hash_data.hex()}")
    
    # Sign and encode as base58btc
    signature_bytes = private_key.sign(hash_data)
    proof_value = "z" + base58.b58encode(signature_bytes).decode('ascii')
    
    # Build proof without @context
    proof_options_for_credential = {k: v for k, v in proof_options.items() if k != '@context'}
    proof_options_for_credential["proofValue"] = proof_value
    
    # Add proof array
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
