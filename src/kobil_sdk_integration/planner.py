"""Resolve customer-selected module contracts without executing providers."""
from importlib.resources import files
import json

# Customer app targets; desktop SDK availability is outside this product scope.
TARGETS = {"android", "ios"}
FRAMEWORKS = {"kotlin": {"android"}, "swift": {"ios"}, "flutter": TARGETS}


def catalog():
    return json.loads(files("kobil_sdk_integration").joinpath("modules.json").read_text())


def plan(profile: dict, capabilities: list[str]) -> dict:
    data = catalog()
    groups = data["provider_groups"]
    if not isinstance(profile, dict) or set(profile) - ({"framework", "targets", "backend", "artifact_source"} | set(groups)):
        raise ValueError("Invalid profile fields; credentials do not belong in the profile")
    framework = profile.get("framework")
    if not isinstance(framework, str) or framework not in FRAMEWORKS:
        raise ValueError("Choose kotlin, swift or flutter")
    targets = profile.get("targets")
    if not isinstance(targets, list) or not targets or any(not isinstance(t, str) or t not in FRAMEWORKS[framework] for t in targets):
        raise ValueError("Choose valid operating-system targets for the framework")
    for field in ("backend", "artifact_source"):
        if field in profile and not isinstance(profile[field], str):
            raise ValueError("Backend and artifact source must be names")
    for field in groups:
        values = profile.get(field, [])
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            raise ValueError("Provider selections must be lists of names")
    known_capabilities = {g["capability"] for g in groups.values()}
    if not isinstance(capabilities, list) or any(not isinstance(c, str) or c not in known_capabilities for c in capabilities):
        raise ValueError("Unknown requested capability")
    required, offered, gaps = [], [], []
    for module in data["modules"]:
        matches = True
        for key, value in module["when"].items():
            if key.endswith("_contains"):
                matches &= value in profile.get(key[:-9], [])
            else:
                matches &= profile.get(key) == value
        if not matches:
            continue
        entry = {k: module[k] for k in ("id", "dependency", "status")}
        if "capability" in module:
            entry["capability"] = module["capability"]
        if "targets" in module:
            entry["applicable_targets"] = sorted(set(targets) & set(module["targets"]))
            if not entry["applicable_targets"]:
                gaps.append({"module": module["id"], "reason": "No declared coverage for selected targets"})
                continue
        if module["mode"] == "required" or module.get("capability") in capabilities:
            required.append(entry)
        else:
            offered.append(entry)
    if profile.get("backend") not in {"ast-shift", "ssms"}:
        gaps.append({"capability": "backend", "reason": "Select or implement a backend adapter"})
    if profile.get("artifact_source") not in {"local", "teamcity"}:
        gaps.append({"capability": "artifacts", "reason": "Select or implement an artifact provider"})
    for field, group in groups.items():
        capability = group["capability"]
        selected = profile.get(field, [])
        known = {m["when"][field + "_contains"] for m in data["modules"] if field + "_contains" in m["when"]}
        for value in sorted(set(selected) - known):
            gaps.append({"capability": capability, "provider": value, "reason": "Provider adapter not declared"})
        if capability not in capabilities:
            continue
        if group["per_target"]:
            covered = {t for m in required if m.get("capability") == capability for t in m.get("applicable_targets", [])}
            for target in sorted(set(targets) - covered):
                gaps.append({"capability": capability, "target": target, "reason": "No selected adapter contract for target"})
        elif not selected:
            gaps.append({"capability": capability, "reason": "No provider selected"})
    return {"required_modules": required, "offered_modules": offered,
            "required_dependencies": sorted({m["dependency"] for m in required}),
            "gaps": gaps, "execution": "plan_only", "ready_to_execute": False}
