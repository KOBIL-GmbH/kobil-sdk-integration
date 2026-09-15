import asyncio
import hashlib
from pathlib import Path
import tempfile
import unittest

from kobil_sdk_integration.planner import plan
from kobil_sdk_integration.server import mcp, sdk_artifact_info, sdk_targets


class StarterTests(unittest.TestCase):
    def profile(self, **updates):
        return {"framework": "flutter", "targets": ["android", "ios", "windows", "macos"],
                "backend": "ast-shift", "artifact_source": "local", **updates}

    def test_four_flutter_platforms(self):
        self.assertEqual(set(sdk_targets()["frameworks"]["flutter"]), {"android", "ios", "windows", "macos"})

    def test_provider_is_offered_not_required_by_default(self):
        result = plan(self.profile(distribution=["updraft"], observability=["grafana"]), [])
        self.assertEqual({m["id"] for m in result["offered_modules"]}, {"updraft", "grafana"})
        self.assertNotIn("updraft", result["required_dependencies"])
        self.assertFalse(result["ready_to_execute"])
        self.assertTrue(all(m["status"] == "adapter_pending" for m in result["required_modules"]))

    def test_grafana_request_does_not_select_distribution(self):
        result = plan(self.profile(distribution=["testflight"], observability=["grafana"]), ["observability"])
        self.assertIn("grafana", result["required_dependencies"])
        self.assertNotIn("testflight", result["required_dependencies"])

    def test_diagnostics_cannot_fill_distribution_gaps(self):
        result = plan(self.profile(diagnostics=["android-device", "ios-device"]), ["diagnostics", "distribution"])
        self.assertEqual({g["target"] for g in result["gaps"]}, {"android", "ios", "windows", "macos"})

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

    def test_mcp_tools_registered(self):
        names = {tool.name for tool in asyncio.run(mcp.list_tools())}
        self.assertEqual(names, {"sdk_targets", "sdk_plan", "sdk_artifact_info"})


if __name__ == "__main__":
    unittest.main()
