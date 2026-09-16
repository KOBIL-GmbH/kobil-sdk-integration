# Changelog

## Unreleased — portable credentials (0.4.0 development)

- Add version-2 credential references with native OS keyring, environment and
  explicit age-file providers; retain legacy authentication profiles.
- Add local hidden-input setup, sanitized probes, exact-account checks and
  reference-only migration; no secret-returning MCP tools.
- Add editor adapter support behind the release capability gate. Current editor
  installers continue to pin v0.3.3 and reject v2 until a new release is pinned.
- Native macOS and age tests passed with disposable credentials. Windows/Linux,
  live backend and editor enrollment validation remain pending. No release cut.

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
