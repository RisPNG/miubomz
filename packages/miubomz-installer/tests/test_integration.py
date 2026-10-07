import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


sys.dont_write_bytecode = True
PACKAGE = Path(__file__).resolve().parents[1]
storage = {}
sys.modules["libcalamares"] = types.SimpleNamespace(
    globalstorage=types.SimpleNamespace(value=storage.get, insert=storage.__setitem__))


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(module)
    return module


installer = load("installer", PACKAGE / "installer/root/usr/lib/python3/dist-packages/miubomz_installer.py")
hook = load("hook", PACKAGE / "recovery/root/usr/lib/miubomz/apt-pre-snapshot")


class IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        storage.clear()
        storage.update(rootMountPoint=str(self.root), username="alice", partitions=[])

    def write(self, path, content):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)

    def test_sources_keep_vendors_and_remove_stale_debian_suites(self):
        self.write("etc/apt/sources.list",
                   "deb https://deb.debian.org/debian trixie main\n"
                   "deb https://repo.vivaldi.com/stable/deb stable main\n")
        self.write("etc/apt/sources.list.d/old.list",
                   "deb https://snapshot.debian.org/archive/debian/date forky main\n")
        self.write("etc/apt/sources.list.d/microsoft.sources",
                   "Types: deb\nURIs: https://packages.microsoft.com/repos/code\n"
                   "Suites: stable\nComponents: main\nSigned-By: /etc/apt/keyrings/code.gpg\n")
        self.write("etc/apt/sources.list.d/mixed.sources",
                   "Types: deb\nURIs: https://deb.debian.org/debian\n"
                   " https://vendor.example/repo\nSuites: stable\nComponents: main\n")
        build_files = (
            "etc/apt/preferences.d/reference.pref",
            "etc/apt/preferences.d/reference.pref.orig",
            "etc/apt/preferences.d/frozen-media.pref",
            "etc/apt/preferences.d/frozen-media.pref.orig",
            "etc/apt/sources.list.d/frozen-media.list",
            "etc/apt/sources.list.d/frozen-media.list.orig")
        for path in build_files:
            self.write(path, "deb [trusted=yes] file:/packages forky main\n" if ".list" in path
                       else "Package: *\nPin: version 1\nPin-Priority: 1001\n")
        preference = "Package: vendor-app\nPin: origin vendor.example\nPin-Priority: 600\n"
        self.write("etc/apt/preferences.d/vendor.pref", preference)
        microsoft = (self.root / "etc/apt/sources.list.d/microsoft.sources").read_text()
        installer.sources_final()
        main = (self.root / "etc/apt/sources.list").read_text()
        self.assertNotIn("trixie", main)
        self.assertIn("forky main non-free-firmware", main)
        self.assertIn("https://repo.vivaldi.com/stable/deb", main)
        self.assertFalse((self.root / "etc/apt/sources.list.d/old.list").exists())
        self.assertEqual(microsoft, (self.root / "etc/apt/sources.list.d/microsoft.sources").read_text())
        mixed = (self.root / "etc/apt/sources.list.d/mixed.sources").read_text()
        self.assertIn("https://vendor.example/repo", mixed)
        self.assertNotIn("deb.debian.org", mixed)
        for path in build_files:
            self.assertFalse((self.root / path).exists(), path)
        self.assertEqual((self.root / "etc/apt/preferences.d/vendor.pref").read_text(), preference)

    def test_target_uses_actual_uuid_and_installer_account(self):
        self.write("usr/lib/miubomz/timeshift-default.json",
                   (PACKAGE / "recovery/root/usr/lib/miubomz/timeshift-default.json").read_text())
        (self.root / "home/linuxbrew/.linuxbrew").mkdir(parents=True)
        with patch.object(installer.subprocess, "check_output", return_value="btrfs fresh-uuid\n"), \
                patch.object(installer.subprocess, "run") as run:
            installer.initialize_target()
        settings = json.loads((self.root / "etc/timeshift/timeshift.json").read_text())
        self.assertEqual(settings["backup_device_uuid"], "fresh-uuid")
        self.assertEqual(settings["count_daily"], "8")
        self.assertEqual(settings["include_btrfs_home_for_restore"], "false")
        run.assert_any_call(["chroot", str(self.root), "/usr/lib/miubomz/initialize-user", "alice"],
                            check=True)
        run.assert_any_call(["chroot", str(self.root), "chown", "-R", "alice:",
                             "/home/linuxbrew/.linuxbrew"], check=True)

    def test_platform_grub_uses_only_offline_media_and_preserves_crypto_tools(self):
        storage.update(firmwareType="efi", partitions=[{"mountPoint": "/", "luksMapperName": "luks-root"}])
        with patch.object(installer.subprocess, "run") as run:
            installer.bootloader_config()
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[0][-3:], ["manual", "cryptsetup-initramfs", "keyutils"])
        self.assertEqual(commands[-1][-4:], ["-y", "--no-install-recommends", "install", "grub-efi-amd64"])
        self.assertIn("Dir::Etc::sourceparts=-", commands[-1])
        self.assertIn("Dir::Etc::sourcelist=/etc/apt/sources.list.d/debian-live-media.list", commands[-1])
        self.assertEqual((self.root / "etc/initramfs-tools/conf.d/initramfs-permissions").read_text(), "UMASK=0077\n")

    def test_bios_grub_keeps_the_selected_device_for_package_updates(self):
        storage.update(firmwareType="bios", bootLoader={"installPath": "/dev/disk/by-id/chosen-disk"})
        with patch.object(installer.subprocess, "run") as run:
            installer.bootloader_config()
        calls = run.call_args_list
        selection = next(call for call in calls if call.args[0][-1] == "debconf-set-selections")
        self.assertEqual(selection.kwargs["input"],
                         "grub-pc grub-pc/install_devices multiselect /dev/disk/by-id/chosen-disk\n"
                         "grub-pc grub-pc/install_devices_empty boolean false\n")
        installation = next(call for call in calls if call.args[0][-2:] == ["install", "grub-pc"])
        self.assertLess(calls.index(selection), calls.index(installation))

    def prepare_hook(self, cmdline="root=UUID=fresh-uuid"):
        self.write("var/lib/miubomz/installed", "Miubomz 0.1\n")
        self.write("proc/cmdline", cmdline)
        path = patch.object(hook, "Path", side_effect=lambda value: self.root / value.lstrip("/"))
        path.start()
        self.addCleanup(path.stop)
        pipe = patch.object(hook.os, "fdopen", return_value=io.StringIO(
            "VERSION 2\nAPT::Architecture=amd64\n\n"
            "old-package 1 > - **REMOVE**\nnew-package - < 2 /var/cache/apt/archives/new.deb\n"))
        pipe.start()
        self.addCleanup(pipe.stop)

    def test_live_hook_reads_input_without_creating_snapshot(self):
        self.prepare_hook("boot=live components")
        with patch.object(hook.subprocess, "run") as run:
            hook.main()
        run.assert_not_called()

    def test_removal_and_install_share_one_snapshot_with_package_context(self):
        self.prepare_hook()
        with patch.object(hook.subprocess, "check_output", return_value="btrfs\n"), \
                patch.object(hook.subprocess, "run") as run:
            hook.main()
        run.assert_called_once()
        command = run.call_args.args[0]
        self.assertEqual(command[:5], ["timeshift", "--create", "--scripted", "--tags", "D"])
        self.assertIn("old-package, new-package", command[-1])

    def test_snapshot_failure_stops_transaction(self):
        self.prepare_hook()
        with patch.object(hook.subprocess, "check_output", return_value="btrfs\n"), \
                patch.object(hook.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "timeshift")):
            with self.assertRaises(subprocess.CalledProcessError):
                hook.main()


if __name__ == "__main__":
    unittest.main()
