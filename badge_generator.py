#!/usr/bin/env python3
"""
Open Badges 3.0 Generator
Generates unsigned Open Badges 3.0 credentials with upstream evidence.
"""

import json
import uuid
import sys
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path


def generate_badge(
    upstream_url: str,
    image_path: str,
    issuer_name: str,
    achievement_name: str,
    credential_email: str,
    expiry_date: str = None,
    domain: str = "certs.djpai.dev",
    output_dir: str = "badges"
) -> tuple:
    """
    Generate an unsigned Open Badges 3.0 credential.
    
    Args:
        upstream_url: URL to the original certificate (for evidence)
        image_path: Path to downloaded badge image file (PNG/SVG)
        issuer_name: Name of the issuing organization (e.g., "Microsoft Learn")
        achievement_name: Name of the achievement
        credential_email: Credly email (MUST be lowercase)
        expiry_date: Optional expiration date (dd/mm/yyyy format)
        domain: Domain where badges are hosted (default: certs.djpai.dev)
        output_dir: Directory to store generated files
    
    Returns:
        tuple: (unsigned credential dict, credential_uuid)
    """
    
    # Validate inputs
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    if not credential_email.islower():
        raise ValueError(f"Email must be lowercase: {credential_email}")
    
    # Ensure email is lowercase
    credential_email = credential_email.lower()
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/images", exist_ok=True)
    
    # Generate unique ID for this credential
    credential_uuid = str(uuid.uuid4())
    
    # Image already downloaded, construct image URL with hash-based filename
    image_filename = os.path.basename(image_path)
    dest_image_path = f"{output_dir}/images/{image_filename}"
    if not os.path.exists(dest_image_path):
        os.rename(image_path, dest_image_path)
    
    # Construct image URL
    image_url = f"https://{domain}/badges/images/{image_filename}"
    
    # Parse expiry date if provided (dd/mm/yyyy → ISO 8601)
    credential_obj = {
        "@context": [
            "https://www.w3.org/ns/credentials/v2",
            "https://purl.imsglobal.org/spec/ob/v3p0/context-3.0.3.json"
        ],
        "id": f"urn:uuid:{credential_uuid}",
        "type": ["VerifiableCredential", "OpenBadgeCredential"],
        "name": issuer_name,
        "issuer": {
            "id": f"did:web:{domain}",
            "type": ["Profile"],
            "name": issuer_name
        },
        "validFrom": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "issuanceDate": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    }
    
    # Add expiration date if provided (kept for future use)
    # if expiry_date:
    #     try:
    #         day, month, year = expiry_date.split('/')
    #         expiry_dt = datetime(int(year), int(month), int(day), 23, 59, 59, tzinfo=timezone.utc)
    #         credential_obj["expirationDate"] = expiry_dt.isoformat().replace('+00:00', 'Z')
    #     except (ValueError, IndexError):
    #         raise ValueError(f"Invalid date format: {expiry_date}. Use dd/mm/yyyy")
    
    
    credential_obj.update({
        "credentialSubject": {
            "id": f"mailto:{credential_email}",
            "type": ["AchievementSubject"],
            "achievement": {
                "id": f"https://{domain}/achievements/{credential_uuid}",
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
    })
    
    return credential_obj, credential_uuid


def save_credential(credential: dict, credential_uuid: str, output_dir: str = "badges"):
    """Save unsigned credential to JSON file."""
    output_file = f"{output_dir}/{credential_uuid}.json"
    with open(output_file, 'w') as f:
        json.dump(credential, f, indent=2)
    return output_file


def main():
    """CLI interface for badge generation."""
    if len(sys.argv) < 6:
        print("Usage: badge_generator.py <upstream_url> <image_path> <issuer_name> <achievement_name> <email> [expiry_date]")
        print("\nExample:")
        print("  python3 badge_generator.py \\")
        print('    "https://learn.microsoft.com/en-us/users/..." \\')
        print('    "/tmp/badge.png" \\')
        print('    "Microsoft Learn" \\')
        print('    "Azure Administrator Associate" \\')
        print('    "your.email@domain.com" \\')
        print('    "17/11/2027"  # optional expiry date')
        sys.exit(1)
    
    upstream_url = sys.argv[1]
    image_path = sys.argv[2]
    issuer_name = sys.argv[3]
    achievement_name = sys.argv[4]
    credential_email = sys.argv[5]
    expiry_date = sys.argv[6] if len(sys.argv) > 6 else None
    
    try:
        credential, uuid_str = generate_badge(
            upstream_url=upstream_url,
            image_path=image_path,
            issuer_name=issuer_name,
            achievement_name=achievement_name,
            credential_email=credential_email,
            expiry_date=expiry_date
        )
        
        output_file = save_credential(credential, uuid_str)
        
        print(f"✅ Badge generated successfully!")
        print(f"   UUID: {uuid_str}")
        print(f"   File: {output_file}")
        print(f"   Image: badges/images/{os.path.basename(image_path)}")
        if expiry_date:
            print(f"   Expires: {credential.get('expirationDate', 'N/A')}")
        print(f"\n📋 Next step: Sign this credential using the GitHub Action (signing adds the proof object)")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
