"""Bundled SDK knowledge with explicit source, artifact and runtime limits."""
import json
from importlib.resources import files
from .native_policy import POLICY

TOPICS = ("setup", "lifecycle", "activation", "login", "multi_step", "tms", "diagnostics", "logs", "automated_testing")

FLUTTER_TOPICS = ("flutter_webview",)

def get_topic(topic, platform, sdk_family="shift", sdk_version=None):
    if topic not in TOPICS + FLUTTER_TOPICS:
        raise ValueError("Unknown topic; use sdk_knowledge_topics")
    if sdk_family != "shift" or not (
        (platform in ("android", "ios") and topic in TOPICS) or
        (platform in ("flutter_android", "flutter_ios") and topic in FLUTTER_TOPICS)
    ):
        return {
            "status": "knowledge_gap", "topic": topic, "platform": platform,
            "sdk_family": sdk_family,
            "reason": "Select a supported topic/target pair: native android/ios or flutter_webview "
                      "with flutter_android/flutter_ios. No SDK-family substitution.",
        }
    resource = files("kobil_sdk_integration").joinpath("knowledge", topic + ".json")
    data = json.loads(resource.read_text(encoding="utf-8"))
    return {
        "status": "source_reviewed_unqualified", "topic": topic, "title": data["title"],
        "platform": platform, "sdk_family": sdk_family,
        "requested_mobile_sdk_version": sdk_version,
        "version_verified": False, "qualification": data["qualification"],
        "prerequisites": data["prerequisites"], "sequence": data["sequence"],
        "expected_result": data["expected_result"], "failure_handling": data["failure_handling"],
        "platform_notes": data["platform_notes"][platform], "example": data["examples"][platform],
        "checklist": data["checklist"], "source_evidence": data["source_evidence"][platform],
        "external_source_access_required": False,
        "integration_generation": data["integration_generation"],
        "backend_tools": data["backend_tools"],
        "native_integration_policy": POLICY,
        "required_preflight": "sdk_native_preflight",
        "runtime_acceptance": data.get("runtime_acceptance", {}).get(platform),
    }


def register(mcp):
    @mcp.tool()
    def sdk_knowledge_topics(platform: str | None = None, sdk_family: str = "shift") -> dict:
        """List bundled native and Flutter mobile Shift topics. Unsupported targets report a gap.

        App-source revisions are not mobile SDK versions. Source review and individual
        example checks do not certify complete recipes or live backend flows.
        """
        if sdk_family != "shift" or platform not in (None, "android", "ios", "flutter_android", "flutter_ios"):
            return {"status": "knowledge_gap", "topics": [],
                    "platform": platform, "sdk_family": sdk_family}
        return {
            "status": "source_reviewed_unqualified", "platforms": ["android", "ios", "flutter_android", "flutter_ios"],
            "sdk_family": "shift", "mobile_sdk_versions_verified": [],
            "topics": [{"id": t,
                        "title": get_topic(t, "flutter_android" if t in FLUTTER_TOPICS else "android")["title"],
                        "platforms": ["flutter_android", "flutter_ios"] if t in FLUTTER_TOPICS else ["android", "ios"]}
                       for t in (TOPICS + FLUTTER_TOPICS if platform is None else
                                 FLUTTER_TOPICS if platform in ("flutter_android", "flutter_ios") else TOPICS)],
        }

    @mcp.tool()
    def sdk_knowledge_get(topic: str, platform: str, sdk_family: str = "shift",
                          sdk_version: str | None = None) -> dict:
        """Retrieve a bundled recipe, platform example, failure handling and checks.

        No WLA/GettingStarted checkout is required. Inspect example validation scope:
        illustrative snippets, compiler checks and synthetic device tests are distinct
        from live flow acceptance. Never infer mobile SDK compatibility from the MCP
        package version or silently choose a backend flow.
        """
        return get_topic(topic, platform, sdk_family, sdk_version)

    @mcp.tool()
    def sdk_integration_checklist(topic: str, platform: str, sdk_family: str = "shift",
                                  sdk_version: str | None = None) -> dict:
        """Return recipe acceptance checks, each initially not_run.

        This tool does not inspect an app or certify compatibility. Record build,
        device and live backend evidence separately.
        """
        data = get_topic(topic, platform, sdk_family, sdk_version)
        if data["status"] == "knowledge_gap":
            return data
        return {
            "topic": topic, "platform": platform, "sdk_family": sdk_family,
            "requested_mobile_sdk_version": sdk_version, "version_verified": False,
            "checks": [{"id": f"{topic}-{i + 1}", "description": check, "status": "not_run"}
                       for i, check in enumerate(data["checklist"])],
        }
