# BAM — Local-only HTTPS preview

This preview runs the **real signed-in HTML interface and offline BAM gateway** on the same computer, but it is **not** a deployed service, Android app, or production environment. It deliberately does not provide public signup, production email verification, Google sign-in, actual social API connections, uploads, paid OpenAI generation, or post scheduling/publishing.

Do **not** expose this runner via Render, a public IP, port-forwarding, cloudflared/ngrok, a reverse proxy, Wi-Fi LAN interfaces or a remote tunnel. It is restricted to the same device's loopback address `127.0.0.1`. Do not use real customers' accounts, social secrets or business data in a preview database.

## Prerequisites

- Python 3.12 or later with the BAM repository checked out on the computer you are testing.
- An external location for all local preview secrets (such as `$HOME/.bam-preview`), **never inside the Git checkout or any synchronized backup folder**.
- A test email, password (12+ characters), business identifier and test business name.
- A local TLS certificate and private key for `localhost`. A self-signed certificate is only for local testing; your browser may not trust it until you explicitly configure local certificate trust.

## 1. Provision a single local test business

```sh
python bam_local_preview.py bootstrap \
  --db "$HOME/.bam-preview/bam.sqlite3" \
  --business-id example-shop \
  --display-name "Example Shop" \
  --industry retail \
  --topic "custom products"
```

The command prompts for the local test email, password and confirmation. The password is not an argument and is stored as a salted PBKDF2 hash. The local database is created privately and is never committed.

**Important:** For the offline preview only, the CLI treats the test email as verified without sending an email. This is not a real customer registration flow and must never be enabled for public visitors. The bootstrap refuses to replace an existing database.

## Optional: Add a second business under the same login

If you want to test BAM's multi-business switching, run the following on the **same local preview database** after the first owner is configured:

```sh
python bam_local_preview.py add-business \
  --db "$HOME/.bam-preview/bam.sqlite3" \
  --existing-business-id example-shop \
  --new-business-id example-service \
  --display-name "Example Service" \
  --industry services \
  --topic "facility care"
```

Enter the existing owner's test email and password when prompted. This does not create another BAM identity or change another user's membership. It requires an active owner role in the first preview business and refuses duplicate IDs. Once the HTTPS preview is running, choose between the two businesses in the signed-in header to test scoped data and token rotation.

## 2. Create a local-only TLS certificate

For a machine with OpenSSL installed:

```sh
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout "$HOME/.bam-preview/localhost-key.pem" \
  -out "$HOME/.bam-preview/localhost-cert.pem" \
  -days 7 -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

chmod 600 "$HOME/.bam-preview/localhost-key.pem"
```

Only use this certificate for localhost preview. Configure trust in your local browser deliberately rather than treating a browser certificate warning as proof of identity. Do not copy the private key to GitHub.

## 3. Run the preview on the same device

```sh
python bam_local_preview.py serve \
  --db "$HOME/.bam-preview/bam.sqlite3" \
  --cert "$HOME/.bam-preview/localhost-cert.pem" \
  --key "$HOME/.bam-preview/localhost-key.pem" \
  --port 8443 \
  --i-understand-local-only
```

Open `https://localhost:8443/` on **the same computer**. The browser navigates to BAM's authenticated HTML shell and can log in using the local test email, password and `example-shop` business ID. The app's script, stylesheet and logo assets are served on the same origin as the authenticated API.

Stop the preview in its terminal when finished. Do not open firewall rules or expose port 8443 over the network. On another physical phone, `localhost` refers to the phone itself and will **not** reach a preview server running on your computer.

## Safety limits

The preview uses a single-process WSGI server and local SQLite with a trusted, self-supplied TLS certificate. The full loopback TLS network flow (page, assets, password login, dashboard, held draft, private image receipt, pending media status, explicit discard, business switching and logout) has passed a separate Python-client smoke test in CI, along with unit and WSGI gateway tests. This does not replace real-browser/Android testing or constitute a production security assessment. Provider OAuth, real Google/email setup, password recovery, audited security events, public hosting, concurrent data migrations, trusted media storage/scanning and final publication permissions are outstanding.

If you need a preview from a different device or a publicly accessible test website, design and review an independently secured staging deployment instead of weakening the loopback guard.

## Optional private image receipt (advanced local testing)

Image-byte transfer is **disabled by default**. For an explicitly local pending-only test, include:

```sh
--pending-media-dir "$HOME/.bam-preview/pending-images"
```

on the `serve` command. The directory must be outside Git and private to your user. The backend accepts an image only after it has a valid business-scoped attachment preflight; the allowed formats are PNG, JPEG and WebP. File bytes are stored under opaque server IDs with private permissions.

**An image receipt is NOT a verified attachment, approved content item, or permission to publish.** The file remains quarantined and unavailable to social posting until a separate trusted malware/consent/media-validation and owner review pipeline exists. The signed-in Content Studio now offers a **capability-gated** image picker when this local-only feature is explicitly enabled and the user can edit that business's held drafts. After transfer, it displays **pending private review** status across refreshes, without showing any image bytes or verified-media status. Image transfer fails closed if the active BAM session changes. An editor can also discard a pending unverified image through a second explicit confirmation, then submit a replacement. The backend removes only that request/item's private pending bytes and metadata; **verified images, malware scanning, publishing approval, and remote upload are still unavailable**.

## Review preparation on the local signed-in interface

Open the **Approvals** card to view a read-only editorial readiness checklist from `GET /api/v1/review-readiness` within the local opt-in HTTPS test environment. It distinguishes missing required media, media not yet trusted/verified, postponed content, and content with all materials complete. All items still require TruthGuard and owner review; neither the checklist nor a saved calendar date approves, schedules, or publishes content. This route is authenticated by the server's active business session and rejects POST and client-supplied tenant IDs. Do not expose this offline gateway to the public Internet.

## Private editorial feedback (local HTTPS preview)

In the **Approvals** card, an owner or marketing manager may add or revise a business-private feedback note for a held draft. This calls the strict versioned `/api/v1/review-feedback` route and does **not** approve the draft. Content creators may read the same note in Content Studio, then revise their draft copy; any old note is marked stale. Content Studio status/channel/search filters affect only the current screen, without transmitting a search query or changing the database. All work remains unavailable in the public Internet because the local offline adapter is not a production server. Do not paste secrets or sensitive customer details into feedback.
