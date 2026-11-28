> **Historical migration record.** Superseded by the v2.2 upload and consolidation into `develop/v3`. Do not re-import this old snapshot over the current branch.

# v2.2 baseline migration — incomplete remote state

The original user-supplied ZIP SHA-256 is `1868195365f120fa271907dc848d83994cb29eec09a74ab3359964a016c34f2f`.
The original archive has 235 files; every Git blob was checked against its ZIP bytes.
A local Git bundle was built with these refs:

- v22: c9123186e6c43199b4a4db1ff28d6e210bbb2951 (235 files, byte-identical archive).
- alpha2: e536616a18bed0921af410992d5e2569b4ca5da7 (257 files, integrated development snapshot, not release-qualified).

Bundle SHA-256: `037cb338d19c4443c2115bef571b69477a483e6bd04b4f5f898bca6be130cffb`.

This commit restores original v2.2 paths from existing repository blobs and several original small files. The rest of the snapshot is still local. Direct Git access failed due to DNS; the connector cannot accept local bundle files. Do not mark release gate R01 complete. Do not change VERSION or merge to main until the full snapshot is imported and tests run.

Use the supplied import_neuroskin_snapshot.py and bundle on a network-enabled checkout of develop/v3. The script restores original blobs including binary/ignored files, preserves remote-only paths, and verifies index hashes before committing. Import v22 first, then alpha2. No force push. T3 remains optional.
