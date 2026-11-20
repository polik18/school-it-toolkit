"""核心安全行為測試：只用標準庫，不連任何設備。  python3 -m unittest discover -s tests"""
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sitk import cli  # noqa: E402
from sitk.adapters.dnsdhcp_bind9_isc import Bind9IscDnsDhcp  # noqa: E402
from sitk.adapters.switch_ssh_cli import PROFILES, SshCliSwitch, parse_mac_table  # noqa: E402
from sitk.errors import FailClosed, OutOfScope, UnknownAsset  # noqa: E402
from sitk.guard import require_in_scope  # noqa: E402
from sitk.registry import Registry  # noqa: E402
from sitk.secrets import Secret, get_secret  # noqa: E402
from sitk.site import load_site  # noqa: E402
from sitk.state import StateStore  # noqa: E402

DEMO = ROOT / "examples" / "demo-school"


class SiteCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(DEMO, self.tmp / "site")
        self.site_file = self.tmp / "site" / "site.toml"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def sitk(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(["--site", str(self.site_file), "--json", *argv])
        return code, json.loads(buf.getvalue())


class TestSiteAndRegistry(SiteCase):
    def test_empty_scope_fail_closed(self):
        txt = self.site_file.read_text(encoding="utf-8").replace(
            'allowed_networks = ["192.0.2.0/24", "198.51.100.0/24"]', "allowed_networks = []")
        self.site_file.write_text(txt, encoding="utf-8")
        with self.assertRaises(FailClosed):
            load_site(str(self.site_file))

    def test_missing_inventory_fail_closed(self):
        (self.tmp / "site" / "inventory" / "devices.csv").unlink()
        with self.assertRaises(FailClosed):
            Registry(load_site(str(self.site_file)))

    def test_empty_inventory_fail_closed(self):
        p = self.tmp / "site" / "inventory" / "devices.csv"
        p.write_text(p.read_text(encoding="utf-8").splitlines()[0] + "\n", encoding="utf-8")
        with self.assertRaises(FailClosed):
            Registry(load_site(str(self.site_file)))

    def test_alias_lookup_and_unknown(self):
        reg = Registry(load_site(str(self.site_file)))
        self.assertEqual(reg.find_space("306班").code, "A306")
        self.assertEqual(reg.find_device("三年六班", kind="ap").name, "ap-a306")
        with self.assertRaises(UnknownAsset):
            reg.find_device("nextcloud.example")  # 不得自造名稱

    def test_scope(self):
        site = load_site(str(self.site_file))
        require_in_scope(site, "192.0.2.50")
        with self.assertRaises(OutOfScope):
            require_in_scope(site, "203.0.113.9")


class TestCliSafety(SiteCase):
    def test_dry_run_default(self):
        code, out = self.sitk("wifi", "reboot", "306班")
        self.assertEqual(out["status"], "DRY_RUN")

    def test_firewall_requires_confirm(self):
        code, out = self.sitk("firewall", "apply", "--apply")
        self.assertEqual(out["status"], "FAIL_CLOSED")
        code, out = self.sitk("firewall", "apply", "--apply", "--confirm", "wrong-name")
        self.assertEqual(out["status"], "FAIL_CLOSED")
        code, out = self.sitk("firewall", "apply", "--apply", "--confirm", "fw-core-01")
        self.assertEqual(out["status"], "OK")
        log = (self.tmp / "site" / "logs" / "audit.jsonl").read_text(encoding="utf-8")
        self.assertIn('"action": "apply"', log)

    def test_staging_not_reported_as_live(self):
        code, out = self.sitk("switch", "status", "sw-b3pc-01")
        self.assertEqual(out["status"], "NOT_ACTIVE")

    def test_unknown_asset_exit_code(self):
        code, out = self.sitk("info", "火星教室")
        self.assertEqual((code, out["status"]), (2, "UNKNOWN_ASSET"))

    def test_untrusted_marked(self):
        code, out = self.sitk("wifi", "aps")
        self.assertIn("ssid", out["untrusted"])


class TestStateMachine(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_flow_and_resume(self):
        s = StateStore(self.dir, "r1")
        s.init("w", ["a", "b"])
        self.assertEqual(s.next()["item"], "a")
        self.assertEqual(s.next()["status"], "RESUME")  # 中斷後必須先處理 a
        with self.assertRaises(FailClosed):
            s.complete("a", verified=False)
        s.complete("a", verified=True)
        s.next()
        s.fail("b", "timeout")
        self.assertEqual(s.retry_failed()["requeued"], 1)

    def test_empty_and_duplicate(self):
        with self.assertRaises(FailClosed):
            StateStore(self.dir, "r2").init("w", [])
        with self.assertRaises(FailClosed):
            StateStore(self.dir, "r3").init("w", ["a", "a"])
        with self.assertRaises(FailClosed):
            StateStore(self.dir, "../escape")


class TestSecrets(SiteCase):
    def test_permission_and_redaction(self):
        site = load_site(str(self.site_file))
        env = self.tmp / "site" / "secrets.env"
        env.write_text("SWITCH_PASSWORD=s3cret-value\n", encoding="utf-8")
        os.chmod(env, 0o644)
        with self.assertRaises(FailClosed):
            get_secret(site, "switch_password")
        os.chmod(env, stat.S_IRUSR | stat.S_IWUSR)
        val = get_secret(site, "switch_password")
        self.assertEqual(val, "s3cret-value")
        self.assertNotIn("s3cret", repr(val))
        self.assertIsInstance(val, Secret)

    def test_no_default_password(self):
        with self.assertRaises(FailClosed):
            get_secret(load_site(str(self.site_file)), "does_not_exist")


class TestAdapterParsing(unittest.TestCase):
    def test_mac_table_multi_vendor(self):
        samples = {
            "colon": ("VlanId  Mac Address         Type     Interface\n"
                      "1       00:00:5e:00:53:21   dynamic  ethernet1/1/10\n", 1, "ethernet1/1/10"),
            "cisco": ("  10    0000.5e00.5321    DYNAMIC     Gi1/0/7\n", 10, "Gi1/0/7"),
            "aruba": ("00:00:5e:00:53:21  20  dynamic  1/1/5\n", 20, "1/1/5"),
            "comware": ("0000-5e00-5321  30  Learned  GE1/0/3  Y\n", 30, "GE1/0/3"),
        }
        for name, (text, vlan, port) in samples.items():
            rows = parse_mac_table(text)
            self.assertEqual(rows, [{"vlan": vlan, "mac": "00:00:5e:00:53:21", "port": port}], name)

    def test_switch_profile_read_only(self):
        for prof in PROFILES.values():
            for cmd in prof.values():
                self.assertTrue(cmd.startswith(("show ", "display ")))
        ad = SshCliSwitch(None, None, {"profile": "custom", "commands": {"mac_table": "configure terminal"}})
        with self.assertRaises(FailClosed):
            ad._commands()

    def test_dns_keyword_injection_blocked(self):
        for bad in ["a; rm -rf /", "$(id)", "x", "a b"]:
            with self.assertRaises(FailClosed):
                Bind9IscDnsDhcp._kw(bad)
        self.assertEqual(Bind9IscDnsDhcp._kw("srv-dns-01"), "srv-dns-01")


class TestPower(SiteCase):
    def test_dependency_order(self):
        code, out = self.sitk("power", "run", "2", "--mode", "recover")
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_manual_phase_cannot_skip_auto(self):
        code, out = self.sitk("power", "done", "1", "--mode", "recover")
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()


class TestSkillRender(unittest.TestCase):
    def test_render_no_placeholders(self):
        sys.path.insert(0, str(ROOT / "setup"))
        import init as initmod  # noqa: E402
        out = Path(tempfile.mkdtemp())
        try:
            files = initmod.render_skills(DEMO / "site.toml", out)
            self.assertEqual(len(files), 5)
            for f in files:
                text = f.read_text(encoding="utf-8")
                self.assertNotIn("{{", text)
                self.assertTrue(text.startswith("---\nname: sitk-"))
        finally:
            shutil.rmtree(out)
