import copy
import hashlib
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True
VARIANT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VARIANT / "build"))
from image_inventory import installed_packages, input_bundle_identity, software_inventory, verify_cached_inputs


class ImageInventoryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="miubomz-input-verification-")
        self.addCleanup(self.temporary.cleanup)
        self.cache = Path(self.temporary.name)
        self.software = self.cache / "software/usr/bin/tool"
        self.software.parent.mkdir(parents=True)
        self.software.write_bytes(b"declared-tool")
        self.archive = self.cache / "apt/package_1.0_all.deb"
        self.archive.parent.mkdir(parents=True)
        self.archive.write_bytes(b"declared-package")
        self.apt_lock = {
            "recipe_sha256": {"live-build/config/package-lists/base.list.chroot": "recipe"},
            "packages": [{
                "name": "package", "version": "1.0", "architecture": "all",
                "filename": "apt/package_1.0_all.deb",
                "sha256": hashlib.sha256(self.archive.read_bytes()).hexdigest(),
                "bytes": self.archive.stat().st_size, "contexts": ["live"],
            }],
        }
        self.software_lock = {"payload": software_inventory(self.cache / "software"),
                              "recipe_sha256": "software-recipe"}

    def test_bundle_identity_depends_on_declared_bytes_and_not_recipe_metadata(self):
        expected = input_bundle_identity(self.apt_lock, self.software_lock)
        self.apt_lock["recipe_sha256"] = {"changed-recipe": "changed"}
        self.apt_lock["packages"][0]["contexts"] = ["live", "installer-media"]
        self.software_lock["recipe_sha256"] = "changed-software-recipe"
        self.software_lock["provenance"] = "a different capture description"
        self.assertEqual(input_bundle_identity(self.apt_lock, self.software_lock), expected)
        changed_archive = copy.deepcopy(self.apt_lock)
        changed_archive["packages"][0]["sha256"] = "changed-archive-sha256"
        self.assertNotEqual(input_bundle_identity(changed_archive, self.software_lock), expected)
        changed_software = copy.deepcopy(self.software_lock)
        changed_software["payload"]["sha256"] = "changed-software-sha256"
        self.assertNotEqual(input_bundle_identity(self.apt_lock, changed_software), expected)

    def test_cached_archive_corruption_is_rejected_despite_cached_build_metadata(self):
        (self.cache / "build-inputs.json").write_text('{"validation": "accepted"}\n')
        verify_cached_inputs(self.cache, self.apt_lock, self.software_lock)
        self.archive.write_bytes(b"tampered-package")
        self.assertEqual(self.archive.stat().st_size, self.apt_lock["packages"][0]["bytes"])
        with self.assertRaisesRegex(SystemExit, "Package archive differs from the tracked lock"):
            verify_cached_inputs(self.cache, self.apt_lock, self.software_lock)

    def test_cached_software_corruption_is_rejected_despite_cached_build_metadata(self):
        (self.cache / "build-inputs.json").write_text('{"validation": "accepted"}\n')
        verify_cached_inputs(self.cache, self.apt_lock, self.software_lock)
        self.software.write_bytes(b"tampered-tool")
        with self.assertRaisesRegex(SystemExit, "Software payload differs from the tracked lock"):
            verify_cached_inputs(self.cache, self.apt_lock, self.software_lock)

    def test_cached_software_permission_changes_are_rejected(self):
        verify_cached_inputs(self.cache, self.apt_lock, self.software_lock)
        mode = stat.S_IMODE(self.software.stat().st_mode)
        self.software.chmod(mode ^ stat.S_IXUSR)
        with self.assertRaisesRegex(SystemExit, "Software payload differs from the tracked lock"):
            verify_cached_inputs(self.cache, self.apt_lock, self.software_lock)

    def test_cached_software_directory_permission_changes_are_rejected(self):
        verify_cached_inputs(self.cache, self.apt_lock, self.software_lock)
        directory = self.software.parent
        mode = stat.S_IMODE(directory.stat().st_mode)
        directory.chmod(mode ^ stat.S_IXOTH)
        with self.assertRaisesRegex(SystemExit, "Software payload differs from the tracked lock"):
            verify_cached_inputs(self.cache, self.apt_lock, self.software_lock)

    def test_native_squashfs_inventory_excludes_removed_package_configuration(self):
        with tempfile.TemporaryDirectory(prefix="miubomz-inventory-test-") as temporary:
            work = Path(temporary)
            status = work / "source/var/lib/dpkg/status"
            status.parent.mkdir(parents=True)
            status.write_text(
                "Package: miubomz-defaults\nStatus: install ok installed\n"
                "Architecture: all\nVersion: 0.2.0\n"
                "Maintainer: Miubomz <miubomz@localhost>\nDescription: defaults\n\n"
                "Package: architecture-package\nStatus: install ok installed\n"
                "Architecture: amd64\nVersion: 1:2.3-4\n"
                "Maintainer: Miubomz <miubomz@localhost>\nDescription: architecture\n\n"
                "Package: removed-package\nStatus: deinstall ok config-files\n"
                "Architecture: all\nVersion: 1.0\n"
                "Maintainer: Miubomz <miubomz@localhost>\nDescription: removed\n")
            filesystem = work / "filesystem.squashfs"
            subprocess.run([
                "mksquashfs", str(work / "source"), str(filesystem),
                "-processors", "1", "-no-progress",
            ], check=True, stdout=subprocess.DEVNULL)
            self.assertEqual(installed_packages(filesystem, work), {
                ("miubomz-defaults", "0.2.0", "all"),
                ("architecture-package", "1:2.3-4", "amd64"),
            })


if __name__ == "__main__":
    unittest.main()
