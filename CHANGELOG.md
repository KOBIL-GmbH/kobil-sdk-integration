# Changelog

## 0.7.1 — 2026-10-08

Xcode plug-in round (project-bound adapter, Xcode 27, iOS 27 simulator, akinci): an agent with only the plug-in built, activated, logged in and proved SignedJWT (SDK + issuer log) on a fresh SwiftUI app; the friction it hit became the fixes below. Tool count 198 (`sdk_runtime_info` is the one addition since 0.7.0). `sdk_backend_status` and `sdk_native_preflight` gained fields only.

### IDE adapters (Xcode plug-in measured 2026-10-08)

- Add an automated Xcode package acceptance runner that executes generated manifests, verifies runtime/knowledge identity and writes machine-readable results without claiming Xcode host qualification.
- Add read-only `sdk_runtime_info` with package version and source/knowledge fingerprints for detecting stale IDE registrations.

- Add project-bound IDE adapter preparation for native VS Code/Xcode plugins and Android Studio Streamable HTTP, with paired skill/reference documentation and explicit development or full-commit release selection.
- Add authenticated loopback HTTP using the MCP library, private token-file validation, Host/Origin checks and foreground process ownership. Require MCP library 1.30 or newer.
- Replace generic connection setup failures with redacted diagnostic categories while preserving modern and legacy profile fields.
- Add adapter preservation, real-process isolation, HTTP lifecycle/port collision and authentication regression tests. Actual IDE agent/build qualification remains pending.

### Onboarding and backend binding

- `sdk_backend_status` returns `hosts` (ast, idp, services), `idp_realm_base` and `tls_check_hosts` from the selected connection (hostnames and the realm base URL only, no credentials). Measured 2026-10-08: without them an agent guessed `/realms/<tenant>` (404) and could not run `sdk_tls_chain_check` for the AST host. SKILL.md step 2 names the authorization endpoint `<idp_realm_base>/protocol/openid-connect/auth`.
- login knowledge: OfflineLogin 802000007 "Failed to read signature key" with the measured simulator cause (LocalAuthentication -7, Face ID enrollment reset after an Xcode/simulator restart; re-enable enrollment, no re-activation needed). Guidance guard asserts it.

- `sdk_native_preflight`: new `warnings` list and per-binding `theme_warning` when a trusted-WebView client carries a plain theme (kobil-lite/keycloak/base); `POLICY['kstrustedwebview']['recommended_clients']` names the kobil-mobile themed copies. Measured 2026-10-08: an Xcode agent that took the BDDK clients showed the desktop-styled login page in the app. Native KSSIDP path unchanged.

- `sdk_onboarding_prepare` and the MCP startup hook return/skip with `connection_already_configured` when `KOBIL_SDK_CONNECTION` points to an existing file; previously a credential request was written into every bound project and an Xcode agent asked for credentials it already had (measured 2026-10-08, Xcode plug-in 0.7.0 dev).
- SKILL.md start-here step 0: `sdk_runtime_info` + `sdk_backend_status` before anything else; onboarding only on `CONNECTION_NOT_SELECTED`; stop when the bound project differs from the open project.

### TLS trust-asset gate

- `sdk_tls_chain_check` now also reports, per host, the leaf hostname match (subjectAltName only), validity of the served leaf and matched asset anchors with an `expiry_warning_days` window (default 14), and a simplified desktop path check that follows the KOBIL `trusted_certs.pem` procedure (the file alone must reach a self-signed root). New per-host `problems`/`warnings` and statuses `hostname_mismatch`, `expired`, `path_invalid`; mobile anchor coverage (`missing_anchors`) is unchanged and still stricter than a desktop client. Existing result fields are kept.
- `sdk_tls_chain_check(platform="ios"|"android")`: iOS (default) keeps the strict anchor rule; Android lets the desktop path decide and reports the strict gap as a warning (shared native OpenSSL validator per source review, not device-verified). Checked against the GettingStarted configurations: 33 of 34 reported gaps were Android-lenient cases.
- iOS: a missing self-signed variant of a device-tested cross-signed top (currently only `Root YR` signed by ISRG Root X1) is a warning instead of `missing_anchors`; an iPhone (iOS 26.7.1) and a simulator (iOS 27.0) loaded a real page with only ISRG Root X1 in the PEM, an X2-only PEM was still rejected (`reason=1`). Every other top, such as the akinci Root X2, keeps the strict rule. Not verified in the SDK's native validator or for other iOS versions.
- Tests: fixture leaf carries a subjectAltName and validity is relative to the real clock; new cases for hostname, wildcard, expiry, intermediate-only/leaf-only/CA-copy assets, forged signatures, malformed PEM, concatenated DER and the live fetch path against a loopback TLS server.

### Knowledge interrogation tests

- Expand blind questions to 46 scenarios with evaluator-only semantic criteria and reader-only comprehension/retrieval packets. Add answer-bound review validation and knowledge-discovery regressions.
- Inject uncertain IDP write failures to verify no retry and tighten minimal-call write counts.
- Add mixed-log correlation regressions; reject ambiguous SignedJWT evidence, report per-attempt outcomes, and avoid inferring a specific cause from generic CSR or exchange errors.

## 0.7.0 — 2026-10-05

- New read-only tool `sdk_log_markers(decrypted_log_path)`: reads the measured markers out of a decrypted MCSDK log - jwt-bearer grant correlated with the token-endpoint 200 (the SignedJWT proof), key kind from `isKeyInsideSecureHardware` / `GetKeystoreInfo` (software vs hardware), NOT_SUPPORTED attribution (missing bouncycastle dependency vs undetermined), explicit-TMS exchange refusals (wrong holder, missing scope, freshness). Golden fixtures from the 2026-10-02/05 device and emulator logs under tests/fixtures/sdk_logs/. Tool count 197.
- IDP tool catalog contract test (`tests/test_idp_tool_catalog.py` + route snapshot): every `sdk_idp_*` wrapper exercised once - validation-only exceptions, internal paths, at most one write per call, no secret echo. Line coverage 82 % -> 88 %.
- Guidance guard: `tests/test_guidance_guard.py` asserts measured facts in the served knowledge, references and SKILL.md and fails on internal identifiers (page ids, fixture users, transaction ids, device serials, personal paths, e-mail addresses, internal hostnames, customer names) in any shipped text. `tests/scenarios/skill_blindtest.json` + `scripts/skill_blindtest.py`: eleven measured customer scenarios (policy vs simulator, token holder after cold OfflineLogin, freshness 0, emulator SignedJWT report, NOT_SUPPORTED attribution, blank WebView, log roots, CLEAR_ALL, two security refusals) for a skill-only reader; lexical judge, local-model runner.
- New reference signing-policy.md and login knowledge: sign-key policy versus test target table (ENFORCE_* fails on emulator/simulator with the measured codes, ALLOW_VIRTUAL_SMART_CARD works with a software key), what each target can prove, NOT_SUPPORTED is not proof of missing hardware (bcpkix case), and the agent duty to resolve target/policy and run the deployment and explicit-TMS preflights before the user can fail on configuration.
- Explicit-auth TMS guidance (tms.md, tms.json, login.json) made deployment-neutral and extended with the 2026-10-05 measurements: token holder reverts to the enrollment client after every cold OfflineLogin (interactive token-client login needed in the current session, silent FAILED/0 otherwise), freshness 3600 vs 0 behaviour (516004035, no SDK step-up path), software-backed key under ALLOW_VIRTUAL_SMART_CARD verified on an emulator, customer login clients without the scope show 403/516004034 and must not be changed from a test run.
- Start-here journey in SKILL.md and new `sdk_knowledge_bundle` (setup/activation/login/tms/logs/diagnostics in one call) to replace ~10 sequential knowledge calls (round-4 O-01/O-05).
- `sdk_idp_login_page_fetch` creates its private output directory (0700) instead of failing; activation-code happy path and CREDENTIAL_NOT_FOUND meaning documented (O-02/O-03).
- `sdk_artifact_info` / sdk-delivery.md: locate AARs, xcframeworks, headers and javadoc inside a delivery without unzip/grep guessing (O-04).
- Login knowledge: BIOMETRIC prompts come with credential/key access, not activation; OfflineLogin grant order (cached access token, refresh token, then signed JWT) from source file; signed-JWT proof recipe ClearIamTokenCache(access+refresh) -> OfflineLogin -> claims, never CLEAR_ALL; the signed-JWT path exists only with maverick.jwtSignKeySecurityPolicy (ENFORCE_STRONG_HARDWARE / ENFORCE_HARDWARE / ALLOW_VIRTUAL_SMART_CARD) set before activation (O-09/O-10/O-12/O-19).
- Copy-ready trusted-WebView allowlist/redirect example per platform; a mismatch shows as a blank WebView without prompt (O-11).
- Log export: verified archive is the pass criterion, share delivery bounded; decrypt with the LoggingFramework version from the ks*.log header (O-13/O-14).
- Automated testing: write TEST_REPORT after every gate, keep heartbeats as children and stop them, budget parallel runs against usage limits; iOS reinstall/OS update can reset the SDK container (O-06/O-16/O-17/O-18).


- Explicit-auth TMS: record the documented AST contract and the three measured preconditions for the token client - optional client scope `tms`, token-holder identity, KOBIL mobile browser-flow override - with the failure signatures of each missing piece (403/516004034, not_allowed token holder with silent FAILED/0, CANNOT_ACQUIRE_TOKEN_DATA). Add read-only `sdk_tms_explicit_preflight` that checks a token client for all three via the IDP admin API. Measured end-to-end in internal validation (2026-10-01 physical device, 2026-10-05 emulator).

- Separate GettingStarted ordinary-TMS baseline from explicit-auth policy; require SDK status and backend proof instead of sample UI success.

- Add read-only TMS authorization diagnosis for requested versus issued transaction scope; document result-event errors, same-client user comparisons and independent timeout/cancellation tests.

- Add read-only deployment preflight for actual mc_config against explicit deployment mTLS and token-owner/scope metadata; mismatches block the integration gate without changing backend policy.
- Add built iOS artifact signing preflight for the selected customer team, embedded profile, application identifier, expiry and device eligibility, including legacy application prefixes.
- Require deployment/signing gates in bundled integration guidance; distinguish token-holder, explicit scope and freshness errors, preserve selected themed flows, and document native diagnostics when SDK errorCode is zero.
- Clarify WebView navigation and export/share lifecycle handling. Checks report their evidence limits and never claim runtime acceptance or physical biometric proof.

## 0.6.1 — 2026-09-29

- Fix sdk_tls_chain_check crashing on interpreters that do not export ssl.ENCODING_DER (bundled CPython 3.11): resolve the DER encoding constant with the _ssl fallback at import time; regression test added. Found in the v0.6.0 retest round (slug tls-chain-check-py311-ssl-encoding-der-crash); chain-comparison logic itself was verified correct against akinci (X1+X2 ok, X1-only reports missing ISRG Root X2).
- E08 completion: local build preflight now includes the ON-DEVICE trust state of the iOS signing team — a Developer App Certificate trust failure appears only at launch while install and codesign verify pass silently (VAL-35).

## 0.6.0 — 2026-09-29

Enhancements E01–E16 from the 2026-09-29 multiplatform validation round
(Android MCSDK 15.16.3088426, iOS MCSDK 15.16.803.3089231, Flutter delivery 549),
plus the environment-transfer work from the previous development line.

- E01: sdk_sftp_list reports the configured remote_root/requested path and that a scoped listing is not the account inventory; sdk_artifact_info classifies ZIP deliveries (android_native/ios_native/flutter) and flags missing mc_config/app_config templates before scaffolding.
- E02: release-qualified mc_config/app_config recipes with verified key structure and error semantics (800000133 category/tag, 800000015 app-config warning, 800000279 SignedJWT+mKex/SE rejection) and the iOS/Android authentication-mode matrix.
- E03: exact trusted WebView authorization contract — ASTCLIENTDATA fragments concatenate with NO separator, the SDK ASTCLIENTID (including the all-zero null ULID) is forwarded unchanged, one PKCE state/nonce/S256 pair per attempt, exact redirect validation with single code consumption, and mandatory backend fixture readback before enrollment retry.
- E04: trust anchors derive from the chains actually negotiated by mobile TLS clients (iOS builds to ISRG Root X2 while desktop sees X1 via the cross-sign); SDK Start trust and WebView pinning stay separate inputs and verification is never disabled.
- E05: error capture/redaction hardening — iOS logger qualified against the shipped binary (getLogSink()+setSeverityLevel fallback), invalid Dart inline (?i) RegExp flag documented, sanitizers must execute in tests and preserve numeric errorCode/type with sanitized descriptions.
- E06: evidence-based acceptance gates with separate scaffold/Start/activation/returning-login/TMS/log-export rows, two NAMED returning-login paths (OfflineLogin/SignedJWT token vs interactive trusted WebView), owner do-not-touch protocol for unattended TMS, and share-sheet log export that pre-declares the destination and exact owner tap sequence before opening the sheet and verifies the ZIP afterwards.
- E07: credential-output setup failures return metadata-only diagnostics distinguishing destination permissions/ownership/provider support, without credential values or plaintext fallback.
- E08: sdk_plan returns a local_build_preflight (complete NDK, compiler versions, iOS deployment target vs Xcode, signing/device readiness, disk space) and interrupted device runs are cleaned up by exact PID with .xcresult preserved and diagnostics.jsonl as the post-mortem channel.
- E09: per-device lease protocol for physical test runs (exclusive lease before interaction, second-runner refusal, explicit handoff, process check before steal/reuse) — documentation only, no lease helper tool.
- E10: sdk_tms_trigger freshness_seconds documents confirmation-time semantics and defaults to 3600 with a warning on unconfirmably low values (0 produced HTTP 403 wrapped as SDK 516004035 "A network error occurred"); sdk_tms_result maps the result endpoint's HTTP 412 to an explicit lowercase "pending" status instead of a backend error.
- E11: OWNER_CHANNEL.md live owner/worker coordination — the worker writes "AWAITING_OWNER: <exact action>" before every device-blocking step and polls for the owner reply, so blocking steps surface within seconds instead of via agent-turn boundaries.
- E12: new sdk_tls_chain_check tool fetches each host's actually-served TLS chain, reports per-certificate subject/issuer/SHA-256 and names MISSING anchors against the local PEM/DER trust asset before any device run (an X1-only asset against an X2-rooted serving reports missing X2); fetching never weakens any verification.
- E13: a blank WebView failure is impossible in reference integrations — onWebResourceError/onURLBlocked/TLS failures render a visible sanitized in-app diagnostic (numeric code + hint, no URLs or secrets), asserted by forced-trust-failure tests.
- E14: encrypted-file-logging capability matrix per SDK family × platform (classic 15.16 Android/iOS supported; shift 549 Flutter/Android not writing — open vendor question VAL-34; shift 549 Flutter/iOS supported, validated on device); acceptance runners mark known gaps EXPECTED-FAIL instead of probing.
- E15: workers use descriptive issue slugs only; the supervisor assigns central VAL-nn identifiers at reconciliation.
- E16: explicit authentication-mode decision gate before activation (enum no=0, biometric=1, password=2, pin=3; preferred biometric) — Android binds the mode at Keystore key creation, so a missing decision blocks with a prompt instead of a silent default; the warning also ships in the sdk_idp_activation_code_generate description.
- Preferred integration method recorded across recipes (user decision): trusted WebView enrollment and interactive login with SignedJWT token-based returning login (useTokenBasedLogin=true, SE-signed JWT OfflineLogin), protected by device biometrics; PIN/password/no-authentication remain documented alternatives, not defaults.
- Enforce stable project identity naming through sdk_age_project_identity, with collision-resistant project IDs and reuse of existing keys.
- Retrieve the receiver public age key with sdk_age_identity_public_key for a two-chat encrypted server handoff.
- Identify inaccessible age identities versus encrypted bundles without exposing secrets; document project-local deliveries and separate recipient identities.
- Transfer multiple AST/IDP server profiles and credentials in a single recipient-encrypted age bundle; import selected environments with recipient-local references.
- Isolate imported credentials under kobil-sdk/import/; reject collisions, preserve local services and report incomplete rollback without exposing secrets.
- Validate macOS Keychain round trips with disposable credentials. Windows native runtime validation remains pending.

Compatibility: 191 MCP tools. Behavior changes called out per version policy: sdk_tms_trigger freshness_seconds is now optional (default 3600) and warns on unconfirmably low values; sdk_tms_result returns status "pending" for the result endpoint's HTTP 412 instead of raising a backend error. The dependency lockfile now includes paramiko (previously missing, breaking `uv run` installs). MCP/plugin version 0.6.0 is separate from mobile SDK versions; SDK binaries and credentials remain separately supplied.

Validation: 245 tests, 3 skipped, green via `uv run python -m unittest discover -s tests` and the PYTHONPATH source path. Device evidence in recipes is scoped to the 2026-09-29 validation round (physical Android/iOS classic 15.16, Flutter Android delivery 549 including biometric activation, SignedJWT cold login and 4/4 TMS with backend readback); Flutter iOS acceptance passed in full (biometric activation, SignedJWT cold login, 4/4 TMS, encrypted log export verified); the shift-549 Android logging vendor question (VAL-34, sharpened by VAL-38: iOS writes logs, Android does not) remains open. The sdk_tls_chain_check live check against a deployment host is fixture-verified only in this package.

## 0.5.1 — 2026-09-22

- Add read-only sdk_native_preflight to verify required native clients and actual backend flow bindings; reject missing, substituted and SuperApp flows.
- Enforce BDDKEnrollment/BDDKLogin, token-based login, maverick and X-KOBIL-ASTUSERID in native KSSIDP guidance; distinguish KSTrustedWebView.
- Diagnose missing IAM status50 and require typed Swift callback result handling.
- Include GSA automated-testing knowledge from PR7. No new mobile SDK/device acceptance claim.

## 0.5.0 — 2026-09-22

- Ship 179 MCP tools, typed IDP/AST administration, 49 explicit HTTP contracts, activation-code generation and backend configuration delivery.
- Add native keystore/file/environment/age credential providers, encrypted environment storage and public-recipient transfers between machines. Native Windows acceptance remains pending.
- Bundle eight classic MCSDK/KSSIDP topics with 16 Kotlin/Swift examples, source hashes, acceptance checklists and backend-to-app handoff. No external WLA skill or GettingStarted checkout is required.
- Validate app-version registration, fresh activation and returning login on physical Android/iOS using MCSDK 15.16; correct explicit iOS IAM certificate-chain initialization.
- Return uncounted AST device collections with explicit incomplete-inventory metadata; reject inconsistent counted responses.

Compatibility: automatic journey selection/provisioning from the v0.4.0 development line is not included. Callers select deployment resources explicitly. Native SuperApp Login V2 is excluded. MCP/plugin version 0.5.0 is separate from mobile SDK versions. SDK binaries and credentials remain separately supplied.

Validation: 147 tests; wheel/stdio packaging checks; all 16 examples compile/link. Native successful-path evidence is scoped to Android15.16.3088426 and iOS15.16.803.3089231 with a nonproduction deployment and test policies. TMS, negative/multi-step cases, real log export and Flutter are not newly qualified by this release.

## 0.4.0

Tagged development snapshot for activation and iOS tooling. Superseded by the explicit service interfaces and bundled knowledge architecture in 0.5.0; migration requires tool discovery rather than assuming identical tool names.

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
