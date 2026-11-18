#!/usr/bin/env python3
"""
Unified Badge Generator - Generates & signs both OB2.0 and OB3.0
Single script for complete badge creation workflow
"""

import json
import uuid
import sys
import hashlib
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ssl._create_default_https_context = ssl._create_unverified_context

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.backends import default_backend
    from pyld import jsonld
    import base58
    HAS_OB3_DEPS = True
except ImportError:
    HAS_OB3_DEPS = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def bake_badge_png(image_path: str, ob2_json: dict, output_file: str):
    """Bake OB2.0 assertion JSON into PNG metadata with standard key 'openbadges'."""
    if not HAS_PIL:
        print(f"⚠️  Skipping PNG baking (PIL not installed)")
        return
    
    try:
        import io
        from PIL import PngImagePlugin
        
        # Open local image file
        img = Image.open(image_path)
        
        # Store OB2.0 with standard 'openbadges' key
        ob2_json_str = json.dumps(ob2_json, separators=(',', ':'))
        
        # Create PNG info with standard Open Badges key
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("openbadges", ob2_json_str)
        
        # Save with OB2.0 metadata
        img.save(output_file, "png", pnginfo=pnginfo)
        print(f"   PNG: {output_file} (baked with OB2.0)")
    except Exception as e:
        print(f"⚠️  Failed to bake PNG: {e}")
        import traceback
        traceback.print_exc()


_CONTEXT_CACHE = {}

def custom_document_loader(url, options=None):
    """Fetch and cache JSON-LD contexts."""
    if url not in _CONTEXT_CACHE:
        req = urllib.request.Request(url, headers={"Accept": "application/ld+json, application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            _CONTEXT_CACHE[url] = json.loads(response.read().decode("utf-8"))
    return {"contextUrl": None, "documentUrl": url, "document": _CONTEXT_CACHE[url]}


def generate_ob2(email: str, issuer_url: str, achievement_name: str, badge_url: str, upstream_url: str = None) -> dict:
    """Generate OB2.0 assertion."""
    email_lower = email.lower()
    email_hash = hashlib.sha256(email_lower.encode()).hexdigest()
    
    assertion = {
        "@context": "https://w3id.org/openbadges/v2",
        "type": "Assertion",
        "badge": badge_url,
        "issuedOn": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "recipient": {
            "type": "email",
            "hashed": True,
            "identity": f"sha256${email_hash}"
        },
        "verification": {"type": "hosted"}
    }
    
    # Add evidence if upstream URL provided
    if upstream_url:
        assertion["evidence"] = [
            {
                "id": upstream_url,
                "name": "Upstream Certificate",
                "narrative": "Original certificate from upstream provider"
            }
        ]
    
    return assertion


def generate_badge_definition(achievement_name: str, achievement_description: str, issuer_name: str, image_url: str, criteria_narrative: str, issuer_url: str, badge_id: str) -> dict:
    """Generate OB2.0 badge definition (unique per achievement)."""
    return {
        "@context": "https://w3id.org/openbadges/v2",
        "type": "BadgeClass",
        "id": f"https://certs.djpai.dev/badges/{badge_id}.json",
        "name": achievement_name,
        "description": achievement_description,
        "image": image_url,
        "issuer": issuer_url,
        "criteria": {
            "narrative": criteria_narrative or f"Verified achievement from {issuer_name}"
        }
    }


def generate_ob3(email: str, achievement_name: str, issuer_name: str, issuer_did: str, upstream_url: str, image_url: str) -> dict:
    """Generate OB3.0 credential (unsigned)."""
    credential_id = str(uuid.uuid4())
    
    return {
        "@context": [
            "https://www.w3.org/ns/credentials/v2",
            "https://purl.imsglobal.org/spec/ob/v3p0/context-3.0.3.json"
        ],
        "id": f"urn:uuid:{credential_id}",
        "type": ["VerifiableCredential", "OpenBadgeCredential"],
        "name": issuer_name,
        "issuer": {
            "id": issuer_did,
            "type": ["Profile"],
            "name": issuer_name
        },
        "validFrom": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "issuanceDate": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "credentialSubject": {
            "id": f"mailto:{email.lower()}",
            "type": ["AchievementSubject"],
            "achievement": {
                "id": f"https://certs.djpai.dev/achievements/{credential_id}",
                "type": ["Achievement"],
                "name": achievement_name,
                "description": f"Achievement: {achievement_name}",
                "image": {"id": image_url, "type": "Image"},
                "criteria": {"narrative": "Upstream certificate was validated at time of issuance."}
            }
        },
        "evidence": [{
            "id": upstream_url,
            "type": ["Evidence"],
            "name": f"Original Upstream {issuer_name} Certificate"
        }]
    }


def sign_ob3(credential: dict, private_key_path: str) -> dict:
    """Sign OB3.0 credential with Ed25519."""
    if not HAS_OB3_DEPS:
        raise ImportError("OB3.0 signing requires: cryptography, pyld, base58")
    
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
    
    signature_bytes = private_key.sign(hash_data)
    proof_value = "z" + base58.b58encode(signature_bytes).decode('ascii')
    
    proof_options_for_credential = {k: v for k, v in proof_options.items() if k != '@context'}
    proof_options_for_credential["proofValue"] = proof_value
    credential_without_proof["proof"] = [proof_options_for_credential]
    
    return credential_without_proof


def main():
    if len(sys.argv) < 8:
        print("Usage: badge_generator.py <email> <achievement_name> <achievement_description> <issuer_name> <criteria_narrative> <upstream_url> <image_url> [issuer_did] [private_key_path]")
        print("\nExample:")
        print('  python3 badge_generator.py "user@example.com" "Azure Admin" "Azure Administrator certification" "Microsoft Learn" "Passed Azure exam" "https://..." "https://certs.djpai.dev/images/badge.png"')
        sys.exit(1)
    
    email = sys.argv[1]
    achievement_name = sys.argv[2]
    achievement_description = sys.argv[3]
    issuer_name = sys.argv[4]
    criteria_narrative = sys.argv[5]
    upstream_url = sys.argv[6]
    image_url = sys.argv[7]
    issuer_did = sys.argv[8] if len(sys.argv) > 8 else "did:key:z6MkeWEbXvH68irW1mameCz8ywzDj2F68mzfmqqBmKV8LdwL"
    private_key_path = sys.argv[9] if len(sys.argv) > 9 else "keys/badge_private_key.pem"
    
    try:
        # Generate badge definition ID (unique per achievement)
        badge_id = str(uuid.uuid4())
        
        # Download and save image locally
        Path("images").mkdir(exist_ok=True)
        image_filename = f"images/{badge_id}.png"
        req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            with open(image_filename, 'wb') as f:
                f.write(response.read())
        
        # Update image URL to local version
        local_image_url = f"https://certs.djpai.dev/images/{badge_id}.png"
        
        # Generate badge definition (unique per achievement) with local image
        badge_def = generate_badge_definition(achievement_name, achievement_description, issuer_name, local_image_url, criteria_narrative, "https://certs.djpai.dev/.well-known/issuer.json", badge_id)
        Path("badges").mkdir(exist_ok=True)
        with open(f"badges/{badge_id}.json", 'w') as f:
            json.dump(badge_def, f, indent=2)
        
        # Get badge URL from the definition
        badge_url = badge_def["id"]
        
        # Generate OB2.0 with upstream evidence
        ob2 = generate_ob2(email, "https://certs.djpai.dev/.well-known/issuer.json", achievement_name, badge_url, upstream_url)
        ob2_id = str(uuid.uuid4())
        ob2["id"] = f"https://certs.djpai.dev/assertions/{ob2_id}.json"
        
        Path("assertions").mkdir(exist_ok=True)
        ob2_file = f"assertions/{ob2_id}.json"
        with open(ob2_file, 'w') as f:
            json.dump(ob2, f, indent=2)
        
        # Generate & sign OB3.0 with local image URL
        ob3 = generate_ob3(email, achievement_name, issuer_name, issuer_did, upstream_url, local_image_url)
        ob3_signed = sign_ob3(ob3, private_key_path)
        ob3_id = str(uuid.uuid4())
        
        Path("credentials").mkdir(exist_ok=True)
        ob3_file = f"credentials/{ob3_id}.json"
        with open(ob3_file, 'w') as f:
            json.dump(ob3_signed, f, indent=2)
        
        # Bake PNG with OB2.0
        png_file = f"badges/{ob3_id}.png"
        bake_badge_png(image_filename, ob2, png_file)
        
        print(f"✅ Generated badges:")
        print(f"   Badge Def: badges/{badge_id}.json")
        print(f"   OB2.0: {ob2_file}")
        print(f"   OB3.0: {ob3_file} (signed)")
        print(f"   PNG: {png_file} (baked)")
        print(f"   Image: {image_filename}")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
