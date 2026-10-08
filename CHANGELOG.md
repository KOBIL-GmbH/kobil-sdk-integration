# Changelog

## 0.4.2 — 2026-09-28

Additive; no tool renamed or removed. 41 MCP tools.

- New tool `sdk_api_lookup`: does the delivered iOS SDK have a class, event, method or
  constant? It searches the installed release's headers for one identifier and, for each class
  declared there, reports whether the binary exports it (`xcrun nm`). Checked on MCSDK
  15.16.803: `KSMClearIamTokenCacheEvent` present, `KsHttpMultiPart` declared but missing from
  the binary, `TransactionEndEvent` (official docs) absent, `KSMTransactionFinishedEvent` present.
  A partial name says what it matched and that a match proves no feature ("Chat" finds only
  chat status events; the iOS SDK has no chat send API).
  Swift classes (`SWIFT_CLASS("_TtC…")` in the generated header) count as present when the
  binary exports their Swift symbols; Swift code links to those, not to an Objective-C class
  symbol. Across the four 15.16 frameworks 205 classes are checked and exactly the 12 known ones
  are missing (`KsHttpMultiPart` and the 11 mute events).
- `sdk_official_docs_search` also searches the plugin's guides. Each result has `kind`
  `official` (with its source URL) or `guide`; new `scope` parameter (`all`, `official`,
  `guides`). Headings and the overview rank first. Before, "chat" found only push categories in
  the official pages and missed the guide's device finding that the iOS SDK cannot send chat.
- SKILL.md: SDK questions are answered through `sdk_docs` overview, the search and
  `sdk_api_lookup`, naming the source of each part.

## 0.4.1 — 2026-09-28

Additive; no tool renamed or removed. 40 MCP tools.

- iOS references build without warnings in a new Xcode 26 app. With approachable concurrency in
  Swift 5 mode, `SdkStatusMonitor.swift:46` and `TransactionCenter.swift:439` warned "reference
  to captured var 'self' in concurrently-executing code" (an error in Swift 6), and
  `DeviceSecurityView.swift:37` warned about a main-actor call from a nonisolated context. The
  `Task` closures now capture `[weak self]` themselves, and the state name is mapped in a closure.
- `refcheck` compiles with every flag approachable concurrency sets in Swift 5 mode
  (`InferSendableFromCaptures`, `GlobalActorIsolatedTypesUsability`,
  `DisableOutwardActorInference`); without them it passed the three warnings above. All three
  variants, Swift 5 and 6, Debug and Release: 0 errors, 0 warnings.
- `DocumentsView`: the row's date no longer gets cut off ("Sep 28, 2…"). The sender shortens
  instead, and the date leaves out the year.
- signing.md: the wiring that turns an accepted signature request into a document shows an alert
  when it fails, instead of discarding the error with `try?`.

Also since 0.4.0:

- The official KOBIL MCSDK documentation for Shift Lite - IdpSdk and the MCSDK introduction
  (87 pages from developer.kobil.com, 2026-09-28) ships in `skills/kobil-sdk/references/official/`,
  each page with its source URL. New tool `sdk_official_docs_search`; `sdk_docs` serves the index
  as `official` and each page as `official/<page>`. The index lists where the delivered iOS 15.16
  headers differ from the documentation. `scripts/fetch_official_docs.py` refreshes the copy.
- iOS reference logout (all three variants) clears the IAM token cache with
  `KSMClearIamTokenCacheEvent` before `KSMRestartEvent`, as the official Logout page requires for
  Shift Lite; before, a restart alone could let the SDK log the user in again from cached tokens.
  Compiled in every variant; not yet run on a device.
- New `ios/platform/PushRegistration.swift`: APNs registration through a `UIApplicationDelegateAdaptor`
  and `.sendsPushToken(to:)`, which sends `KSMSetPushTokenEvent` after every successful login
  (official Push Token page). Compiled in every variant; push delivery not yet run on a device.
- sdk-features.md: push wiring, app-side push localization, and when to use offline login
  ("Stay Logged In"); the reference sessions deliberately do not call it automatically.
- Guide corrections against the official documentation: iOS 15.16 has no PIN authentication mode
  and `jwtSignKeySecurityPolicy` is not tied to one (SKILL.md); IdpSdk client IDs are per realm and
  the public defaults are `KssIdpEnrollment` / `KssIdpLogin` (login-standards.md); the iOS
  delivery exposes `KssIdp` where the docs describe `IdpSdkService` (ios/README.md).

- `scripts/build_plugin.py` (in the source repository): one self-contained plugin folder
  (skills, docs, MCP code, launcher, connection, Keychain map, setup script) built from an
  allowlist, plus a hand-over zip.
- Plugin folder installs in every host, not just Copilot: the one-plugin marketplace manifest is
  written to `.claude-plugin/marketplace.json` as well as `.github/plugin/marketplace.json`.
  Claude Code reads the first, Codex reads Claude's path, Copilot reads the second. Xcode also
  reads the marketplace entry (its description) and rewrites both `plugin.json` files for its
  own Claude and Codex agents. Without the `.claude-plugin` copy `claude plugin marketplace add
  <folder>` failed with
  "Marketplace file not found" and Codex with "marketplace root does not contain a supported
  manifest".
- The Python environment lives in `~/.kobil-sdk/venvs/<hash of the folder path>`, not in a
  `.venv` inside the folder, so the folder Xcode copies holds nothing specific to one Mac (the
  old `.venv` was 32 MB, 1 349 files, linked to the builder's Python). `setup.sh` removes an
  old `.venv`. Bytecode goes to `~/.kobil-sdk/pycache`. Launcher and `setup.sh` also work when
  the host passes no `HOME`.
- `.codex-plugin/plugin.json` is named `kobil-sdk`, matching `.claude-plugin/plugin.json` and the
  marketplace entry. Codex refused the old `kobil-sdk-integration` with "plugin.json name does
  not match marketplace plugin name". The Python distribution keeps its own name.
- Launcher and `setup.sh` call `/usr/bin/security` by absolute path, so reading the Keychain no
  longer depends on the PATH the host happens to pass. With PATH unset `/bin/sh` falls back to a
  default that includes `/usr/bin`, so a bare `security` worked; a host that sets a PATH without
  `/usr/bin` would have made every entry look missing.
- `INSTALL.md` covers Claude Code and Codex CLI, and says to run `./setup.sh` before any host
  that copies the folder: Codex does not expand `${CLAUDE_PLUGIN_ROOT}` and cannot start a server
  whose command still contains it, while Claude Code resolves it to the plugin's own folder.
  Moving the folder needs a `setup.sh` re-run **and** a fresh Xcode import, because Xcode's copy
  keeps the launcher's old absolute path.
- Self-contained plugin: `tests/test_self_contained.py` (in the source repository) fails on home-folder paths, assistant
  memory, broken or outside links, unbundled skills, hex colours outside the theme, image
  assets the plugin does not ship and previews outside `#if DEBUG`; a clean-room test runs the
  MCP from a bare copy with an empty home folder.
- `kobil-sdk-refcheck`: type-checks every iOS variant with the feature folders in Swift 5 and
  6, Debug and Release. Fixes it found: Sendable handover in `SdkFeatureRequests.swift`,
  `nonisolated` event receiver and signature shape, previews that broke Release builds.
- Wallet: `references/wallet.md` and `references/ios/wallet/` (saved cards without number or
  security code, Keychain per user, "Pay with" on the approval sheet).
- Payment data contract: `amount`, `currency`, `merchant` read by `TransactionCenter`;
  documented in tms.md. Approval sheet Done button follows the theme in dark mode.
- `sdk_tms_test_sequence` and `sdk_tms_test_sequence_status`: message, signature and payment
  requests one after another.
- `sdk_ios_project_integrate` sets iPhone/iPad-only destinations and optional
  `usage_descriptions` (Face ID, camera, photo library), and warns that Xcode reloads.
- Theme: text word mark and SF Symbol shield instead of image assets.
- `ios-visual-check` skill bundled with `compare.swift` (per-cell difference and side-by-side
  sheet); no references outside the plugin.
- Signing: wiring for accepted signature requests to the Sign tab; the Swift 6-only claim
  corrected. ios/README: debug-framework warning (hardening alert, plaintext logs).

- KOBIL's official native login standards: `kssidp` (current) and `bddk` (deprecated, removal
  planned for IDP 6.0). New read-only `sdk_login_standard_check` compares a realm's clients,
  flow bindings, theme, official step order and first-activation step settings with the
  standard. `sdk_idp_journeys` tags official clients with `login_standard`.
- `sdk_activation_password_set(temporary=True)` issues the temporary password the kssidp
  enrollment asks for.
- Skill: `references/login-standards.md`, the official KSSIDP flow exports in
  `references/flows/`, and the device-verified iOS login-standards variant in
  `references/ios/login-standards/` (three-page enrollment runner, plain error messages).

## 0.4.0 — 2026-09-17

Additive on top of 0.3.3; no existing tool was renamed or removed. 36 MCP tools (23 new),
143 tests. Verified on a KOBIL development realm with an iPhone 15 Pro and MCSDK iOS
15.16.803.3089231: first activation, relaunch to login required, login and logout, for a
hand-built app and for an app built by Xcode's coding agent from the plug-in alone.

- Fix: `client_credentials` token requests now send the optional `oauth.scope`, without
  which the token carried no AST role.
- Connection file: optional `admin` block (IDP administration) and `oauth.scope`.
- TMS: `sdk_display_message_send` and `sdk_tms_scope_ensure` (explicit-authentication scope).
- Discovery: `sdk_docs`, `sdk_platforms`, `sdk_backend_verify`, `sdk_idp_clients`,
  `sdk_idp_journeys` (classifies a realm's clients by the journey their flow runs;
  minimal disclosure, optional client-id list).
- Activation journey: `sdk_activation_flow_ensure` (the device-verified four-step flow by
  default, per-occurrence step settings), `sdk_activation_flow_describe`,
  `sdk_activation_step_config`, `sdk_activation_client_ensure`, `sdk_idp_theme_check`.
- Test users: `sdk_activation_user_ensure`, `sdk_activation_password_set`,
  `sdk_activation_code_set`, `sdk_activation_user_status`. Codes and passwords are
  generated in the server and returned once, never accepted as arguments.
- App-side files: `sdk_trusted_certificate_write` (root of the IDP host's verified chain,
  checked against every backend host), `sdk_mc_config` with `output_path`.
- SDK delivery and Xcode: `sdk_artifacts_import`, `sdk_artifacts_install`,
  `sdk_artifacts_list`, `sdk_artifacts_notes` (checksum-verified local store of delivered
  zips, release notes served from it; nothing downloaded), `sdk_ios_project_integrate`
  (four XCFrameworks as Embed & Sign, bridging header, version and deployment target on
  every target; verified by a headless build of a fresh Xcode 27 project).
- `sdk_app_get` reports the app's categories, or the tenant's category values in use.
- Skill: `references/activation-login-findings.md` (the IDP defects met and the
  `acr_values=1` bypass), `references/ios/` (a customer-neutral copy of the verified Swift
  integration with a setup README), rules on device input, credentials in files, device
  state and realm-specific client names.
- Docs: `docs/backend.md` extended for all of the above.

Known limits:

- The iOS reference always sends `acr_values=1`. Its verification notes report a
  missing `amr` claim and HTTP 403 on signing-key upload; activation/login results
  do not establish signing or TMS readiness for this reference.
- Installing a replacement archive under an existing SDK version can remove the
  previous installation before replacement validation completes.
- Repeated Xcode integration does not repair missing frameworks or apply version
  changes once its project references exist.
- Reusing an IDP client does not validate or complete a missing AST client scope.
- The user-setup workflow recommends setting a password even when reusing an
  existing user; that operation replaces the user's current permanent password.
- Generated test-user passwords and activation codes are returned in MCP results.
- VS Code/Xcode installers and shared credential-provider changes are maintained
  separately and are not included in this release.
- Use the full Git checkout for skills and Swift references. The Python package
  does not bundle these files; `sdk_docs` does not expose nested Swift sources.

## 0.3.3

First tagged GitHub release. Previous package versions existed only in development history.

- Document fixed-version installations for the MCP and skill from one Git tag.
- Use the committed uv lockfile for release installations.
- Define coordinated versioning, explicit upgrades and rollback.
- Separate installation paths from backend connection and secret-manager setup.

No public tool contract changes from 0.3.2. Includes 13 MCP tools for integration
planning, artifact inspection, AST app/version/configuration and foreground TMS.
Native Android/iOS activation, returning login and selected foreground TMS flows
have prior version-scoped evidence; complete SDK coverage and Flutter runtime
verification remain pending. SDK binaries and credentials are not distributed here.
