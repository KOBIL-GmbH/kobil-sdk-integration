# Changelog

## Unreleased (branch feature/activation-and-ios-tooling)

Additive on top of 0.3.3; no existing tool was renamed or removed. 34 MCP tools (21 new),
125 tests. Verified on a KOBIL development realm with an iPhone 15 Pro and MCSDK iOS
15.16.803.3089231: first activation, relaunch to login required, login and logout, for a
hand-built app and for an app built by Xcode's coding agent from the plug-in alone.

- Fix: `client_credentials` token requests now send the optional `oauth.scope`, without
  which the token carried no AST role.
- Connection file: optional `admin` block (IDP administration) and `oauth.scope`.
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

Known: the branch is based on 0.3.3 (`6736dc9`); merging onto the credential-provider work
on `main` needs the `admin` block and `oauth.scope` expressed as credential references
(two hunks in `backend.py`).

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
