# Test v0.5.0 native integration

This change is released as `v0.5.0` from `develop`.
It is not installed by updating an unrelated release checkout. Keep the current
installation available for rollback and use a separate candidate directory.

```sh
git clone --branch v0.5.0 --depth 1 \
  https://github.com/KOBIL-GmbH/kobil-sdk-integration.git kobil-sdk-candidate
cd kobil-sdk-candidate
git rev-parse HEAD
uv sync --frozen --python 3.11
uv run --frozen kobil-sdk-mcp
```

Record the commit and stop this foreground server after checking startup. Configure
your MCP client to launch that same command with an absolute candidate directory.
Keep the existing `KOBIL_SDK_CONNECTION` provider/selector; do not put credentials
in the checkout. Point the agent to `skills/kobil-sdk/SKILL.md` in the same
candidate. Restart the MCP and start a fresh chat so cached tools/instructions
are not mixed with an older package. SDK archives remain separately supplied.

Ask the agent:

> Use only the KOBIL SDK MCP and its matching bundled skill for KOBIL integration
> knowledge. Use normal file, build, terminal and device tools to implement the app.
> Call sdk_service_catalog and sdk_knowledge_topics first. Build a fresh native
> app for my chosen Android or iOS target, using classic MCSDK 15.16. Follow the
> bundled integration handoff and all eight topic recipes. Use my selected backend
> environment and existing suitable app/version. Implement activation, returning
> login, native multi-step interaction, TMS and SDK log export. Record the topic
> checklists and original SDK error events. Ask when required deployment choices
> cannot be determined; do not invent a backend flow or report untested success.

Expected discovery: **179 tools**, including `sdk_knowledge_topics`,
`sdk_knowledge_get` and `sdk_integration_checklist`. Each retrieved topic identifies
`classic_mcsdk_kssidp`; examples include exact artifact/build evidence. Flutter
and other unsupported recipe families report a gap rather than substituting a
native recipe. This release's package version is 0.5.0, separate from SDK
15.16 and any older editor installation.

The complete acceptance list is in the
[native integration handoff](../skills/kobil-sdk/references/native-integration.md).
