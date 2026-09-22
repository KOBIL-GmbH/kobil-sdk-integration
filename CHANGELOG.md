## Unreleased — service interfaces

- Add typed IDP/AST operations and 41 explicit HTTP contracts covering all 45 inspected dashboard service routes.
- Add private request-payload files, token refresh, bounded device inventory and contract tests.
- Separate service transport from app-flow guidance; WLA skills and GettingStarted apps supply app behavior. No reverted journey-selection/provisioning recipes are imported.

# Changelog

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

## Audited service additions (unreleased)

- Add eight IDP dispatcher operations and explicit OIDC login-page fetch.
- Add activation-code generation/set, private AST token export, authentication testing and optional Grafana client correlation.
- Keep connection selection host-owned and app-flow selection explicit.
- Validate with 115 local tests and package build; live backend acceptance pending.

## Shared credentials (unreleased)

- Integrate native keystore, private file, environment and encrypted age references into AST and IDP authentication.
- Add scoped MCP credential status/import/delete and local setup CLI; preserve legacy profiles and OAuth scope.
- Keep original shared-credentials branch archived; no app-flow implementation imported.
