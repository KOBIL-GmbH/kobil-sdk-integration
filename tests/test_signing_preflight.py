import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from kobil_sdk_integration.signing_preflight import preflight, register

TEAM = "ABC1234567"
UDID = "00000000-1234567890ABCDEF"


class SigningPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = Path(self.tmp.name).resolve() / "Space ;$(ignored).app"
        self.app.mkdir()
        (self.app / "embedded.mobileprovision").write_bytes(b"opaque cms")
        self.ent = {"application-identifier": TEAM + ".org.example.app",
                    "com.apple.developer.team-identifier": TEAM}
        self.profile = {"TeamIdentifier": [TEAM], "ApplicationIdentifierPrefix": [TEAM],
                        "Entitlements": copy.deepcopy(self.ent), "DeveloperCertificates": [b"leaf DER"],
                        "ExpirationDate": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1),
                        "ProvisionedDevices": [UDID], "private_value": "DO_NOT_EXPOSE"}
        self.leaf = b"leaf DER"
        self.metadata = f"Identifier=org.example.app\nTeamIdentifier={TEAM}\n"

    def run_check(self, failure=None, udid=UDID, **kwargs):
        calls = []
        def run(argv, **options):
            calls.append(argv)
            self.assertEqual(options, dict(capture_output=True, timeout=20, check=False))
            kind = ("profile" if argv[0].endswith("security") else "signature" if "--verify" in argv
                    else "entitlements" if "--entitlements" in argv
                    else "certificate" if any(arg.startswith("--extract-certificates=") for arg in argv) else "metadata")
            if failure == kind:
                return subprocess.CompletedProcess(argv, 1, b"SECRET", b"SECRET PROFILE")
            out = b""
            err = b""
            if kind == "profile": out = plistlib.dumps(self.profile)
            if kind == "entitlements": out = plistlib.dumps(self.ent)
            if kind == "metadata": err = self.metadata.encode()
            if kind == "certificate" and self.leaf is not None:
                prefix = next(arg.split("=", 1)[1] for arg in argv if arg.startswith("--extract-certificates="))
                self.assertEqual(Path(prefix).parent.stat().st_mode & 0o777, 0o700)
                Path(prefix + "0").write_bytes(self.leaf)
                self.certificate_directory = Path(prefix).parent
            return subprocess.CompletedProcess(argv, 0, out, err)
        with patch("kobil_sdk_integration.signing_preflight.subprocess.run", side_effect=run):
            result = preflight(str(self.app), TEAM, udid, **kwargs)
        self.assertNotIn("DO_NOT_EXPOSE", json.dumps(result))
        self.assertNotIn("SECRET", json.dumps(result))
        for argv in calls:
            self.assertIn(str(self.app) if not argv[0].endswith("security") else str(self.app / "embedded.mobileprovision"), argv)
        return result

    def test_valid_signed_app_and_device(self):
        result = self.run_check()
        self.assertEqual(result["status"], "artifact_checked")
        self.assertTrue(result["checks"]["codesign_verified"])
        self.assertFalse(result["runtime_verified"])

    def test_wrong_actual_team_even_if_profile_expected(self):
        self.metadata = self.metadata.replace(TEAM, "XYZ7654321")
        self.assertIn("SIGNED_TEAM_MISMATCH_OR_UNKNOWN", self.run_check()["errors"])

    def test_profile_team_mismatch(self):
        self.profile["TeamIdentifier"] = ["XYZ7654321"]
        self.assertEqual(self.run_check()["status"], "blocked")

    def test_profile_app_prefix_or_bundle_mismatch(self):
        for identifier in ["XYZ7654321.org.example.app", TEAM + ".org.other.app", None]:
            with self.subTest(identifier=identifier):
                self.profile["Entitlements"]["application-identifier"] = identifier or ""
                self.assertIn("PROFILE_APPLICATION_IDENTIFIER_MISMATCH_OR_UNKNOWN", self.run_check()["errors"])

    def test_signed_entitlement_team_and_bundle_mismatch(self):
        self.ent["com.apple.developer.team-identifier"] = "XYZ7654321"
        self.ent["application-identifier"] = TEAM + ".org.other.app"
        self.assertEqual(self.run_check()["status"], "blocked")

    def test_expired_or_missing_expiry(self):
        self.profile["ExpirationDate"] = datetime(2000, 1, 1)
        self.assertIn("PROFILE_UNEXPIRED_MISMATCH_OR_UNKNOWN", self.run_check()["errors"])
        del self.profile["ExpirationDate"]
        self.assertEqual(self.run_check()["status"], "blocked")

    def test_device_mismatch_and_enterprise(self):
        self.profile["ProvisionedDevices"] = ["OTHER0000"]
        self.assertEqual(self.run_check()["status"], "blocked")
        self.profile["ProvisionsAllDevices"] = True
        self.assertEqual(self.run_check()["status"], "artifact_checked")

    def test_optional_device_and_wildcard(self):
        del self.profile["ProvisionedDevices"]
        self.profile["Entitlements"]["application-identifier"] = TEAM + ".*"
        r = self.run_check(udid=None)
        self.assertEqual(r["status"], "artifact_checked")
        self.assertEqual(r["checks"]["device_eligible"], "not_requested")

    def test_each_command_failure_is_sanitized_and_blocks(self):
        for name in ["signature", "metadata", "entitlements", "profile", "certificate"]:
            with self.subTest(name=name):
                code = "CERTIFICATE_EXTRACTION_FAILED" if name == "certificate" else name.upper() + "_FAILED"
                self.assertIn(code, self.run_check(failure=name)["errors"])

    def test_unreadable_and_timeout(self):
        for exc in [FileNotFoundError("SECRET"), subprocess.TimeoutExpired("SECRET", 20, output=b"SECRET")]:
            with patch("kobil_sdk_integration.signing_preflight.subprocess.run", side_effect=exc):
                result = preflight(str(self.app), TEAM, UDID)
                self.assertEqual(result["status"], "blocked")
                self.assertNotIn("SECRET", json.dumps(result))
        with patch("kobil_sdk_integration.signing_preflight.subprocess.run", return_value=subprocess.CompletedProcess([], 0, b"not a plist", b"")):
            self.assertEqual(preflight(str(self.app), TEAM)["status"], "blocked")

    def test_missing_app_or_profile_and_invalid_inputs_do_not_run(self):
        (self.app / "embedded.mobileprovision").unlink()
        with patch("kobil_sdk_integration.signing_preflight.subprocess.run") as run:
            for path, team in [(str(self.app), TEAM), ("/missing.app", TEAM), (str(self.app), "")]:
                self.assertEqual(preflight(path, team)["status"], "blocked")
            run.assert_not_called()

    def test_malformed_xml_and_missing_team_are_blocked(self):
        with patch("kobil_sdk_integration.signing_preflight.subprocess.run", return_value=subprocess.CompletedProcess([], 0, b"<?xml malformed", b"")):
            self.assertEqual(preflight(str(self.app), TEAM)["status"], "blocked")
        self.metadata = "Identifier=org.example.app\n"
        self.assertIn("SIGNED_TEAM_MISMATCH_OR_UNKNOWN", self.run_check()["errors"])

    def test_legacy_app_prefix_can_differ_from_team(self):
        legacy = "OLD1234567"
        self.profile["ApplicationIdentifierPrefix"] = [legacy]
        self.ent["application-identifier"] = legacy + ".org.example.app"
        self.profile["Entitlements"]["application-identifier"] = legacy + ".*"
        self.assertEqual(self.run_check()["status"], "artifact_checked")

    def test_incorrect_or_missing_profile_prefix_blocks(self):
        self.profile["ApplicationIdentifierPrefix"] = ["OLD1234567"]
        self.assertEqual(self.run_check()["status"], "blocked")
        del self.profile["ApplicationIdentifierPrefix"]
        self.assertEqual(self.run_check()["status"], "blocked")

    def test_wrong_types_are_blocked_before_commands(self):
        with patch("kobil_sdk_integration.signing_preflight.subprocess.run") as run:
            for team in [None, 123, [], {}]:
                self.assertEqual(preflight(str(self.app), team)["status"], "blocked")
            for device in [123, [], {}, True]:
                self.assertEqual(preflight(str(self.app), TEAM, device)["status"], "blocked")
            run.assert_not_called()

    def test_signer_certificate_mismatch_missing_and_cleanup(self):
        self.profile["DeveloperCertificates"] = [b"other DER"]
        self.assertIn("SIGNER_CERTIFICATE_AUTHORIZED_MISMATCH_OR_UNKNOWN", self.run_check()["errors"])
        self.assertFalse(self.certificate_directory.exists())
        for certificates in [[], ["not DER"], None]:
            self.profile["DeveloperCertificates"] = certificates or []
            self.assertEqual(self.run_check()["status"], "blocked")
        self.leaf = None
        self.assertIn("CERTIFICATE_EXTRACTION_UNAVAILABLE", self.run_check()["errors"])

    def test_debug_entitlement_cannot_exceed_profile(self):
        self.ent["get-task-allow"] = True
        self.profile["Entitlements"]["get-task-allow"] = False
        self.assertIn("SIGNED_ENTITLEMENTS_AUTHORIZED_MISMATCH_OR_UNKNOWN", self.run_check()["errors"])
        self.ent["get-task-allow"] = False
        self.assertEqual(self.run_check()["status"], "artifact_checked")
        del self.profile["Entitlements"]["get-task-allow"]
        self.assertEqual(self.run_check()["status"], "blocked")

    def test_group_wildcards_and_ungranted_groups(self):
        for key in ["keychain-access-groups", "com.apple.security.application-groups"]:
            self.ent[key] = [TEAM + ".group"]
            self.profile["Entitlements"][key] = [TEAM + ".*"]
        self.assertEqual(self.run_check()["status"], "artifact_checked")
        self.ent["keychain-access-groups"].append("OTHER.group")
        self.assertEqual(self.run_check()["status"], "blocked")

    def test_structured_grants_are_recursive_and_no_generic_wildcards(self):
        self.ent["custom"] = {"nested": ["one"], "enabled": True}
        self.profile["Entitlements"]["custom"] = {"nested": ["one", "two"], "enabled": True}
        self.assertEqual(self.run_check()["status"], "artifact_checked")
        self.profile["Entitlements"]["custom"]["nested"] = ["*"]
        self.assertEqual(self.run_check()["status"], "blocked")
        self.ent["custom"] = "something"
        self.profile["Entitlements"]["custom"] = "*"
        self.assertEqual(self.run_check()["status"], "blocked")

    def test_registration_exact_api(self):
        class MCP:
            def tool(self):
                def save(fn):
                    self.fn = fn
                    return fn
                return save
        mcp = MCP()
        register(mcp)
        self.assertEqual(mcp.fn.__name__, "sdk_ios_signing_preflight")
        with patch("kobil_sdk_integration.signing_preflight.preflight", return_value={"status": "blocked"}) as check:
            mcp.fn("app.app", TEAM, UDID)
            check.assert_called_once_with("app.app", TEAM, UDID)
