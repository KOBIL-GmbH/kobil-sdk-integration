import asyncio
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from kobil_sdk_integration.planner import plan
from kobil_sdk_integration.server import mcp, sdk_artifact_info, sdk_targets


class StarterTests(unittest.TestCase):
    def profile(self, **updates):
        return {"framework": "flutter", "targets": ["android", "ios"],
                "backend": "ast-shift", "artifact_source": "local", **updates}

    def test_customer_flutter_platforms(self):
        self.assertEqual(set(sdk_targets()["frameworks"]["flutter"]), {"android", "ios"})

    def test_desktop_customer_targets_rejected(self):
        for target in ("windows", "macos"):
            with self.assertRaises(ValueError):
                plan(self.profile(targets=[target]), [])

    def test_plan_returns_local_build_preflight_before_long_builds(self):
        # E08 / VAL-06, VAL-07: toolchain findings belong in preflight, not mid-build
        text = ' '.join(plan(self.profile(), [])["local_build_preflight"])
        for token in ('BEFORE any long build', 'never a mid-build surprise',
                      'Never mutate shared toolchains', 'COMPLETELY installed', 'source.properties',
                      'NDK 27.2.12479018', 'NOT vendor qualification', 'deployment target',
                      'Xcode', 'iOS 15 for Xcode 27', 'signing', 'disk space',
                      'distinct from simulator tests', '2026-09-29'):
            self.assertIn(token, text, token)
        android_only = ' '.join(plan(self.profile(framework='kotlin', targets=['android']), [])["local_build_preflight"])
        self.assertIn('source.properties', android_only)
        self.assertNotIn('deployment target', android_only)
        ios_only = ' '.join(plan(self.profile(framework='swift', targets=['ios']), [])["local_build_preflight"])
        self.assertIn('deployment target', ios_only)
        self.assertNotIn('source.properties', ios_only)

    def test_provider_is_offered_not_required_by_default(self):
        result = plan(self.profile(distribution=["updraft"], observability=["grafana"]), [])
        self.assertEqual({m["id"] for m in result["offered_modules"]}, {"updraft", "grafana"})
        self.assertNotIn("updraft", result["required_dependencies"])
        self.assertFalse(result["ready_to_execute"])
        self.assertEqual(result["required_modules"][0]["status"], "implemented_selected_live_flows_verified")

    def test_sftp_contract_does_not_claim_execution(self):
        result = plan(self.profile(artifact_source='sftp'), [])
        self.assertIn('sftp-artifacts', result['required_dependencies'])
        self.assertEqual(result['gaps'], [])
        module = next(m for m in result['required_modules'] if m['id'] == 'sftp-artifacts')
        self.assertEqual(module['status'], 'implemented')
        self.assertFalse(result['ready_to_execute'])

    def test_grafana_request_does_not_select_distribution(self):
        result = plan(self.profile(distribution=["testflight"], observability=["grafana"]), ["observability"])
        self.assertIn("grafana", result["required_dependencies"])
        self.assertNotIn("testflight", result["required_dependencies"])

    def test_diagnostics_cannot_fill_distribution_gaps(self):
        result = plan(self.profile(diagnostics=["android-device", "ios-device"]), ["diagnostics", "distribution"])
        self.assertEqual({g["target"] for g in result["gaps"]}, {"android", "ios"})

    def test_unknown_provider_is_visible(self):
        result = plan(self.profile(distribution=["custom-provider"]), [])
        self.assertEqual(result["gaps"][0]["provider"], "custom-provider")

    def test_invalid_profile_and_credentials_rejected(self):
        for profile in (self.profile(password="dummy"), self.profile(targets=["web"]),
                        self.profile(framework="swift", targets=["windows"]), self.profile(testing="robot-appium")):
            with self.assertRaises(ValueError):
                plan(profile, [])

    def test_artifact_hash_does_not_return_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.dll"
            raw = b"test fixture only"
            path.write_bytes(raw)
            result = sdk_artifact_info(str(path))
            self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(result["bytes"], len(raw))
            self.assertFalse(result["compatibility_verified"])
            self.assertNotIn(raw.decode(), str(result))

    def test_artifact_rejects_keys_and_missing_files(self):
        for path in ("private.key", "missing.dll"):
            with self.assertRaises(ValueError):
                sdk_artifact_info(path)

    def test_zip_inventory_flags_missing_config_templates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ios-frameworks.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("Frameworks/KSMasterController.xcframework/Info.plist", "fixture")
            result = sdk_artifact_info(str(path))
            inventory = result["delivery_inventory"]
            self.assertTrue(inventory["inspected"])
            self.assertEqual(inventory["platform_kinds"], ["ios_native"])
            self.assertEqual(inventory["config_templates_present"], [])
            self.assertEqual(inventory["config_templates_missing"], ["mc_config", "app_config"])
            self.assertIn("GettingStarted", inventory["note"])
            self.assertIn("account-wide", inventory["note"])
            self.assertNotIn("fixture", str(inventory))

    def test_zip_inventory_classifies_platforms_and_present_templates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "delivery.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("libs/mcsdk.aar", "fixture")
                archive.writestr("flutter_wrapper/pubspec.yaml", "fixture")
                archive.writestr("assets/mc_config.json", "fixture")
                archive.writestr("assets/app_config.json", "fixture")
            inventory = sdk_artifact_info(str(path))["delivery_inventory"]
            self.assertEqual(inventory["platform_kinds"], ["android_native", "flutter"])
            self.assertEqual(inventory["config_templates_present"], ["app_config", "mc_config"])
            self.assertEqual(inventory["config_templates_missing"], [])

    def test_non_zip_artifact_has_no_inventory_and_bad_zip_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            plain = Path(directory) / "fixture.dll"
            plain.write_bytes(b"fixture")
            self.assertNotIn("delivery_inventory", sdk_artifact_info(str(plain)))
            broken = Path(directory) / "broken.zip"
            broken.write_bytes(b"not a zip archive")
            inventory = sdk_artifact_info(str(broken))["delivery_inventory"]
            self.assertFalse(inventory["inspected"])
            self.assertEqual(inventory["platform_kinds"], ["unknown"])

    def test_mcp_tools_registered(self):
        names = {tool.name for tool in asyncio.run(mcp.list_tools())}
        self.assertTrue({"sdk_targets", "sdk_plan", "sdk_artifact_info", "sdk_backend_status", "sdk_app_get", "sdk_app_versions", "sdk_app_ensure", "sdk_app_version_ensure", "sdk_config_write", "sdk_tls_chain_check", "sdk_tms_trigger", "sdk_tms_status", "sdk_tms_result", "sdk_tms_cancel"} <= names)


if __name__ == "__main__":
    unittest.main()
