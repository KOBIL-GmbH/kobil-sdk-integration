# SDK delivery through customer SFTP access

Customers generally receive SDK binaries through a separately provisioned SFTP
account. This is an artifact delivery channel, independent of AST/IDP backend
credentials. The SDK binaries remain outside this repository.

## Connection and download workflow

1. Resolve the customer-provided hostname, port (normally 22), account and
   approved remote release path. Do not hardcode a shared account, endpoint,
   password or internal path in the skill. An HTTP link in an access email does
   not change the transport: connect with SFTP over SSH, not HTTP or FTP.
2. Use an approved SFTP client with credentials supplied through a secure
   credential store or interactive authentication. Never place passwords in
   command arguments, scripts, planning files, manifests, logs or Git history.
   Do not copy credentials from chat into repository configuration.
3. Verify the SSH host key using a trusted fingerprint or already verified
   known_hosts entry. Do not disable host-key verification. If the connection
   cannot be authenticated or verified, report that precise blocker.
4. List only the authorized release directory. Select the intended SDK family,
   version, native/wrapper combination and Android/iOS architecture. Ask for
   a missing release/path decision rather than silently picking the newest file.
5. Download the selected artifacts to private local storage. Preserve the
   delivery layout and accompanying release notes, compatibility information
   and checksums/signatures where supplied. Do not modify remote content.
6. Inspect the downloaded artifacts with sdk_artifact_info. Compare against
   trusted supplied checksums/signatures where available; a locally calculated
   checksum alone does not prove authenticity. Record non-secret release and
   compatibility evidence in the app integration record.

SFTP is a documented delivery workflow, not an implemented download capability
of the SDK MCP. Use an available approved SFTP client/adapter; do not claim that
sdk_artifact_info downloads artifacts or that receiving account details proves
connectivity, directory access or compatibility. Track connection, download,
artifact inspection, build and runtime verification as separate checkpoints.

## Review the release before integration

Read both CHANGELOG and platform README, plus component/version metadata inside
the downloaded package. Record breaking changes, minimum API requirements,
commercial OS support, build toolchain, backend requirements, compatibility,
known issues and regression tests needed by the requested feature. Do not treat
minimum API level and commercial OS support as equivalent. Cross-check a
changelog claiming no known issues against the README's known-issues section.

A standalone wrapper directory can lag behind the wrapper bundled in an MCSDK
release. Prefer the documented release combination; never replace the bundled
wrapper with a separately downloaded one solely because its directory looks
current. A missing Flutter delivery is an access/artifact gap, not evidence that
Flutter is unsupported. Record missing checksums explicitly; ZIP CRC validation
and a local hash do not replace a supplier integrity manifest.

See [15.16 release review](release-review-15.16.md) for a completed download and
source-review checkpoint. Download verification does not establish runtime
compatibility or authorize upgrading existing apps.
