# Initial public snapshot

Prepared 12 November 2026 from the local development sources. Hardware evidence
was last recorded 10 October 2026; no fresh phone test was performed for publication.

Included: text sources beneath `port/` and `tests/`, top-level Python/shell tools,
and this documentation. Existing attribution and per-file licenses are preserved.

Excluded: `device-data/`, `build/`, `test-runs/`, `sources/`, `diagnostic/`, downloaded
SDKs/drivers/archives, compiled artifacts and Python caches. There is no imported
Git history, so old device data is not reachable through earlier commits.

Device serial and install-ID literals have been replaced by explicit placeholders.
Personal LAN addresses use documentation-only addresses. The original development
PIN has been removed from the public source. These substitutions affect only this
publication checkout; the local working port and phone have not been changed.

The public files are a development snapshot. Local scripts may still require
non-published inputs and refer to historical evidence. No binary release, installer,
firmware distribution or authentication-readiness claim accompanies this snapshot.

Publication checks: 47 synthetic fingerprint storage/worker/bridge tests passed
against this copy. Python syntax was checked for 197 files and shell syntax for
91 files. A staged-file scan checked excluded paths, known device identifiers
and credential patterns. These checks do not replace hardware validation or a
complete security and licensing review.
