#!/usr/bin/env python3
"""
Unified Badge Generator - OB2.0 and OB3.0
Generates both Open Badges 2.0 (IMS Global) and 3.0 (W3C Verifiable Credentials)
"""

import json
import uuid
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path


def generate_ob2_assertion(email: str, badge_class_url: str, issuer_url: str) -> dict:
    """Generate OB2.0 assertion with unsalted email hash."""
    email_lower = email.lower()
    email_hash = hashlib.sha256(email_lower.encode()).hexdigest()
    
    return {
        "@context": "https://w3id.org/openbadges/v2",
        "id": f"https://{Path.cwd().name}/assertions/{uuid.uuid4()}.json",
        "type": "Assertion",
        "badge": badge_class_url,
        "issuedOn": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "recipient": {
            "type": "email",
            "hashed": True,
            "identity": f"sha256${email_hash}"
        },
        "verification": {
            "type": "hosted"
        }
    }


def generate_ob3_credential(email: str, achievement_name: str, issuer_name: str, issuer_did: str, upstream_url: str, image_url: str) -> dict:
    """Generate OB3.0 credential with did:key."""
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
                "image": {
                    "id": image_url,
                    "type": "Image"
                },
                "criteria": {
                    "narrative": "Upstream certificate was validated at time of issuance."
                }
            }
        },
        "evidence": [
            {
                "id": upstream_url,
                "type": ["Evidence"],
                "name": f"Original Upstream {issuer_name} Certificate"
            }
        ]
    }


def main():
    if len(sys.argv) < 6:
        print("Usage: badge_generator.py <email> <achievement_name> <issuer_name> <upstream_url> <image_url> [issuer_did]")
        print("\nExample:")
        print('  python3 badge_generator.py "user@example.com" "Azure Admin" "Microsoft Learn" "https://learn.microsoft.com/..." "https://certs.djpai.dev/images/badge.png"')
        sys.exit(1)
    
    email = sys.argv[1]
    achievement_name = sys.argv[2]
    issuer_name = sys.argv[3]
    upstream_url = sys.argv[4]
    image_url = sys.argv[5]
    issuer_did = sys.argv[6] if len(sys.argv) > 6 else "did:key:z6MkeWEbXvH68irW1mameCz8ywzDj2F68mzfmqqBmKV8LdwL"
    
    try:
        # Generate both formats
        ob2 = generate_ob2_assertion(email, f"https://certs.djpai.dev/badges/{issuer_name.lower().replace(' ', '-')}.json", "https://certs.djpai.dev/.well-known/issuer.json")
        ob3 = generate_ob3_credential(email, achievement_name, issuer_name, issuer_did, upstream_url, image_url)
        
        # Save OB2.0
        ob2_file = f"assertions/{uuid.uuid4()}.json"
        Path("assertions").mkdir(exist_ok=True)
        with open(ob2_file, 'w') as f:
            json.dump(ob2, f, indent=2)
        
        # Save OB3.0 (unsigned)
        ob3_file = f"credentials/{uuid.uuid4()}.json"
        Path("credentials").mkdir(exist_ok=True)
        with open(ob3_file, 'w') as f:
            json.dump(ob3, f, indent=2)
        
        print(f"✅ Generated badges:")
        print(f"   OB2.0: {ob2_file}")
        print(f"   OB3.0: {ob3_file} (unsigned, needs signing)")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
