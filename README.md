# KOBIL SDK Integration

A single-purpose skill and MCP for integrating KOBIL SDK features into existing
or fresh apps. SDK binaries are provided separately by the customer or an
authorized artifact source.

## Target scope

- Kotlin on Android and Swift on iOS.
- Flutter/Dart on **Android, iOS, Windows and macOS**.
- All public SDK features, with support and verification tracked per SDK release,
  wrapper version and target platform. Activation/login is the first milestone.
- Optional provider modules selected from the customer's workflow, including
  TeamCity, Updraft, TestFlight, Grafana, device diagnostics and testing.

## Current state

Implemented: a runnable MCP for targets, conditional dependency planning, local
SDK artifact hashes, AST app/version creation and reuse, and backend-signed SDK
configuration delivery to a private file. Customer connections are configured
at runtime. See [backend setup](docs/backend.md).

Pending: live deployment verification, SSMS and optional provider adapters,
automatic module installation, complete SDK feature recipes and end-to-end
platform validation. The AST module includes backend tools; other module
declarations remain extension contracts. No SDK binaries or internal support
history are included.

## Run

With Python 3.11+ and uv installed, from the repository root:

```sh
uv sync
uv run kobil-sdk-mcp
```

The server uses MCP over standard input/output. The plugin manifest and `.mcp.json`
register that command relative to the plugin root. A generic MCP client can use
`uv run --directory /path/to/checkout kobil-sdk-mcp`. The skill is in
`skills/kobil-sdk/SKILL.md` and can also be loaded independently.

Tools:

| Tool | Purpose |
|---|---|
| sdk_targets | List the integration targets and verification state |
| sdk_plan | Resolve required modules, optional offers and capability/platform gaps |
| sdk_artifact_info | Inspect one customer-supplied binary/archive; return size/hash only |
| sdk_backend_status | Validate local connection configuration without exposing credentials |
| sdk_app_ensure | Reuse or create a configured tenant's AST app |
| sdk_app_version_ensure | Reuse or create an AST app version with explicit registration/integrity settings |
| sdk_config_write | Request signed SDK configuration and write a new private JWT file |

Example `sdk_plan` arguments:

```json
{
  "profile": {
    "framework": "flutter",
    "targets": ["android", "ios", "windows", "macos"],
    "backend": "ast-shift",
    "artifact_source": "local",
    "distribution": ["updraft", "testflight"],
    "observability": ["grafana"]
  },
  "capabilities": ["observability"]
}
```

Grafana becomes a selected dependency for observability. Updraft and TestFlight
remain optional offers until distribution is requested. Neither a module choice
nor an artifact hash proves SDK compatibility or authorizes an external action.

## SDK artifacts and configuration

Supply SDKs from a local directory outside this repository or an approved
artifact provider. Record exact versions, native architectures and checksums in
the app's integration record. Do not assume a Dart wrapper includes all native
libraries or that a filename proves version compatibility.

Backend tools use customer-configured endpoints and keep credentials
inside the server runtime. No provider account or backend connection is
preconfigured. Only connect services needed for the requested capability.

## Validation

```sh
uv run python -m unittest discover -s tests -v
```

The tests do not contact customer services or validate native SDK activation.
