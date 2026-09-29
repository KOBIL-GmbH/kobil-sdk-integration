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


def _certificate(subject, issuer, public_key, signing_key, ca=True):
    now = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    return (x509.CertificateBuilder()
            .subject_name(_name(subject)).issuer_name(_name(issuer))
            .public_key(public_key).serial_number(x509.random_serial_number())
            .not_valid_before(now).not_valid_after(now + datetime.timedelta(days=365))
            .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
            .sign(signing_key, hashes.SHA256()))


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
        self.leaf = _certificate("service.test", "Test YE2", k["leaf"].public_key(), k["ye2"], ca=False)

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
        self.assertEqual(matched, {"CN=Test Root X2": "same_subject_variant"})

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


if __name__ == "__main__":
    unittest.main()
