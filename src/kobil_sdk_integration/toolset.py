"""Optional tool sets. KOBIL_SDK_TOOLSET=start exposes only the standard journey (about 40 tools, 40 KB);
the default is the full catalog.

Measured 2026-10-08: the tool list is NOT what stalls Xcode's chat. A simulated host receives about 33 KB of
stream data with the full list (14 KB init message) and the permission round trip completes in under a
second when answered; the stall sits in Xcode's own approval path. The start set is kept as an option for hosts
that limit the number of tools. The set is the union of the skill's start-here order and every tool the
validated simulator journey used.
"""
import asyncio

START = frozenset("""
sdk_runtime_info sdk_backend_status sdk_service_catalog sdk_plan sdk_targets
sdk_knowledge_bundle sdk_knowledge_topics sdk_knowledge_get
sdk_artifact_info sdk_sftp_list sdk_config_write
sdk_native_preflight sdk_deployment_preflight sdk_tls_chain_check sdk_ios_signing_preflight sdk_tms_explicit_preflight
sdk_app_list sdk_app_versions
sdk_idp_user_search sdk_idp_user_get sdk_idp_user_create sdk_idp_user_password_set
sdk_idp_activation_code_generate sdk_idp_activation_code_set sdk_idp_user_credentials_list
sdk_idp_client_list sdk_idp_login_page_fetch sdk_idp_realm_get sdk_idp_server_info
sdk_idp_sessions_list sdk_idp_events_list sdk_idp_bruteforce_get
sdk_ast_device_list sdk_ast_device_get
sdk_tms_trigger sdk_tms_status sdk_tms_result sdk_tms_cancel
sdk_log_markers sdk_onboarding_prepare sdk_environment_select
""".split())


def apply(mcp, mode):
    """Reduce the registered tools to the start set unless mode is 'full'."""
    if mode == 'full':
        return 0
    if mode != 'start':
        raise ValueError("KOBIL_SDK_TOOLSET must be 'start' or 'full'")
    removed = 0
    for tool in asyncio.run(mcp.list_tools()):
        if tool.name not in START:
            mcp.remove_tool(tool.name)
            removed += 1
    return removed
