# Changelog

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
