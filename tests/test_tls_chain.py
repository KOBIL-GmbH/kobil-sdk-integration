"""E12 / VAL-16, VAL-36: served-chain vs trust-asset preflight with fixture certs.

No network: the chain fetch is injected. The fixture reproduces the akinci
evidence shape: leaf <- YE2 <- Root YE <- Root X2, where Root X2 exists both
self-signed and cross-signed by Root X1.
"""
import datetime
from pathlib import Path
import tempfile
import unittest

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from kobil_sdk_integration.tls_chain import check, load_trust_asset, parse_host


def _name(common_name):
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


NOW = datetime.datetime.now(datetime.timezone.utc)


def _certificate(subject, issuer, public_key, signing_key, ca=True, san=None,
                 not_before=None, not_after=None):
    # Validity is relative to the real clock so the fixture never expires under the suite.
    builder = (x509.CertificateBuilder()
               .subject_name(_name(subject)).issuer_name(_name(issuer))
               .public_key(public_key).serial_number(x509.random_serial_number())
               .not_valid_before(not_before or NOW - datetime.timedelta(days=30))
               .not_valid_after(not_after or NOW + datetime.timedelta(days=3650))
               .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True))
    if san:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(name) for name in san]), critical=False)
    return builder.sign(signing_key, hashes.SHA256())


class _Fixture:
    def __init__(self):
        self.keys = {name: ec.generate_private_key(ec.SECP256R1())
                     for name in ("x1", "x2", "ye", "ye2", "leaf")}
        k = self.keys
        self.x1 = _certificate("Test Root X1", "Test Root X1", k["x1"].public_key(), k["x1"])
        self.x2_self = _certificate("Test Root X2", "Test Root X2", k["x2"].public_key(), k["x2"])
        # Cross-sign: same subject and key as x2_self, issued by X1.
        self.x2_cross = _certificate("Test Root X2", "Test Root X1", k["x2"].public_key(), k["x1"])
        self.root_ye = _certificate("Test Root YE", "Test Root X2", k["ye"].public_key(), k["x2"])
        self.ye2 = _certificate("Test YE2", "Test Root YE", k["ye2"].public_key(), k["ye"])
        self.leaf = _certificate("service.test", "Test YE2", k["leaf"].public_key(), k["ye2"], ca=False,
                                 san=["service.test"])

    def served(self, *certificates):
        chain = [c.public_bytes(serialization.Encoding.DER) for c in certificates]
        return lambda host, port: list(chain)

    @staticmethod
    def pem(*certificates):
        return b"".join(c.public_bytes(serialization.Encoding.PEM) for c in certificates)


FIXTURE = _Fixture()


class TlsChainCheckTests(unittest.TestCase):
    def asset(self, data, suffix=".pem"):
        path = Path(self.directory.name) / ("asset" + suffix)
        path.write_bytes(data)
        return str(path)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.cross_chain = FIXTURE.served(FIXTURE.leaf, FIXTURE.ye2, FIXTURE.root_ye, FIXTURE.x2_cross)

    def test_x1_only_asset_reports_missing_x2(self):
        result = check(["https://service.test"], self.asset(FIXTURE.pem(FIXTURE.x1)),
                       fetch=self.cross_chain)
        host = result["hosts"][0]
        self.assertEqual(host["status"], "missing_anchors")
        self.assertEqual(host["missing_anchors"], ["CN=Test Root X2"])
        self.assertFalse(result["all_hosts_ok"])
        subjects = [c["subject"] for c in host["served_chain"]]
        self.assertEqual(subjects, ["CN=service.test", "CN=Test YE2", "CN=Test Root YE", "CN=Test Root X2"])
        # every served certificate is described with issuer and fingerprint
        for entry in host["served_chain"]:
            self.assertTrue(entry["issuer"])
            self.assertEqual(len(entry["sha256_fingerprint"]), 64)

    def test_x1_plus_x2_asset_is_ok_even_against_cross_signed_serving(self):
        result = check(["service.test"], self.asset(FIXTURE.pem(FIXTURE.x1, FIXTURE.x2_self)),
                       fetch=self.cross_chain)
        host = result["hosts"][0]
        self.assertEqual(host["status"], "ok")
        self.assertEqual(host["missing_anchors"], [])
        self.assertTrue(result["all_hosts_ok"])
        matched = {m["subject"]: m["match"] for m in host["matched_anchors"]}
        # the asset holds the SELF-SIGNED X2 variant while the server sent the cross-sign
        self.assertEqual(matched, {"CN=Test Root X2": "same_subject_and_key_variant"})

    def test_same_subject_with_different_key_is_not_a_match(self):
        other = ec.generate_private_key(ec.SECP256R1())
        impostor = _certificate("Test Root X2", "Test Root X2", other.public_key(), other)
        result = check(["service.test"], self.asset(FIXTURE.pem(impostor)), fetch=self.cross_chain)
        self.assertFalse(result["all_hosts_ok"])
        self.assertEqual(result["hosts"][0]["matched_anchors"], [])
        self.assertEqual(result["hosts"][0]["missing_anchors"], ["CN=Test Root X2"])

    def test_asset_coverage_does_not_claim_runtime_or_path_validation(self):
        result = check(["service.test"], self.asset(FIXTURE.pem(FIXTURE.x2_self)), fetch=self.cross_chain)
        self.assertTrue(result["all_hosts_ok"])
        self.assertEqual(result["verification_scope"], "asset_coverage_only")
        self.assertFalse(result["runtime_acceptance_verified"])
        self.assertFalse(result["certificate_path_verified"])
        self.assertIn("PEM trust-store bytes", result["verification_note"])

    def test_x2_only_asset_is_ok_and_recommends_cross_sign_parent(self):
        result = check(["service.test:8443"], self.asset(FIXTURE.pem(FIXTURE.x2_self)),
                       fetch=self.cross_chain)
        host = result["hosts"][0]
        self.assertEqual((host["host"], host["port"], host["status"]), ("service.test", 8443, "ok"))
        self.assertEqual([r["subject"] for r in host["recommended_additional_anchors"]],
                         ["CN=Test Root X1"])
        self.assertIn("Cross-sign parent", host["recommended_additional_anchors"][0]["reason"])

    def test_self_signed_top_matches_exact_certificate(self):
        served = FIXTURE.served(FIXTURE.leaf, FIXTURE.ye2, FIXTURE.root_ye, FIXTURE.x2_self)
        host = check(["service.test"], self.asset(FIXTURE.pem(FIXTURE.x2_self)),
                     fetch=served)["hosts"][0]
        self.assertEqual(host["status"], "ok")
        self.assertEqual(host["matched_anchors"], [{"subject": "CN=Test Root X2",
                                                    "match": "exact_certificate"}])
        self.assertEqual(host["recommended_additional_anchors"], [])

    def test_der_single_certificate_asset_is_supported(self):
        der = FIXTURE.x1.public_bytes(serialization.Encoding.DER)
        result = check(["service.test"], self.asset(der, suffix=".der"), fetch=self.cross_chain)
        self.assertEqual(result["trust_asset"]["certificates"][0]["subject"], "CN=Test Root X1")
        self.assertEqual(result["hosts"][0]["missing_anchors"], ["CN=Test Root X2"])

    def test_one_unreachable_host_does_not_hide_the_others(self):
        chain = self.cross_chain

        def fetch(host, port):
            if host == "down.test":
                raise OSError("connection refused")
            return chain(host, port)
        result = check(["service.test", "down.test"],
                       self.asset(FIXTURE.pem(FIXTURE.x1, FIXTURE.x2_self)), fetch=fetch)
        by_host = {h["host"]: h for h in result["hosts"]}
        self.assertEqual(by_host["service.test"]["status"], "ok")
        self.assertEqual(by_host["down.test"]["status"], "fetch_failed")
        self.assertFalse(result["all_hosts_ok"])

    def test_rejects_invalid_input_before_any_connection(self):
        calls = []

        def fetch(host, port):
            calls.append(host)
            return self.cross_chain(host, port)
        asset = self.asset(FIXTURE.pem(FIXTURE.x1))
        for hosts in (["http://plain.test"], [""], ["host:99999"], []):
            with self.assertRaises(ValueError):
                check(hosts, asset, fetch=fetch)
        self.assertEqual(calls, [])
        with self.assertRaises(ValueError):
            check(["service.test"], self.asset(b"", suffix=".empty"), fetch=fetch)
        with self.assertRaises(ValueError):
            check(["service.test"], self.asset(b"not a certificate", suffix=".bin"), fetch=fetch)

    def test_parse_host_variants(self):
        self.assertEqual(parse_host("https://idp.example:8443/auth/realms/x"), ("idp.example", 8443))
        self.assertEqual(parse_host("https://idp.example"), ("idp.example", 443))
        self.assertEqual(parse_host("idp.example"), ("idp.example", 443))

    def test_no_verification_weakening_claim_and_asset_untouched(self):
        asset = self.asset(FIXTURE.pem(FIXTURE.x1))
        before = Path(asset).read_bytes()
        result = check(["service.test"], asset, fetch=self.cross_chain)
        self.assertIn("never disables", result["verification_note"])
        self.assertIn("no trust decision", result["verification_note"])
        self.assertEqual(Path(asset).read_bytes(), before)
        self.assertEqual(len(load_trust_asset(asset)), 1)

    def test_der_encoding_constant_resolves_on_this_interpreter(self):
        # Regression for the bundled CPython 3.11 crash: ssl.ENCODING_DER is
        # not exported there, so the module must resolve the _ssl fallback at
        # import time instead of failing on every live fetch.
        import _ssl

        from kobil_sdk_integration import tls_chain

        self.assertEqual(tls_chain._DER_ENCODING, _ssl.ENCODING_DER)


class _Base(unittest.TestCase):
    def asset(self, data, suffix=".pem"):
        path = Path(self.directory.name) / ("asset" + suffix)
        path.write_bytes(data)
        return str(path)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.cross_chain = FIXTURE.served(FIXTURE.leaf, FIXTURE.ye2, FIXTURE.root_ye, FIXTURE.x2_cross)
        self.both = self.asset(FIXTURE.pem(FIXTURE.x1, FIXTURE.x2_self))

    def host(self, hosts, asset, fetch=None, **kwargs):
        return check(hosts, asset, fetch=fetch or self.cross_chain, **kwargs)["hosts"][0]


class HostnameTests(_Base):
    def leaf_with(self, *names):
        return _certificate("service.test", "Test YE2", FIXTURE.keys["leaf"].public_key(),
                            FIXTURE.keys["ye2"], ca=False, san=list(names) or None)

    def chain_with(self, leaf):
        return FIXTURE.served(leaf, FIXTURE.ye2, FIXTURE.root_ye, FIXTURE.x2_cross)

    def test_matching_san_is_reported(self):
        host = self.host(["service.test"], self.both)
        self.assertTrue(host["hostname_match"]["matches"])
        self.assertEqual(host["hostname_match"]["names"], ["service.test"])
        self.assertEqual(host["status"], "ok")

    def test_other_host_is_a_hostname_mismatch_problem(self):
        host = self.host(["other.test"], self.both)
        self.assertFalse(host["hostname_match"]["matches"])
        self.assertEqual(host["status"], "hostname_mismatch")
        self.assertIn("hostname_mismatch", host["problems"])

    def test_wildcard_matches_exactly_one_label(self):
        fetch = self.chain_with(self.leaf_with("*.service.test"))
        self.assertTrue(self.host(["a.service.test"], self.both, fetch)["hostname_match"]["matches"])
        self.assertFalse(self.host(["a.b.service.test"], self.both, fetch)["hostname_match"]["matches"])
        self.assertFalse(self.host(["service.test"], self.both, fetch)["hostname_match"]["matches"])

    def test_common_name_alone_is_not_enough(self):
        fetch = self.chain_with(self.leaf_with())
        host = self.host(["service.test"], self.both, fetch)
        self.assertFalse(host["hostname_match"]["matches"])
        self.assertEqual(host["hostname_match"]["names"], [])

    def test_hostname_comparison_ignores_case(self):
        fetch = self.chain_with(self.leaf_with("Service.Test"))
        self.assertTrue(self.host(["SERVICE.test"], self.both, fetch)["hostname_match"]["matches"])


class ValidityTests(_Base):
    def issue(self, subject, issuer, key, signer, **kw):
        return _certificate(subject, issuer, FIXTURE.keys[key].public_key(), FIXTURE.keys[signer], **kw)

    def test_served_certificates_report_validity_dates(self):
        host = self.host(["service.test"], self.both)
        for entry in host["served_chain"]:
            self.assertRegex(entry["not_after"], r"^\d{4}-\d{2}-\d{2}T")
            self.assertGreater(entry["days_until_expiry"], 3000)
            self.assertFalse(entry["expired"])

    def test_expired_leaf_is_an_expired_problem(self):
        leaf = self.issue("service.test", "Test YE2", "leaf", "ye2", ca=False, san=["service.test"],
                          not_before=NOW - datetime.timedelta(days=90),
                          not_after=NOW - datetime.timedelta(days=1))
        host = self.host(["service.test"], self.both, FIXTURE.served(leaf, FIXTURE.ye2, FIXTURE.root_ye, FIXTURE.x2_cross))
        self.assertEqual(host["status"], "expired")
        self.assertEqual(host["validity"]["expired"], ["CN=service.test"])

    def test_expired_matched_anchor_in_the_asset_is_an_expired_problem(self):
        old_x2 = self.issue("Test Root X2", "Test Root X2", "x2", "x2",
                            not_before=NOW - datetime.timedelta(days=900),
                            not_after=NOW - datetime.timedelta(days=5))
        host = self.host(["service.test"], self.asset(FIXTURE.pem(FIXTURE.x1, old_x2)))
        self.assertEqual(host["missing_anchors"], [])  # same subject and key still matches
        self.assertEqual(host["status"], "expired")
        self.assertIn("CN=Test Root X2", host["validity"]["expired"])

    def test_expiring_soon_warns_but_does_not_fail(self):
        leaf = self.issue("service.test", "Test YE2", "leaf", "ye2", ca=False, san=["service.test"],
                          not_after=NOW + datetime.timedelta(days=10))
        fetch = FIXTURE.served(leaf, FIXTURE.ye2, FIXTURE.root_ye, FIXTURE.x2_cross)
        host = self.host(["service.test"], self.both, fetch)
        self.assertEqual(host["status"], "ok")
        self.assertEqual(host["validity"]["expiring_soon"], ["CN=service.test"])
        self.assertEqual(host["validity"]["warning_days"], 14)
        quiet = self.host(["service.test"], self.both, fetch, expiry_warning_days=5)
        self.assertEqual(quiet["validity"]["expiring_soon"], [])

    def test_expiry_is_judged_at_the_injected_time(self):
        later = NOW + datetime.timedelta(days=4000)
        host = self.host(["service.test"], self.both, now=later)
        self.assertEqual(host["status"], "expired")

    def test_unused_expired_asset_certificate_does_not_fail_the_host(self):
        stale = self.issue("Unrelated Old Root", "Unrelated Old Root", "ye", "ye",
                           not_before=NOW - datetime.timedelta(days=900),
                           not_after=NOW - datetime.timedelta(days=5))
        result = check(["service.test"], self.asset(FIXTURE.pem(FIXTURE.x1, FIXTURE.x2_self, stale)),
                       fetch=self.cross_chain)
        self.assertEqual(result["hosts"][0]["status"], "ok")
        flags = {c["subject"]: c["expired"] for c in result["trust_asset"]["certificates"]}
        self.assertTrue(flags["CN=Unrelated Old Root"])
        self.assertFalse(flags["CN=Test Root X1"])

    def test_invalid_warning_days_are_rejected(self):
        for value in (-1, "7", None, 4000):
            with self.assertRaises(ValueError):
                check(["service.test"], self.both, fetch=self.cross_chain, expiry_warning_days=value)


class DesktopPathTests(_Base):
    """The KOBIL Confluence procedure for trusted_certs.pem defines 'verified' as a full path check that uses ONLY the
    file as trust (wget/openssl): the chain must end in a self-signed certificate from the
    file. Reported separately because the mobile rule above is stricter or looser in places."""

    def test_self_signed_anchors_give_a_valid_desktop_path(self):
        host = self.host(["service.test"], self.both)
        self.assertEqual(host["desktop_path_check"]["result"], "valid")
        self.assertEqual(host["desktop_path_check"]["terminates_at"], "CN=Test Root X2")

    def test_x1_only_is_desktop_valid_but_still_missing_for_mobile(self):
        host = self.host(["service.test"], self.asset(FIXTURE.pem(FIXTURE.x1)))
        self.assertEqual(host["desktop_path_check"]["result"], "valid")
        self.assertEqual(host["status"], "missing_anchors")
        self.assertEqual(host["problems"], ["missing_anchors"])

    def test_confluence_style_ca_copy_of_a_cross_signed_chain_is_incomplete(self):
        # CA certificates copied from the served chain (page procedure): YE2, YE, cross-signed X2.
        asset = self.asset(FIXTURE.pem(FIXTURE.ye2, FIXTURE.root_ye, FIXTURE.x2_cross))
        host = self.host(["service.test"], asset)
        self.assertEqual(host["missing_anchors"], [])
        self.assertEqual(host["desktop_path_check"]["result"], "invalid")
        self.assertIn("self-signed", host["desktop_path_check"]["detail"])
        self.assertEqual(host["status"], "path_invalid")

    def test_intermediate_only_asset_is_not_ok_even_when_coverage_matches(self):
        served = FIXTURE.served(FIXTURE.leaf, FIXTURE.ye2)
        host = self.host(["service.test"], self.asset(FIXTURE.pem(FIXTURE.ye2)), served)
        self.assertEqual(host["missing_anchors"], [])
        self.assertEqual(host["status"], "path_invalid")
        self.assertFalse(check(["service.test"], self.asset(FIXTURE.pem(FIXTURE.ye2)),
                               fetch=served)["all_hosts_ok"])

    def test_leaf_only_asset_has_no_path(self):
        host = self.host(["service.test"], self.asset(FIXTURE.pem(FIXTURE.leaf)))
        self.assertEqual(host["desktop_path_check"]["result"], "invalid")
        self.assertIn("missing_anchors", host["problems"])

    def test_forged_intermediate_signature_is_not_a_path(self):
        impostor = _certificate("Test YE2", "Test Root YE", FIXTURE.keys["ye2"].public_key(),
                                ec.generate_private_key(ec.SECP256R1()))  # same names, wrong signer
        served = FIXTURE.served(FIXTURE.leaf, impostor, FIXTURE.root_ye, FIXTURE.x2_cross)
        host = self.host(["service.test"], self.both, served)
        self.assertEqual(host["desktop_path_check"]["result"], "invalid")

    def test_expired_intermediate_breaks_the_path(self):
        old = _certificate("Test YE2", "Test Root YE", FIXTURE.keys["ye2"].public_key(), FIXTURE.keys["ye"],
                           not_before=NOW - datetime.timedelta(days=900), not_after=NOW - datetime.timedelta(days=1))
        served = FIXTURE.served(FIXTURE.leaf, old, FIXTURE.root_ye, FIXTURE.x2_cross)
        host = self.host(["service.test"], self.both, served)
        self.assertEqual(host["desktop_path_check"]["result"], "invalid")
        self.assertIn("expired", host["problems"])

    def test_non_ca_issuer_is_rejected(self):
        not_ca = _certificate("Test YE2", "Test Root YE", FIXTURE.keys["ye2"].public_key(),
                              FIXTURE.keys["ye"], ca=False)
        served = FIXTURE.served(FIXTURE.leaf, not_ca, FIXTURE.root_ye, FIXTURE.x2_cross)
        self.assertEqual(self.host(["service.test"], self.both, served)["desktop_path_check"]["result"], "invalid")

    def test_top_that_is_not_self_signed_needs_the_self_signed_variant_for_mobile(self):
        # Served top is Root YE (issuer X2 is not served). The asset holds X1+X2, so a desktop
        # client builds the path, but the strict mobile rule still wants the top subject itself.
        served = FIXTURE.served(FIXTURE.leaf, FIXTURE.ye2, FIXTURE.root_ye)
        host = self.host(["service.test"], self.both, served)
        self.assertEqual(host["desktop_path_check"]["result"], "valid")
        self.assertEqual(host["missing_anchors"], ["CN=Test Root YE"])
        self.assertEqual(host["status"], "missing_anchors")

    def test_path_check_is_not_a_platform_claim(self):
        result = check(["service.test"], self.both, fetch=self.cross_chain)
        self.assertFalse(result["certificate_path_verified"])
        self.assertTrue(result["desktop_path_all_valid"])
        self.assertIn("Confluence", result["verification_note"])
        self.assertIn("not a statement about", result["verification_note"])


class PlatformTests(_Base):
    """Android's native validator is OpenSSL full-path validation over the supplied PEM (no
    partial chain), so the desktop path result decides there. iOS keeps the strict rule that the
    self-signed variant of the top CA subject must be in the asset (VAL-16/VAL-36)."""

    def x1_only(self):
        return self.asset(FIXTURE.pem(FIXTURE.x1))

    def test_default_is_the_strict_ios_rule(self):
        result = check(["service.test"], self.x1_only(), fetch=self.cross_chain)
        self.assertEqual(result["platform"], "ios")
        self.assertEqual(result["hosts"][0]["status"], "missing_anchors")

    def test_android_accepts_x1_only_when_the_desktop_path_is_valid(self):
        result = check(["service.test"], self.x1_only(), fetch=self.cross_chain, platform="android")
        host = result["hosts"][0]
        self.assertEqual(result["platform"], "android")
        self.assertEqual(host["status"], "ok")
        self.assertTrue(result["all_hosts_ok"])
        self.assertEqual(host["problems"], [])

    def test_android_still_reports_the_strict_gap_as_a_warning_not_a_problem(self):
        host = check(["service.test"], self.x1_only(), fetch=self.cross_chain, platform="android")["hosts"][0]
        self.assertEqual(host["missing_anchors"], ["CN=Test Root X2"])
        self.assertTrue(any("iOS" in w and "CN=Test Root X2" in w for w in host["warnings"]))

    def test_android_does_not_hide_a_broken_path(self):
        asset = self.asset(FIXTURE.pem(FIXTURE.ye2, FIXTURE.root_ye, FIXTURE.x2_cross))  # CA copy, no root
        host = check(["service.test"], asset, fetch=self.cross_chain, platform="android")["hosts"][0]
        self.assertEqual(host["status"], "path_invalid")

    def test_android_keeps_hostname_and_expiry_problems(self):
        host = check(["other.test"], self.x1_only(), fetch=self.cross_chain, platform="android")["hosts"][0]
        self.assertEqual(host["status"], "hostname_mismatch")
        later = NOW + datetime.timedelta(days=4000)
        host = check(["service.test"], self.x1_only(), fetch=self.cross_chain, platform="android", now=later)["hosts"][0]
        self.assertEqual(host["status"], "expired")

    def test_android_with_unrelated_root_fails(self):
        other = ec.generate_private_key(ec.SECP256R1())
        impostor = _certificate("Test Root X1", "Test Root X1", other.public_key(), other)
        host = check(["service.test"], self.asset(FIXTURE.pem(impostor)), fetch=self.cross_chain,
                     platform="android")["hosts"][0]
        self.assertEqual(host["status"], "path_invalid")

    def test_android_top_without_self_signed_variant_is_ok_when_the_issuer_root_is_present(self):
        served = FIXTURE.served(FIXTURE.leaf, FIXTURE.ye2, FIXTURE.root_ye)  # top Root YE, issuer X2 not served
        host = check(["service.test"], self.asset(FIXTURE.pem(FIXTURE.x1), suffix=".x1.pem"), fetch=served,
                     platform="android")["hosts"][0]
        # X1 alone cannot end this path (YE <- X2 <- X1 needs the X2 cross-sign, which is not served)
        self.assertEqual(host["status"], "path_invalid")
        host = check(["service.test"], self.both, fetch=served, platform="android")["hosts"][0]
        self.assertEqual(host["status"], "ok")

    def test_unknown_platform_is_rejected(self):
        for value in ("windows", "", None, 1):
            with self.assertRaises(ValueError):
                check(["service.test"], self.x1_only(), fetch=self.cross_chain, platform=value)

    def test_note_names_the_platform_rules(self):
        note = check(["service.test"], self.x1_only(), fetch=self.cross_chain)["verification_note"]
        self.assertIn("Android", note)
        self.assertIn("not verified on a device", note)


class AssetParsingTests(_Base):
    def test_marker_with_corrupt_body_is_rejected(self):
        bad = b"-----BEGIN CERTIFICATE-----\nQUJD\n-----END CERTIFICATE-----\n"
        with self.assertRaises(ValueError):
            check(["service.test"], self.asset(bad), fetch=self.cross_chain)

    def test_concatenated_der_certificates_are_rejected_not_truncated(self):
        der = FIXTURE.x1.public_bytes(serialization.Encoding.DER) + FIXTURE.x2_self.public_bytes(serialization.Encoding.DER)
        with self.assertRaises(ValueError):
            check(["service.test"], self.asset(der, suffix=".der"), fetch=self.cross_chain)

    def test_pem_with_text_before_and_between_certificates_is_read_completely(self):
        data = b"# trusted roots\n" + FIXTURE.pem(FIXTURE.x1) + b"\n# second\n" + FIXTURE.pem(FIXTURE.x2_self)
        host = self.host(["service.test"], self.asset(data))
        self.assertEqual(host["status"], "ok")


class LiveFetchTests(unittest.TestCase):
    def test_fetch_served_chain_returns_the_served_certificates_in_order(self):
        import socket
        import ssl
        import threading

        from kobil_sdk_integration.tls_chain import fetch_served_chain

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        certfile = Path(directory.name) / "chain.pem"
        keyfile = Path(directory.name) / "leaf.key"
        certfile.write_bytes(FIXTURE.pem(FIXTURE.leaf, FIXTURE.ye2, FIXTURE.root_ye))
        keyfile.write_bytes(FIXTURE.keys["leaf"].private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_context.load_cert_chain(str(certfile), str(keyfile))
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(10)
        self.addCleanup(listener.close)

        def serve():
            try:
                connection, _ = listener.accept()
                with server_context.wrap_socket(connection, server_side=True) as tls:
                    tls.recv(1)
            except (OSError, ssl.SSLError):
                pass
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        der = fetch_served_chain("127.0.0.1", listener.getsockname()[1], timeout=10)
        thread.join(5)
        expected = [c.public_bytes(serialization.Encoding.DER) for c in (FIXTURE.leaf, FIXTURE.ye2, FIXTURE.root_ye)]
        self.assertEqual(der, expected)


if __name__ == "__main__":
    unittest.main()
