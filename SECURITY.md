# Security / Güvenlik

## Reporting a vulnerability

Please report security problems privately through GitHub: **Security → Report a vulnerability** on
https://github.com/RealMrNovember/cicibyte-ai-media-factory. Do not open a public issue for them.
Include what you found, how to reproduce it and the version (Settings → Updates shows it). We aim to answer
within a week and to ship a fix as soon as it is verified; you will be credited unless you prefer not to be.

Only the latest version on `main` and the latest desktop release are supported.

## Security model

CiciByte AI Media Factory is a **single-owner, self-hosted** application.

- **No sign-in.** Whoever can reach the server's port controls the factory. Run it on a private network
  (Tailscale or your LAN) or behind a reverse proxy with its own authentication. Never expose the port to the
  internet (no port forwarding, no `tailscale funnel`). The installer binds to the Tailscale address or
  `127.0.0.1` by default.
- **Host check.** Requests must use a name listed in `MF_ALLOWED_HOSTS`, which blocks DNS-rebinding attacks
  from web pages you visit. Requests that change data must carry the `X-MF-Client` header, which a web page on
  another site cannot send without the server's consent (CSRF protection).
- **Secrets at rest.** AI provider keys, YouTube refresh tokens, the Instagram token and Reddit credentials are
  stored encrypted (Fernet, key derived from `MF_SECRET_KEY`). The API never returns them. Settings exports
  include them only when you set a password, encrypted with that password (PBKDF2-SHA256).
- **Logs.** Job logs and errors pass through a redactor that removes keys and tokens before they are stored.
- **Outgoing requests.** Source fetching refuses private, loopback, link-local and other internal addresses
  (SSRF protection), including after redirects; specific internal hosts can be allowed with
  `MF_FETCH_ALLOWLIST`.
- **Uploads.** File names are sanitised, types and sizes are checked, and files stay inside the data folder.
- **Updates.** The server only installs commits from this repository's `main` branch and rolls back a version
  that does not start healthy. The desktop app only installs installers from this repository's releases whose
  SHA-256 matches the published checksum.
- **Publishing.** Nothing is published without your approval unless you turn on automatic approval; videos
  that fail the quality, originality, sensitive-content or rights checks always wait for a person.

## Your responsibilities

- Keep `MF_SECRET_KEY` and your settings file private and backed up.
- Use your own API keys and OAuth apps, and revoke them if a machine is lost.
- Only publish content you have the rights to (see [docs/SOURCE_RIGHTS.md](docs/SOURCE_RIGHTS.md)).

---

Powered by [CiciByte Technology](https://cicibyte.com)
