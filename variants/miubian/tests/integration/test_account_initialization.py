from pathlib import Path, PosixPath
import configparser
import hashlib
import json
import os
import runpy
import subprocess
import sys
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch


sys.dont_write_bytecode = True
VARIANT = Path(__file__).resolve().parents[2]
INITIALIZER = VARIANT / "integration/helpers/initialize-user"


class AccountInitializationTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="miubomz-account-initialization-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home/alice"
        self.home.mkdir(parents=True)
        self.account = SimpleNamespace(pw_name="alice", pw_dir=str(self.home), pw_uid=1001, pw_gid=1002)
        self.debian_seed = self.root / "etc/skel/.bashrc"
        self.debian_seed.parent.mkdir(parents=True)
        self.debian_seed.write_bytes(b"# Debian account seed\n")
        self.product_seed = self.root / "usr/share/miubomz/skel/.bashrc"
        self.product_seed.parent.mkdir(parents=True)
        self.product_seed.write_bytes(b"export PATH=\"$HOME/.local/share/mise/shims:$PATH\"\n")
        self.gio = SimpleNamespace(
            content_types_get_registered=lambda: ["audio/mpeg", "audio/webm", "video/mp4", "video/x-mjpeg", "image/png", "application/x-picture"],
            content_type_get_mime_type=lambda value: value,
            content_type_is_a=lambda value, family: (value, family) in {
                ("audio/webm", "video/*"), ("video/x-mjpeg", "image/*"), ("application/x-picture", "image/*")
            },
        )

    def initialize_account(self, root=False):
        def fixture_path(value):
            if str(value) in ("/etc/skel/.bashrc", "/usr/share/miubomz/skel/.bashrc"):
                return self.root / str(value).lstrip("/")
            return PosixPath(value)

        with patch("pathlib.Path", new=fixture_path), \
                patch("pwd.getpwnam", return_value=self.account), \
                patch("sys.argv", [str(INITIALIZER), "alice"]), \
                patch.dict("sys.modules", {"gi": SimpleNamespace(), "gi.repository": SimpleNamespace(Gio=self.gio)}), \
                patch("os.geteuid", return_value=0 if root else 1001), \
                patch("os.chown") as chown, patch("os.lchown") as lchown, \
                patch("subprocess.run") as run:
            self.commands = run
            runpy.run_path(str(INITIALIZER), run_name="__main__")
        return chown, lchown, run

    def test_missing_account_shell_receives_product_seed(self):
        chown, _, run = self.initialize_account()
        self.assertEqual((self.home / ".bashrc").read_bytes(), self.product_seed.read_bytes())
        self.assertTrue((self.home / ".local/state/miubomz/initialized-0.1.0").is_file())
        self.assertEqual((self.home / ".config/gtk-4.0/gtk.css").readlink(),
                         Path("/usr/share/themes/Fluent-round-Dark-compact/gtk-4.0/gtk.css"))
        chown.assert_not_called()
        run.assert_any_call([
            "env", "HOME=" + str(self.home), "XDG_DATA_HOME=" + str(self.home / ".local/share"),
            "XDG_CONFIG_HOME=" + str(self.home / ".config"), "/usr/bin/mise", "reshim",
        ], check=True)

    def test_clean_debian_account_shell_receives_product_seed(self):
        (self.home / ".bashrc").write_bytes(self.debian_seed.read_bytes())
        self.initialize_account()
        self.assertEqual((self.home / ".bashrc").read_bytes(), self.product_seed.read_bytes())
        self.assertEqual(self.debian_seed.read_bytes(), b"# Debian account seed\n")

    def test_custom_account_shell_is_preserved_during_initialization(self):
        custom = b"export MY_ACCOUNT_PREFERENCE=custom\n"
        (self.home / ".bashrc").write_bytes(custom)
        self.initialize_account()
        self.assertEqual((self.home / ".bashrc").read_bytes(), custom)
        self.assertTrue((self.home / ".local/state/miubomz/initialized-0.1.0").is_file())

    def test_root_initialization_assigns_seed_and_links_to_account(self):
        (self.home / ".bashrc").write_bytes(self.debian_seed.read_bytes())
        chown, lchown, run = self.initialize_account(root=True)
        chown.assert_any_call(self.home / ".bashrc", self.account.pw_uid, self.account.pw_gid)
        lchown.assert_any_call(self.home / ".config/gtk-4.0/gtk.css",
                              self.account.pw_uid, self.account.pw_gid)
        run.assert_any_call([
            "/usr/sbin/runuser", "-u", "alice", "--", "env", "HOME=" + str(self.home),
            "XDG_DATA_HOME=" + str(self.home / ".local/share"),
            "XDG_CONFIG_HOME=" + str(self.home / ".config"), "/usr/bin/mise", "reshim",
        ], check=True)

    def test_existing_initialization_stamp_preserves_later_shell_changes(self):
        self.initialize_account()
        custom = b"export MY_LATER_PREFERENCE=retained\n"
        (self.home / ".bashrc").write_bytes(custom)
        with self.assertRaises(SystemExit) as result:
            self.initialize_account()
        self.assertEqual(result.exception.code, 0)
        self.assertEqual((self.home / ".bashrc").read_bytes(), custom)
        self.commands.assert_not_called()

    def test_media_defaults_expand_native_types_without_crossing_families(self):
        path = self.home / ".config/mimeapps.list"
        path.parent.mkdir(parents=True)
        path.write_text((VARIANT / "integration/defaults/applications/mimeapps.list").read_text())
        self.initialize_account()
        associations = configparser.ConfigParser(interpolation=None)
        associations.read(path)
        defaults = associations["Default Applications"]
        self.assertEqual(defaults["audio/mpeg"], "harmonoid.desktop;mpv.desktop;")
        self.assertEqual(defaults["audio/webm"], "harmonoid.desktop;mpv.desktop;")
        self.assertEqual(defaults["application/xspf+xml"], "harmonoid.desktop;mpv.desktop;")
        self.assertEqual(defaults["video/mp4"], "mpv.desktop;")
        self.assertEqual(defaults["video/x-mjpeg"], "mpv.desktop;")
        self.assertEqual(defaults["image/png"], "qview.desktop;")
        self.assertEqual(defaults["application/x-picture"], "qview.desktop;")
        self.assertEqual(defaults["application/pdf"], "org.gnome.Evince.desktop;")
        self.assertEqual(defaults["application/xhtml+xml"], "vivaldi-stable.desktop;")
        self.assertFalse(any("*" in mime for mime in defaults))
        self.assertEqual(associations["Added Associations"]["audio/mpeg"], "harmonoid.desktop;mpv.desktop;")

    def test_audio_default_tracks_manual_harmonoid_installation_and_removal(self):
        path = self.home / ".config/mimeapps.list"
        path.parent.mkdir(parents=True)
        path.write_text((VARIANT / "integration/defaults/applications/mimeapps.list").read_text())
        self.initialize_account()
        preferences = path.read_bytes()
        applications = self.home / ".local/share/applications"
        applications.mkdir(parents=True)
        native_data = self.root / "native/share"
        native_data.mkdir(parents=True)
        (native_data / "mime").symlink_to("/usr/share/mime")
        environment = dict(os.environ, HOME=str(self.home), XDG_CONFIG_HOME=str(path.parent),
                           XDG_DATA_HOME=str(applications.parent), XDG_CONFIG_DIRS=str(self.root / "etc/xdg"),
                           XDG_DATA_DIRS=str(native_data), XDG_CURRENT_DESKTOP="GNOME")
        audio_types = ["audio/mpeg", "audio/webm", "application/xspf+xml"]
        desktop = ("[Desktop Entry]\nType=Application\nName={name}\nExec=/bin/true %U\n"
                   "MimeType=" + ";".join(audio_types) + ";\n")
        (applications / "mpv.desktop").write_text(desktop.format(name="mpv"))
        query = ("import json; from gi.repository import Gio; "
                 f"print(json.dumps({{mime: Gio.AppInfo.get_default_for_type(mime, False).get_id() "
                 f"for mime in {audio_types!r}}}))")
        for state, expected in [("absent", "mpv.desktop"), ("installed", "harmonoid.desktop"),
                                ("removed", "mpv.desktop")]:
            with self.subTest(state=state):
                if state == "installed":
                    (applications / "harmonoid.desktop").write_text(desktop.format(name="Harmonoid"))
                elif state == "removed":
                    (applications / "harmonoid.desktop").unlink()
                subprocess.run(["update-desktop-database", str(applications)], env=environment, check=True)
                selected = json.loads(subprocess.check_output(["/usr/bin/python3", "-c", query],
                                                              env=environment, text=True))
                self.assertEqual(selected, dict.fromkeys(audio_types, expected))
                self.assertEqual(path.read_bytes(), preferences)

    def test_existing_explicit_associations_are_preserved_and_root_assigns_mimeapps(self):
        path = self.home / ".config/mimeapps.list"
        path.parent.mkdir(parents=True)
        path.write_text("[Default Applications]\nimage/*=qview.desktop;\nimage/png=personal-viewer.desktop;\n"
                        "text/plain=personal-editor.desktop;\n[Added Associations]\nimage/png=another-viewer.desktop;\n"
                        "[Removed Associations]\nimage/png=personal-viewer.desktop;blocked-viewer.desktop;\n")
        chown, _, _ = self.initialize_account(root=True)
        associations = configparser.ConfigParser(interpolation=None)
        associations.read(path)
        self.assertEqual(associations["Default Applications"]["image/png"], "personal-viewer.desktop;")
        self.assertEqual(associations["Default Applications"]["text/plain"], "personal-editor.desktop;")
        self.assertEqual(associations["Added Associations"]["image/png"], "personal-viewer.desktop;another-viewer.desktop;")
        self.assertEqual(associations["Removed Associations"]["image/png"], "blocked-viewer.desktop;")
        chown.assert_any_call(path, self.account.pw_uid, self.account.pw_gid)
        path.write_text("[Default Applications]\nimage/png=later-viewer.desktop;\n")
        with self.assertRaises(SystemExit):
            self.initialize_account()
        self.assertEqual(path.read_text(), "[Default Applications]\nimage/png=later-viewer.desktop;\n")

    def test_gearlever_registration_with_account_key_is_preserved(self):
        path = self.home / ".var/app/it.mijorus.gearlever/config/gearlever.conf"
        path.parent.mkdir(parents=True)
        appimage = self.home / "AppImages/qview.appimage"
        key = "app." + hashlib.md5(bytes(appimage)).hexdigest()
        path.write_text(f"[{key}]\nname=qView\nfile_path={appimage}\n")
        self.initialize_account()
        settings = configparser.ConfigParser(interpolation=None)
        settings.read(path)
        self.assertEqual(settings.sections(), [key])
        self.assertEqual(settings[key]["name"], "qView")
        self.assertEqual(settings[key]["file_path"], str(appimage))


if __name__ == "__main__":
    unittest.main()
