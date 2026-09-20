# Evidence Guide

## Evidence types

`SCREENSHOT, VIDEO, IMAGE, PUBLIC_POST, PUBLIC_COMMENT, PUBLIC_PROFILE, PUBLIC_URL, ARTICLE,
ARCHIVE, DOCUMENT, API_RESPONSE, METADATA` — the full set from `models/enums.py`. Every
evidence item has an `evidence_number` (`EV-NNNNNN`, generated from the highest existing
number + 1, not a row count — see the note in ARCHITECTURE.md/git history about why a
`COUNT(*)`-based generator is wrong once there are gaps in the sequence), a required
`source_url`, and a `collected_by`/`collected_at`.

## Two ways to register evidence

1. **File upload** — `POST /api/evidence` as `multipart/form-data` with a `file` field.
   Goes through `services/evidence_service.upload_evidence_file`:
   - Extension + declared MIME type both checked against an allowlist.
   - Size capped at `MAX_UPLOAD_MB`.
   - Stored under a **server-generated UUID filename** — the original filename is recorded
     as metadata (`original_filename`) but never used to build a filesystem path, so a
     path-traversal-style filename like `../../../../etc/passwd.png` cannot escape the
     storage directory (see SECURITY.md).
   - SHA-256 computed immediately from the uploaded bytes.
   - If that hash already exists on another evidence item, this one is marked `DUPLICATE`
     immediately — before any human review — with a note pointing at the original.
2. **URL reference** — omit `file`; the evidence item just records the source URL and a
   description, for cases where the operator is citing a public page/post by reference
   rather than uploading a captured file.

## Hashing

```python
hashlib.sha256(file_bytes).hexdigest()
```
exactly as the spec asks (`services/hash_service.sha256_bytes`), computed once at upload and
recorded both on the `Evidence` row and as an `evidence_hashes` row with `stage=ORIGINAL`.
That `ORIGINAL` row is never overwritten. If you later need a redacted/annotated copy for a
report attachment, the schema supports recording it as a separate `evidence_hashes` row with
`stage=WORKING` or `stage=ANNOTATED` — the original stays untouched and its hash stays the
one chain-of-custody events reference.

## Chain of custody

Every evidence item accumulates an append-only sequence of `ChainOfCustodyEvent` rows.
Actions actually recorded by this codebase: `CREATED` (URL-reference evidence),
`UPLOADED` + `HASHED` (file evidence, both written at upload time), `REVIEWED` or `VERIFIED`
(written by `POST /api/evidence/{id}/verify`, depending on whether integrity checks passed).
`REPORT_GENERATED` and `SUBMITTED` custody events from the original spec's example chain are
not currently written — evidence-to-report linkage is tracked via the report's
`body.evidence` list instead, not as additional custody events on the evidence item itself.
Each event records `previous_hash`/`new_hash` where relevant so a reviewer can see whether
the file's hash changed between recorded events (it shouldn't, for the original).

## Verification (`POST /api/evidence/{id}/verify`)

Does **not** re-fetch the third-party source (no automated re-scraping of a URL that might
have changed or gone offline since collection — that would itself be a form of unreviewed
automated web access). Instead it checks what's already on file:

- Is the recorded `source_url` a well-formed `http(s)://` URL? (Not HTTPS specifically is a
  warning, not a hard failure.)
- If a file was uploaded: does it still exist on disk, and does recomputing its SHA-256 match
  the recorded hash? A mismatch means possible corruption or tampering and the item is marked
  `FAILED`, not silently passed.

Passing all checks marks the item `VERIFIED` and appends a `VERIFIED` custody event; failing
any blocking check marks it `FAILED` and appends a `REVIEWED` event with the specific
problem(s) in `verification_notes`.

## Target/profile data minimization

`models/target.py` only has fields for what a normal, unauthenticated visitor to a profile
page can see: username, display name, profile URL, bio, public follower/following/post
counts, verification badge status. There is no field for anything requiring authentication
to view (private posts, DMs, non-public follower lists, email, phone). This is enforced by
the schema shape itself, not just a policy statement — there's nowhere to even put that data
if you wanted to.

## Immutability in practice

"Original evidence must never change" is enforced by: (1) the stored file is written once at
upload and no endpoint ever overwrites `stored_filename`'s contents; (2) the `ORIGINAL`
`evidence_hashes` row is written once and no code path updates it; (3) verification
recomputes and *compares against* the recorded hash rather than replacing it. As with the
audit log (see SECURITY.md), this is enforced by the absence of a mutation path in the
application layer, not a database-level write-once constraint — someone with direct
filesystem/database access could still alter it. If your threat model includes that, put the
evidence storage volume on write-once media or object storage with object-lock enabled.
