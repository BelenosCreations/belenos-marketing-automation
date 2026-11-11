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

The preview uses a single-process WSGI server and local SQLite with a trusted, self-supplied TLS certificate. Its authentication and browser code is exercised by unit and gateway tests but does not constitute a production security assessment. Provider OAuth, real Google/email setup, password recovery, audited security events, public hosting, concurrent data migrations, trusted media storage/scanning and final publication permissions are outstanding.

If you need a preview from a different device or a publicly accessible test website, design and review an independently secured staging deployment instead of weakening the loopback guard.
