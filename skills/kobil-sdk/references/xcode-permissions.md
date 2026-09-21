# Remembering Xcode tool permissions

Xcode manages permission prompts independently of this MCP and skill. Importing
this package does not automatically approve tools. The verified Xcode 27
Permissions panel applies to all agents and all projects.

## One-time setup

1. On a KOBIL MCP permission prompt, open the arrow beside **Allow**.
2. Choose **Always Allow “mcp__kobilsdk__<tool>”…** for a tool you want to trust
   for future calls. Complete Xcode's confirmation if shown. Plain **Allow**
   is a one-time approval.
3. Review remembered rules at **Xcode → Settings → Intelligence → Agents →
   Permissions → Allowed Tools**. Remove a rule there to revoke it.
4. For recurring terminal commands, use **Allowed Commands → +**. Add the
   particular command you intend to approve. Build commands can execute project
   build scripts; their approval covers that work too.

Use the exact server/tool name displayed by your installation. New tools are
separate permissions and can prompt on first use. Administrative deletion and
credential changes have different effects from reads; choose permissions per tool.

## Integration constraints

The inspected UI permits adding commands and removing remembered tool rules;
new tool approvals are offered in the conversation. No documented plugin manifest
field for preapproving Xcode host tools was established. Do not advertise zero
prompts or silently change protected host settings. Claude Agent and Codex have
separate agent configuration; changing Codex approval_policy does not configure
Claude Agent or establish that Xcode host prompts are disabled.

When diagnosing repeated prompts, first check whether the exact tool is already
listed in Allowed Tools. Record the agent, Xcode version, tool name and observed
result, without credentials or backend response contents.

Source: [Apple: Extending and customizing agents](https://developer.apple.com/documentation/xcode/extending-and-customizing-agents).
Verified locally in Xcode 27 on 2026-09-21: Allow Once / Always Allow menu and
shared Allowed Commands / Allowed Tools panel. Automatic permission installation
is not implemented or verified.
