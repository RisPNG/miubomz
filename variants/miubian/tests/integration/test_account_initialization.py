from pathlib import Path, PosixPath
import runpy
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

    def initialize_account(self, root=False):
        def fixture_path(value):
            if str(value) in ("/etc/skel/.bashrc", "/usr/share/miubomz/skel/.bashrc"):
                return self.root / str(value).lstrip("/")
            return PosixPath(value)

        with patch("pathlib.Path", new=fixture_path), \
                patch("pwd.getpwnam", return_value=self.account), \
                patch("sys.argv", [str(INITIALIZER), "alice"]), \
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


if __name__ == "__main__":
    unittest.main()
