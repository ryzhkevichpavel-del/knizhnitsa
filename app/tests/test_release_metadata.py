import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]


class ReleaseMetadataTests(unittest.TestCase):
    def test_one_version_is_used_everywhere(self):
        main_text = (APP_DIR / "main.py").read_text(encoding="utf-8")
        installer = (APP_DIR / "installer.iss").read_text(encoding="utf-8")
        version_info = (APP_DIR / "version_info.txt").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION = "1.1.0"', main_text)
        self.assertIn('#define AppVersion "1.1.0"', installer)
        self.assertIn("filevers=(1, 1, 0, 0)", version_info)
        self.assertIn("prodvers=(1, 1, 0, 0)", version_info)

    def test_app_user_model_id_is_consistent(self):
        startup = (APP_DIR / "windows_startup.py").read_text(encoding="utf-8")
        installer = (APP_DIR / "installer.iss").read_text(encoding="utf-8")
        shortcut_script = (APP_DIR / "set_shortcut_app_id.ps1").read_text(encoding="utf-8-sig")
        expected = "Knizhnitsa.Desktop"
        self.assertIn(expected, startup)
        self.assertIn(expected, installer)
        self.assertIn(expected, shortcut_script)
        self.assertGreaterEqual(installer.count("AppUserModelID:"), 2)

    def test_release_build_requires_a_certificate(self):
        build_script = (APP_DIR / "build_release.ps1").read_text(encoding="utf-8-sig")
        sign_script = (APP_DIR / "sign_file.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("[Parameter(Mandatory = $true)]", build_script)
        self.assertIn("[string]$CertificateThumbprint", build_script)
        self.assertIn("Set-AuthenticodeSignature", sign_script)
        self.assertIn('HashAlgorithm = "SHA256"', sign_script)

    def test_activation_and_splash_do_not_expire_during_a_slow_start(self):
        main_text = (APP_DIR / "main.py").read_text(encoding="utf-8")
        startup = (APP_DIR / "windows_startup.py").read_text(encoding="utf-8")
        self.assertIn("activation_pending.set()", main_text)
        self.assertIn("if activation_pending.is_set()", main_text)
        self.assertNotIn("wait_seconds=60", main_text)
        self.assertIn("self._timer = threading.Timer(self.slow_after, self._mark_slow)", startup)
        self.assertNotIn("threading.Timer(self.timeout, self.stop)", startup)


if __name__ == "__main__":
    unittest.main()
