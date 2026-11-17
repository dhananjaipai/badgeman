# Open Badges 3.0 Proxy Issuer for Credly

**Self-host compliant Open Badges 3.0 credentials for platforms (Microsoft Learn, Mistral, Oracle, Salesforce, internal) that don't yet support W3C Verifiable Credentials.**

By acting as a **Proxy Issuer**, you cryptographically sign a wrapper credential that points to your upstream certificates. Credly verifies the signature against your public key on GitHub Pages, then validates the upstream evidence link.

---

## 🎯 Why This Matters

Platforms like Microsoft Learn, Mistral AI, and internal corporate systems don't issue compliant Open Badges 3.0 credentials. Credly's native verifier blocks them. **This system solves that** by letting you create verifiable wrappers that:

- ✅ Are cryptographically signed with Ed25519
- ✅ Reference the upstream certificate as evidence
- ✅ Credly can verify and display in your portfolio
- ✅ Show the REAL issuer name (not "djpai.dev Proxy Issuer")
- ✅ Require only static hosting (GitHub Pages)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│ You: Trigger GitHub Action with badge details          │
├─────────────────────────────────────────────────────────┤
│ Workflow:                                               │
│  1. Download badge image from URL                      │
│  2. Generate Open Badges 3.0 JSON                      │
│  3. Sign with Ed25519 private key                      │
│  4. Commit to gh-pages branch                          │
│  5. Print public HTTPS URL                             │
│                                                         │
│ GitHub Pages: certs.djpai.dev                          │
│  ├─ /.well-known/did.json (public key)                 │
│  └─ /badges/                                            │
│      ├─ images/                                         │
│      └─ [uuid].json (signed credentials)               │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ You: Download JSON from GitHub summary                 │
│      Upload to Credly via "Other Badges" UI            │
│                                                         │
│ Credly:                                                 │
│  1. Fetches did.json from certs.djpai.dev              │
│  2. Verifies Ed25519 signature                         │
│  3. Displays badge with YOUR issuer name               │
│  4. Shows upstream evidence link                       │
└─────────────────────────────────────────────────────────┘
```

---

## 🔐 Cryptographic Identity (did:web)

You have a **unique cryptographic identity** that Credly trusts:

```
did:web:certs.djpai.dev
  ↓
Resolves to: https://certs.djpai.dev/.well-known/did.json
  ↓
Contains: Your Ed25519 public key
  ↓
Used by: Credly to verify all credentials you sign
```

This public key is published on GitHub Pages. When you sign a credential with your Ed25519 private key, Credly can verify it matches the public key at your domain.

---

## ⚙️ How It Works

### 1. Workflow Inputs

You provide:
- **upstream_url**: Link to original certificate (e.g., Microsoft Learn, Mistral, Google Drive)
- **image_url**: Direct link to badge image (PNG/SVG)
- **issuer_name**: Organization name (e.g., "Microsoft Learn") — **this appears in Credly**
- **achievement_name**: Badge name (e.g., "Azure Administrator Associate")
- **expiry_date** (optional): dd/mm/yyyy format for credential expiration

### 2. What Gets Generated

```json
{
  "@context": ["https://www.w3.org/2018/credentials/v1", "https://purl.imsglobal.org/spec/ob/v3p0/context-3.0.2.json"],
  "id": "urn:uuid:a1b2c3d4-e5f6-4a5b-9c8d-7e6f5a4b3c2d",
  "type": ["VerifiableCredential", "OpenBadgeCredential"],

  "issuer": {
    "id": "did:web:certs.djpai.dev",        # Your cryptographic identity (signer)
    "name": "Microsoft Learn"               # Your issuer_name input (what Credly shows!)
  },

  "validFrom": "2026-11-17T19:46:00Z",
  "expirationDate": "2027-11-17T23:59:59Z",

  "credentialSubject": {
    "id": "mailto:<mail>",    # Your email from PERSONAL_EMAIL secret
    "achievement": {
      "name": "Azure Administrator Associate",  # Your achievement_name input
      "image": {
        "id": "https://certs.djpai.dev/badges/images/badge-7f8e9d1c.png"  # Hosted on your domain
      }
    }
  },

  "evidence": [{
    "id": "https://learn.microsoft.com/en-us/users/.../credentials/...",  # Your upstream_url
    "name": "Original Microsoft Learn Certificate"
  }],

  "proof": {
    "type": "DataIntegrityProof",
    "cryptosuite": "ed25519-2020",
    "created": "2026-11-17T19:46:30Z",
    "verificationMethod": "did:web:certs.djpai.dev#key-1",
    "proofPurpose": "assertionMethod",
    "proofValue": "base64encodedEd25519Signature..."  # Cryptographic signature
  }
}
```

**What Credly sees**:
- ✅ Issuer: "Microsoft Learn" (from your input!)
- ✅ Achievement: "Azure Administrator Associate"
- ✅ Your email: dhananjaimvpai@gmail.com
- ✅ Image: Fetched from your domain
- ✅ Upstream evidence: Link for verification
- ✅ Cryptographic proof: Verifiable against did:web:certs.djpai.dev

### 3. Image Handling (Smart Deduplication)

Workflow downloads image from URL and saves with deterministic filename:

```
Input URL: https://learn.microsoft.com/static/azure-badge.png
  ↓
Hash: md5(url) = 7f8e9d1c
  ↓
Saved as: badges/images/badge-7f8e9d1c.png
  ↓
If same URL later: Same filename (no duplicates!)
```

### 4. Storing Badges (Permanent)

Signed badge JSON committed to `gh-pages` branch:

```
https://certs.djpai.dev/badges/{uuid}.json
```

This is:
- ✅ Permanent (git history)
- ✅ Versioned (can track changes)
- ✅ Publicly accessible (can share URL)
- ✅ No expiration (not like GitHub Actions artifacts)

---

## 🚀 Quick Start

### Step 1: Verify Prerequisites

- GitHub Pages: Publishing from `gh-pages` branch, custom domain `certs.djpai.dev`

### Step 2: Trigger Workflow

Go to repo → **Actions** → **Sign and Deploy Badge** → **Run workflow**

Fill in:
- **upstream_url**: `https://learn.mistral.ai/public/certificate/rdh8v2bdqk`
- **image_url**: `https://mistral.ai/badge.png`
- **issuer_name**: `Mistral AI`
- **achievement_name**: `Machine Learning Expert`
- **expiry_date**: `17/11/2027` (optional)

### Step 3: Get Badge JSON

Workflow runs (~60 seconds), then:
1. GitHub Actions summary shows badge details
2. Click badge JSON link or scroll to see it
3. Right-click → **Save link as** to download

Alternatively:
```bash
curl -O https://certs.djpai.dev/badges/{uuid}.json
```

### Step 4: Upload to Credly

1. Go to https://credly.com → Sign in
2. Badge Wallet → Other tab
3. Click **+ Upload Other Badges**
4. Select the JSON file
5. Done! Credly displays badge with "Mistral AI" as issuer

---

## 🔍 Troubleshooting

### "Image download failed"
Check image URL is publicly accessible:
```bash
curl -I "https://example.com/badge.png"
```

### "Credly can't verify signature"
- Verify email matches Credly account (lowercase!)
- Check `certs.djpai.dev/.well-known/did.json` is accessible
- Workflow logs show detailed errors

### "GitHub Pages not building"
- Verify `.nojekyll` file exists
- Check `gh-pages` branch is publishing source
- Custom domain set to `certs.djpai.dev`
- DNS might need 2-5 minutes to propagate
