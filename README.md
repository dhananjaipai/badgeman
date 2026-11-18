# Open Badges Proxy Issuer

Cryptographically signed Open Badges proxy for Credly. Issues verified badges for non-compliant upstream credentials (Microsoft Learn, Oracle, Mistral AI, etc.).

## 🎯 Why?

Platforms like Microsoft Learn, Oracle, and Mistral don't issue compliant Open Badges, so Credly blocks them. This proxy acts as an issuer, cryptographically signing wrapper credentials that point to the upstream link, forcing Credly to accept and verify them.

## ✨ Features

- **Dual Format**: Generates both OB2.0 (Credly) and OB3.0 (W3C) in one command
- **Automated Signing**: Ed25519 signatures with RDF canonicalization (eddsa-rdfc-2022)
- **GitHub Actions**: Workflow inputs for one-click badge generation
- **Self-Verifying**: OB3.0 uses `did:key` (no network lookup needed)
- **GitHub Pages Hosted**: Zero backend infrastructure required

## 📋 How It Works

```
Upstream Certificate (e.g., Microsoft Learn)
        ↓
   badge_generator.py
   ├── Generates OB2.0 Assertion
   │   └── Hash recipient email → assertions/<uuid>.json
   │
   └── Generates & Signs OB3.0 Credential
       ├── Ed25519 signature
       ├── RDF canonicalization (URDNA2015)
       └── credentials/<uuid>.json (final signed)
        ↓
   Upload to Credly (OB2.0) or verify at badges.badgr.com (OB3.0)
```

## 🚀 Quick Start

### GitHub Actions (Recommended)

1. **Go to Actions** → **Generate Open Badges** → **Run workflow**
2. **Fill inputs:**
   - Email: `user@example.com`
   - Achievement: `Azure Administrator Associate`
   - Issuer: `Microsoft Learn`
   - Upstream URL: `https://learn.microsoft.com/en-us/users/...`
   - Image URL: `https://certs.djpai.dev/badges/images/badge.png`
3. **Run** → Badges generated, signed, and committed ✅

### Local (Manual)

```bash
python3 badge_generator.py \
  "user@example.com" \
  "Azure Administrator Associate" \
  "Microsoft Learn" \
  "https://learn.microsoft.com/en-us/users/..." \
  "https://certs.djpai.dev/badges/images/badge.png"
```

**Output:**
- `assertions/<uuid>.json` → Upload to Credly
- `credentials/<uuid>.json` → Verify at https://badges.badgr.com/public/validate

## 📂 Directory Structure

```
.
├── badge_generator.py                    # Unified OB2.0 + OB3.0 generator
├── .github/
│   ├── workflows/generate-badges.yml     # GitHub Actions workflow
├── .well-known/
│   └── issuer.json                       # OB2.0 issuer metadata
├── keys/
│   ├── badge_private_key.pem             # Ed25519 private key (SECRET)
│   └── badge_public_key.pem              # Public key (reference)
├── assertions/                           # OB2.0 badges (output)
└── credentials/                          # OB3.0 badges - signed (output)
```

## 🔐 Cryptography

- **Algorithm**: Ed25519 (fastest, most secure for signatures)
- **Signing**: Data Integrity Proof with eddsa-rdfc-2022 cryptosuite
- **Canonicalization**: URDNA2015 (RDF N-Quads)
- **DID Format**: `did:key:z6MkeWEbXvH68irW1mameCz8ywzDj2F68mzfmqqBmKV8LdwL`
- **Public Key**: Embedded in DID (no network lookup needed)

## 📤 OB2.0 Workflow (Credly Upload)

1. Generate with `badge_generator.py`
2. Find `assertions/<uuid>.json`
3. Upload to Credly:
   - **Badge Wallet** → **Other** → **+ Upload Other Badges** → Select JSON file
   - Credly validates against `.well-known/issuer.json`
   - ✅ Badge appears in wallet

**Note:** Custom issuer badges appear in "Other" tab only (not official transcripts)

## 🔒 OB3.0 Workflow (Verifiable Credentials)

1. Generate & sign with `badge_generator.py`
2. Find `credentials/<uuid>.json`
3. Verify at https://badges.badgr.com/public/validate
4. All 13 tests should pass ✅

## ⚙️ Configuration

### Issuer Metadata (`.well-known/issuer.json`)

```json
{
  "@context": "https://w3id.org/openbadges/v2",
  "id": "https://certs.djpai.dev/.well-known/issuer.json",
  "type": "Profile",
  "name": "Your Organization",
  "email": "contact@example.com",
  "image": "https://example.com/logo.png",
  "url": "https://example.com"
}
```

### Email Hashing (Critical for Credly)

OB2.0 uses SHA256 hash of **lowercase** email:
```
Input:  user@example.com
Hash:   sha256$<64-char-hex-string>
```

Must match exactly with Credly account email.

### DID (OB3.0)

Default: `did:key:z6MkeWEbXvH68irW1mameCz8ywzDj2F68mzfmqqBmKV8LdwL`

Change by passing as argument:
```bash
python3 badge_generator.py <email> <name> <issuer> <url> <image> <your-did>
```

## 🧪 Testing

**OB2.0:**
1. Generate locally
2. Upload to Credly
3. Check wallet (Other tab)

**OB3.0:**
1. Generate locally
2. Host on GitHub Pages or raw.githubusercontent.com
3. Validate at https://badges.badgr.com/public/validate
4. Expected: ✅ All 13 tests pass

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| Credly upload fails | Email hash doesn't match Credly account. Regenerate with correct email. |
| Image unreachable | URL must be publicly accessible. Use `https://certs.djpai.dev/badges/images/...` |
| OB3.0 signature invalid | Ensure `keys/badge_private_key.pem` exists. Check RDF canonicalization. |
| Cloudflare cache stale | Purge manually in Cloudflare dashboard or wait 10 minutes. |

## 📚 References

- [Open Badges 2.0 Spec](https://www.imsglobal.org/sites/default/files/Badges/OBv2_0Final.pdf)
- [Open Badges 3.0 Spec](https://www.imsglobal.org/spec/ob/v3p0/)
- [W3C Verifiable Credentials](https://www.w3.org/TR/vc-data-model/)
- [DID Specification](https://www.w3.org/TR/did-core/)
- [Data Integrity Proofs](https://www.w3.org/TR/vc-data-integrity/)

## 📄 License

MIT
