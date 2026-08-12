import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]


class ReleaseMetadataTests(unittest.TestCase):
    def test_one_version_is_used_everywhere(self):
        main_text = (APP_DIR / "main.py").read_text(encoding="utf-8")
        installer = (APP_DIR / "installer.iss").read_text(encoding="utf-8")
        version_info = (APP_DIR / "version_info.txt").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION = "1.4.0"', main_text)
        self.assertIn('#define AppVersion "1.4.0"', installer)
        self.assertIn("VersionInfoVersion=1.4.0.0", installer)
        self.assertIn("filevers=(1, 4, 0, 0)", version_info)
        self.assertIn("prodvers=(1, 4, 0, 0)", version_info)

    def test_app_user_model_id_is_consistent(self):
        startup = (APP_DIR / "windows_startup.py").read_text(encoding="utf-8")
        installer = (APP_DIR / "installer.iss").read_text(encoding="utf-8")
        shortcut_script = (APP_DIR / "set_shortcut_app_id.ps1").read_text(encoding="utf-8-sig")
        expected = "Avtoreya.Desktop"
        self.assertIn(expected, startup)
        self.assertIn(expected, installer)
        self.assertIn(expected, shortcut_script)
        self.assertGreaterEqual(installer.count("AppUserModelID:"), 2)

    def test_release_build_supports_explicit_signed_and_unsigned_modes(self):
        build_script = (APP_DIR / "build_release.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('[ValidateSet("Unsigned", "Signed")]', build_script)
        self.assertIn('[string]$Mode = "Unsigned"', build_script)
        self.assertIn("[string]$CertificateThumbprint", build_script)
        self.assertIn('if ($Mode -eq "Signed")', build_script)
        self.assertIn("Set-AuthenticodeSignature", build_script)
        self.assertIn('-HashAlgorithm "SHA256"', build_script)
        self.assertIn("Windows PowerShell 5.1", build_script)

    def test_release_build_targets_the_current_onedir_executable(self):
        build_script = (APP_DIR / "build_release.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('Get-ChildItem -LiteralPath (Join-Path $appDir "dist") -Directory', build_script)
        self.assertIn('Where-Object { $_.Name -ne "installer" }', build_script)
        self.assertNotIn("Expected exactly one application executable", build_script)

    def test_release_build_runs_checks_and_uses_public_installer_name(self):
        build_script = (APP_DIR / "build_release.ps1").read_text(encoding="utf-8-sig")
        installer = (APP_DIR / "installer.iss").read_text(encoding="utf-8")
        workflow = (APP_DIR.parent / ".github" / "workflows" / "windows-checks.yml").read_text(encoding="utf-8")
        self.assertIn("compileall", build_script)
        self.assertIn("unittest discover", build_script)
        self.assertIn("node --check", build_script)
        self.assertIn("OutputBaseFilename=Avtoreya-Setup", installer)
        self.assertIn("python -m unittest discover", workflow)
        self.assertIn("python -m PyInstaller", workflow)
        self.assertIn("actions/checkout@v7", workflow)
        self.assertIn("actions/setup-python@v7", workflow)
        self.assertNotIn("FORCE_JAVASCRIPT_ACTIONS_TO_NODE24", workflow)

    def test_brand_upgrade_removes_only_old_program_files_and_shortcuts(self):
        installer = (APP_DIR / "installer.iss").read_text(encoding="utf-8")
        self.assertIn("UsePreviousGroup=no", installer)
        self.assertIn('Type: files; Name: "{app}\\Книжница.exe"', installer)
        self.assertIn('Type: files; Name: "{autodesktop}\\Книжница.lnk"', installer)
        self.assertNotIn('%APPDATA%\\Книжница', installer)

    def test_release_dependencies_are_fully_pinned(self):
        requirements = (APP_DIR / "requirements.txt").read_text(encoding="utf-8")
        package_lines = [
            line.strip()
            for line in requirements.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertTrue(package_lines)
        self.assertTrue(all("==" in line for line in package_lines))
        for required in ("pywebview", "pythonnet", "clr_loader", "cffi", "PyInstaller", "Pillow", "python-docx"):
            self.assertTrue(any(line.lower().startswith(required.lower() + "==") for line in package_lines), required)

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
