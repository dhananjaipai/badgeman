# Open Badges Proxy Issuer

Cryptographically signed Open Badges proxy for Credly. Accepts non-compliant upstream credentials (Microsoft Learn, Oracle, Mistral AI) and issues verified badges.

## 🎯 Supported Formats

- **OB2.0** (IMS Global) - For Credly upload
- **OB3.0** (W3C Verifiable Credentials) - Self-contained cryptographic signatures

## 🚀 Quick Start

### Generate Badges (GitHub Actions)

1. Go to **Actions** → **Generate Open Badges**
2. Click **Run workflow**
3. Fill in the inputs:
   - **Email**: recipient email (lowercase)
   - **Achievement Name**: Badge title
   - **Issuer Name**: Organization (e.g., "Microsoft Learn")
   - **Upstream URL**: Link to original certificate
   - **Image URL**: Badge image URL (e.g., `https://certs.djpai.dev/badges/images/badge.png`)
4. Run → Badges generated and committed

### Manual Generation (Local)

```bash
python3 badge_generator.py \
  "user@example.com" \
  "Azure Administrator Associate" \
  "Microsoft Learn" \
  "https://learn.microsoft.com/en-us/users/..." \
  "https://certs.djpai.dev/badges/images/azure-badge.png"
```

Outputs:
- OB2.0: `assertions/<uuid>.json` (ready to upload to Credly)
- OB3.0: `credentials/<uuid>.json` (unsigned)

### Sign OB3.0 Credentials

```bash
python3 .github/scripts/sign_ob3_credential.py credentials/<uuid>.json keys/badge_private_key.pem
```

## 📋 OB2.0 Workflow (Credly Upload)

1. Generate with `badge_generator.py`
2. Find `assertions/<uuid>.json`
3. Upload to Credly: Badge Wallet → Other → + Upload Other Badges → Select JSON file

## 🔐 OB3.0 Workflow (W3C Verifiable Credentials)

1. Generate with `badge_generator.py`
2. Sign with `.github/scripts/sign_ob3_credential.py`
3. Upload to Credly or verify at: https://badges.badgr.com/public/validate

## 🔑 Cryptography

- **Algorithm**: Ed25519
- **Signing**: eddsa-rdfc-2022 (RDF canonicalization URDNA2015)
- **DID**: `did:key:z6MkeWEbXvH68irW1mameCz8ywzDj2F68mzfmqqBmKV8LdwL`
- **Public Key**: `.well-known/did.json` and `/.well-known/issuer.json`

## 📂 Directory Structure

```
.
├── badge_generator.py                # Unified OB2.0 + OB3.0 generator
├── .github/
│   ├── workflows/
│   │   └── generate-badges.yml       # GitHub Actions workflow
│   └── scripts/
│       └── sign_ob3_credential.py    # OB3.0 Ed25519 signer
├── .well-known/
│   ├── did.json                      # DID document with public key
│   └── issuer.json                   # OB2.0 issuer metadata
├── keys/
│   ├── badge_private_key.pem         # Private key (SECRET - in repo secrets)
│   └── badge_public_key.pem          # Public key
├── assertions/                       # OB2.0 badges
├── credentials/                      # OB3.0 badges (unsigned)
└── badges/
    ├── images/                       # Badge graphics
    └── mistral-partner.json          # Badge class template
```

## ⚙️ Configuration

**Email Hashing**: OB2.0 uses SHA256 unsalted hash of lowercase email
- Must match exactly with Credly account email
- Example: `dhananjaimvpai@gmail.com` → `sha256$5821a508...`

**Issuer**: Configure in `.well-known/issuer.json`
- Name, email, description, logo

**DID**: OB3.0 uses `did:key` format with embedded public key
- Self-verifiable, no network lookup needed

## 🧪 Testing

**OB2.0**: Upload to Credly → Check wallet

**OB3.0**: https://badges.badgr.com/public/validate
- Paste credential URL or JSON
- Should show: ✅ All 13 tests pass

## 🛠️ Troubleshooting

### OB2.0 Upload Fails
- Verify email hash matches Credly account
- Ensure image URL is accessible
- Check issuer metadata in `.well-known/issuer.json`

### OB3.0 Signature Invalid
- Verify Ed25519 private key in `keys/badge_private_key.pem`
- Check RDF canonicalization: contexts must fetch from real URLs
- Ensure proof uses base58btc encoding (starts with `z`)

### Cloudflare Cache Issues
- Purge cache manually in Cloudflare dashboard
- Or wait 10 minutes for TTL

## 📚 References

- [Open Badges 2.0 Spec](https://www.imsglobal.org/sites/default/files/Badges/OBv2_0Final.pdf)
- [Open Badges 3.0 Spec](https://www.imsglobal.org/spec/ob/v3p0/)
- [W3C Verifiable Credentials](https://www.w3.org/TR/vc-data-model/)
- [DID Spec](https://www.w3.org/TR/did-core/)
- [Data Integrity Proofs](https://www.w3.org/TR/vc-data-integrity/)

## 📄 License

MIT
