# Source & Rights Policy / Kaynak ve Hak Politikası

CiciByte AI Media Factory records **where every piece of content came from and what rights you have to
it**. This page explains the rules the software enforces and the responsibilities that stay with you.

> This is not legal advice. You are responsible for the content you publish and for following the terms of
> every platform you collect from and publish to.

## Every item keeps its provenance

Each collected item stores: source and source type, canonical URL, title, author (when known), published
and fetched time, the raw and normalized text, a SHA-256 content hash, a revision counter, and its
**rights status** with a full history of who changed it, when and why.

The same content arriving through different links (tracking parameters, `old.reddit.com`, trailing slashes)
is stored once; when a source changes the text, the item is marked **updated** and its revision increases.

## Rights statuses

| Status | Meaning | Can it be published? |
|---|---|---|
| `unknown` | **Default.** You have not established any rights. | Only as an original work *inspired* by it (see below), never verbatim |
| `user_owned` | You wrote or own it. | Yes |
| `licensed` | You hold a licence that covers this use. | Yes, within the licence |
| `permission_granted` | The rights holder allowed this use. Record how in the note. | Yes, within the permission |
| `public_domain` | No copyright applies. | Yes |
| `restricted` | Must not be used. | No |

Changing a status is recorded in the item's rights history and in the audit log.

## Script modes

- **`inspired` (default):** the AI takes only the idea, theme and atmosphere and writes an **original** story
  or script. Long passages from the source are never copied; an overlap check sends suspicious scripts to
  manual review.
- **`adaptation`:** a retelling of the source. Allowed only when the item is `user_owned`, `licensed`,
  `permission_granted` or `public_domain`.

Nothing is ever published without a person approving it in the panel.

## Platform rules the software follows

- **Reddit:** posts belong to their authors. The default `reddit_rss` adapter reads Reddit's public feeds;
  the `reddit` adapter uses the official API with credentials you register (Settings → Source credentials).
  Reddit items start as `unknown`.
- **Web pages:** `robots.txt` is honoured, requests to the same host are spaced out (≥ 2 s), responses are
  capped at 5 MB, and private/internal network addresses are refused.
- **Wattpad and similar platforms:** **no scraping.** Import only stories you own or have permission for,
  through manual upload, and set the rights status accordingly.
- **Background clips, music and sound effects:** each file in the media library must carry a licence/origin
  note (e.g. Coverr, Mixkit, your own recording). Files without one are not used.

## Your responsibilities

- Set the correct rights status before choosing `adaptation`.
- Keep evidence of licences and permissions (the note field is for a reference, not the document itself).
- Respect each platform's terms of service and YouTube's policies on reused content, synthetic media
  disclosure and "made for kids".

---

Powered by [CiciByte Technology](https://cicibyte.com)
