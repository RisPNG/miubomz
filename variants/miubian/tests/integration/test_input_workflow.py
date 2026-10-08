import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True
VARIANT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VARIANT / "build"))
from image_inventory import software_inventory, source_inputs, verify_cached_inputs


class InputWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="miubomz-input-workflow-")
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name) / "project"
        self.variant = self.project / "variants/miubian"
        (self.variant / "build").mkdir(parents=True)
        for filename in ("export-inputs.py", "prepare-inputs.py", "image_inventory.py", "container-build.sh"):
            shutil.copy2(VARIANT / "build" / filename, self.variant / "build" / filename)
        self.environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MIUBOMZ_BUILD_JOBS="1")
        self.environment.pop("MIUBOMZ_INPUT_BUNDLE", None)
        self.environment.pop("MIUBOMZ_RESOLVE_INPUTS", None)
        self.cache = self.project / "cache"
        self.environment["MIUBOMZ_CACHE_DIR"] = str(self.cache)
        self.legacy = self.project / "legacy-cache"
        self.software = self.legacy / "reference/includes.chroot"
        self.software.mkdir(parents=True)
        assets = self.software / "usr/share/fixture-assets"
        assets.mkdir(parents=True)
        assets.chmod(0o750)
        self.executable = assets / "helper"
        self.executable.write_bytes(b"#!/bin/sh\nprintf 'fixture\\n'\n")
        self.executable.chmod(0o755)
        os.link(self.executable, assets / "helper-alias")
        (assets / "helper-link").symlink_to("helper")
        independent = self.software / "usr/share/independent-fixture"
        independent.mkdir()
        (independent / "extra.txt").write_text("independent declared asset\n")
        (self.software / "usr/share/not-selected.txt").write_text("unselected cached bytes\n")
        product_seed = self.software / "etc/skel/.config/mise"
        product_seed.mkdir(parents=True)
        (product_seed / "config.toml").write_text("captured product configuration\n")
        root_seed = self.software / "root/.config/mc"
        root_seed.mkdir(parents=True)
        (root_seed / "ini").write_text("captured root configuration\n")
        (self.software / "root/not-selected.txt").write_text("excluded root bytes\n")
        extension = self.software / "etc/skel/.local/share/gnome-shell/extensions/fixture@example"
        extension.mkdir(parents=True)
        (extension / "metadata.json").write_text(json.dumps({
            "uuid": "fixture@example", "version": 1, "url": "https://example.invalid/fixture",
        }) + "\n")
        self.recipe = {
            "schema": 1, "architecture": "amd64",
            "bundle": {"path": "artifacts/inputs/pending.tar.zst", "sha256": None, "bytes": None},
            "assets": [{"destination": path} for path in (
                "usr/share/fixture-assets", "usr/share/independent-fixture",
                "etc/skel/.config/mise", "root",
                "etc/skel/.local/share/gnome-shell/extensions",
            )],
            "staging_excludes": ["etc/skel/.config/mise/config.toml", "root"],
            "flatpak_applications": [], "flatpak_runtimes": [],
            "gnome_extensions": [{"uuid": "fixture@example", "version": 1,
                                  "upstream": "https://example.invalid/fixture"}],
            "mise_installed": {}, "homebrew_cellar": {}, "mise_pyenv_commit": None,
        }
        package_lists = self.variant / "live-build/config/package-lists"
        package_lists.mkdir(parents=True)
        (package_lists / "05-exported-inputs.list.chroot").write_text("vendor-exported\n")
        (package_lists / "00-platform.list.chroot").write_text("base-package\n")
        (package_lists / "grub.list.binary").write_text("offline-grub\n")
        (self.variant / "inputs/locks").mkdir(parents=True)
        (self.variant / "release.json").write_text(json.dumps({
            "variant": "miubian", "version": "0.2.0", "architecture": "amd64", "distribution": "forky",
        }) + "\n")
        self.apt_lock = {"schema": 1, "architecture": "amd64", "distribution": "forky", "packages": []}
        self.archives = {}
        for name, version, contexts in (
                ("vendor-exported", "1.0", ["live"]),
                ("base-package", "2.0", ["live"]),
                ("offline-grub", "3.0", ["installer-media"])):
            directory = self.legacy / "reference/packages.chroot"
            if contexts == ["installer-media"]:
                directory = self.legacy / "reference/installer-media/pool/main/o/offline-grub"
            archive = self.build_package(name, version, directory)
            self.archives[name] = archive
            self.apt_lock["packages"].append({
                "name": name, "version": version, "architecture": "all",
                "filename": "apt/" + archive.name,
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "bytes": archive.stat().st_size, "contexts": contexts,
            })
        self.apt_lock["recipe_sha256"] = {
            name: value for name, value in source_inputs(self.variant).items()
            if name.startswith(("live-build/config/package-lists/", "live-build/config/archives/"))
        }
        self.software_lock = {
            "schema": 1, "payload": software_inventory(self.software),
            "flatpaks": [], "flatpak_dependencies": [],
            "gnome_extensions": self.recipe["gnome_extensions"],
            "mise_installed": {}, "homebrew_cellar": {}, "mise_pyenv_commit": None,
        }
        (self.variant / "inputs/locks/apt.json").write_text(json.dumps(self.apt_lock, indent=2) + "\n")
        self.review_software_recipe()

    def build_package(self, name, version, destination):
        root = self.project / "package-roots" / name
        (root / "DEBIAN").mkdir(parents=True)
        (root / "DEBIAN/control").write_text(
            f"Package: {name}\nVersion: {version}\nArchitecture: all\n"
            "Maintainer: Ris Peng <hello@rispeng.com>\nDescription: native input workflow fixture\n")
        content = root / "usr/share" / name
        content.mkdir(parents=True)
        (content / "fixture.txt").write_text(f"{name} {version}\n")
        destination.mkdir(parents=True, exist_ok=True)
        archive = destination / f"{name}_{version}_all.deb"
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(root), str(archive)],
                       check=True, stdout=subprocess.DEVNULL)
        return archive

    def review_software_recipe(self):
        selection = {name: value for name, value in self.recipe.items() if name != "bundle"}
        self.software_lock["recipe_sha256"] = hashlib.sha256(json.dumps(
            selection, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        (self.variant / "inputs/software.json").write_text(json.dumps(self.recipe, indent=2) + "\n")
        (self.variant / "inputs/locks/software.json").write_text(json.dumps(self.software_lock, indent=2) + "\n")

    def export_inputs(self):
        result = subprocess.run([
            sys.executable, "-B", str(self.variant / "build/export-inputs.py"),
            str(self.legacy), str(self.project / "artifacts/inputs"), "--legacy-cache",
        ], env=self.environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.recipe = json.loads((self.variant / "inputs/software.json").read_text())
        return self.project / self.recipe["bundle"]["path"]

    def prepare_inputs(self, name="normal", resolve=False):
        config = self.project / "work" / name / "config"
        shutil.copytree(self.variant / "live-build/config", config)
        product = config / "includes.chroot/etc/skel/.config/mise"
        product.mkdir(parents=True)
        (product / "config.toml").write_text("editable product default\n")
        root_product = config / "includes.chroot/root/.config/mc"
        root_product.mkdir(parents=True)
        (root_product / "ini").write_text("editable root default\n")
        environment = dict(self.environment)
        if resolve:
            environment["MIUBOMZ_RESOLVE_INPUTS"] = "1"
        result = subprocess.run([
            sys.executable, "-B", str(self.variant / "build/prepare-inputs.py"), str(config),
        ], env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        return config, result

    def test_export_to_fresh_cache_preserves_native_package_and_software_identity(self):
        original = software_inventory(self.software)
        bundle = self.export_inputs()
        descriptor = self.recipe["bundle"]
        self.assertEqual(descriptor["sha256"], hashlib.sha256(bundle.read_bytes()).hexdigest())
        self.assertEqual(descriptor["bytes"], bundle.stat().st_size)
        self.assertEqual(software_inventory(self.software), original)
        unpacked = self.project / "unpacked"
        unpacked.mkdir()
        subprocess.run(["tar", "--zstd", "-xf", str(bundle), "-C", str(unpacked)], check=True)
        self.assertEqual(software_inventory(unpacked / "software"), original)
        exported_assets = unpacked / "software/usr/share/fixture-assets"
        self.assertEqual((exported_assets / "helper").stat().st_ino,
                         (exported_assets / "helper-alias").stat().st_ino)
        self.assertEqual(os.readlink(exported_assets / "helper-link"), "helper")
        self.assertFalse((unpacked / "reference").exists())
        config, result = self.prepare_inputs()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(software_inventory(self.cache / "software"), original)
        for name, archive in self.archives.items():
            self.assertEqual((self.cache / "apt" / archive.name).read_bytes(), archive.read_bytes(), name)
        staged = config / "includes.chroot/usr/share/fixture-assets"
        self.assertEqual((staged / "helper").read_bytes(), self.executable.read_bytes())
        self.assertEqual(stat.S_IMODE(staged.stat().st_mode), 0o750)
        self.assertEqual(stat.S_IMODE((staged / "helper").stat().st_mode), 0o755)
        self.assertEqual((staged / "helper").stat().st_ino, (staged / "helper-alias").stat().st_ino)
        self.assertEqual(os.readlink(staged / "helper-link"), "helper")
        self.assertTrue((config / "includes.chroot/usr/share/independent-fixture/extra.txt").is_file())
        self.assertFalse((config / "includes.chroot/usr/share/not-selected.txt").exists())
        self.assertEqual((config / "includes.chroot/etc/skel/.config/mise/config.toml").read_text(),
                         "editable product default\n")
        self.assertEqual((config / "includes.chroot/root/.config/mc/ini").read_text(), "editable root default\n")
        self.assertFalse((config / "includes.chroot/root/not-selected.txt").exists())
        self.assertEqual(json.loads((config / "includes.chroot/usr/share/miubomz/software-lock.json").read_text()),
                         self.software_lock)
        self.assertEqual({path.name for path in (config / "packages.chroot").glob("*.deb")},
                         {self.archives[name].name for name in ("vendor-exported", "base-package")})
        media = config / "includes.binary"
        self.assertEqual((media / "pool/main/o/offline-grub" / self.archives["offline-grub"].name).read_bytes(),
                         self.archives["offline-grub"].read_bytes())
        index = media / "dists/forky/main/binary-amd64/Packages"
        self.assertIn("Package: offline-grub\n", index.read_text())
        self.assertTrue(index.with_suffix(".gz").is_file())
        self.assertIn("SHA256:", (media / "dists/forky/Release").read_text())
        self.assertTrue((config / "archives/locked-inputs.pref.chroot").is_file())
        self.assertFalse((config / "apt/locked-inputs.pref").exists())
        self.assertFalse(list((config / "archives").glob("*.pref.binary")))
        self.assertFalse((config / "package-lists/grub.list.binary").exists())
        self.assertEqual((self.variant / "live-build/config/package-lists/grub.list.binary").read_text(),
                         "offline-grub\n")
        cached = software_inventory(self.cache / "software")
        _, result = self.prepare_inputs("reused")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(software_inventory(self.cache / "software"), cached)

    def test_changed_native_recipe_requires_a_reviewed_normal_build_lock(self):
        self.export_inputs()
        (self.variant / "live-build/config/package-lists/00-platform.list.chroot").write_text("new-platform\n")
        _, result = self.prepare_inputs()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Native APT recipes changed", result.stdout)
        self.assertFalse(self.cache.exists())

    def test_mutable_bootstrap_cache_preserves_canonical_archive_identity(self):
        self.export_inputs()
        _, result = self.prepare_inputs()
        self.assertEqual(result.returncode, 0, result.stdout)
        archive = self.archives["vendor-exported"]
        canonical = self.cache / "apt" / archive.name
        bootstrap = self.cache / "bootstrap" / archive.name
        original = canonical.read_bytes()
        original_sha256 = hashlib.sha256(original).hexdigest()
        self.assertEqual(bootstrap.read_bytes(), original)
        self.assertNotEqual(bootstrap.stat().st_ino, canonical.stat().st_ino)
        replacement = b"native debootstrap replacement archive\n"
        bootstrap.write_bytes(replacement)
        self.assertEqual(canonical.read_bytes(), original)
        self.assertEqual(hashlib.sha256(canonical.read_bytes()).hexdigest(), original_sha256)
        verify_cached_inputs(self.cache, self.apt_lock, self.software_lock)
        config, result = self.prepare_inputs("mutated-bootstrap-reused")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(bootstrap.read_bytes(), replacement)
        self.assertEqual((config / "packages.chroot" / archive.name).read_bytes(), original)
        verify_cached_inputs(self.cache, self.apt_lock, self.software_lock)

    def test_resolution_uses_exported_archives_and_locally_built_versions(self):
        self.export_inputs()
        (self.variant / "live-build/config/package-lists/00-platform.list.chroot").write_text("new-platform\n")
        config, result = self.prepare_inputs("resolution", resolve=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual({path.name for path in (config / "packages.chroot").glob("*.deb")},
                         {self.archives["vendor-exported"].name})
        self.assertFalse((config / "includes.binary").exists())
        self.assertEqual((config / "package-lists/grub.list.binary").read_text(), "offline-grub\n")
        self.assertEqual((config / "package-lists/00-platform.list.chroot").read_text(), "new-platform\n")
        local_packages = config.parent / "local-packages"
        local_archive = self.build_package("miubomz-local", "0.2.0", local_packages)
        orchestration = (self.variant / "build/container-build.sh").read_text()
        start = orchestration.index("cp /work/local-packages/*.deb ")
        end = orchestration.index("\nCONFIGURE", start) + len("\nCONFIGURE")
        configuration = orchestration[start:end].replace("/work/", str(config.parent) + "/")
        environment = dict(self.environment, MIUBOMZ_RESOLVE_INPUTS="1", MIUBOMZ_PROFILE=str(self.variant))
        result = subprocess.run([
            "bash", "-eu", "-c", configuration,
        ], env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual({path.name for path in (config / "packages.chroot").glob("*.deb")},
                         {self.archives["vendor-exported"].name, local_archive.name})
        self.assertEqual((config / "packages.chroot" / local_archive.name).read_bytes(), local_archive.read_bytes())
        pins = (config / "archives/locked-inputs.pref.chroot").read_text()
        self.assertIn("Package: vendor-exported\nPin: version 1.0\n", pins)
        self.assertIn("Package: miubomz-local\nPin: version 0.2.0\n", pins)
        self.assertNotIn("base-package", pins)
        self.assertNotIn("offline-grub", pins)
        self.assertEqual((config / "package-lists/local.list.chroot").read_text(), "miubomz-local\n")

    def test_removed_declared_asset_is_not_staged_from_the_same_bundle(self):
        bundle = self.export_inputs()
        self.recipe["assets"] = [asset for asset in self.recipe["assets"]
                                 if asset["destination"] != "usr/share/independent-fixture"]
        self.review_software_recipe()
        config, result = self.prepare_inputs()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(bundle.is_file())
        self.assertTrue((self.cache / "software/usr/share/independent-fixture/extra.txt").is_file())
        self.assertFalse((config / "includes.chroot/usr/share/independent-fixture").exists())
        self.assertEqual(software_inventory(self.cache / "software"), self.software_lock["payload"])

    def test_reviewed_extension_change_rejects_unchanged_cached_payload(self):
        self.export_inputs()
        self.recipe["gnome_extensions"][0]["version"] = 2
        self.software_lock["gnome_extensions"] = self.recipe["gnome_extensions"]
        self.review_software_recipe()
        config, result = self.prepare_inputs()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Cached GNOME extensions differ from their declared UUIDs and versions", result.stdout)
        self.assertEqual(software_inventory(self.cache / "software"), self.software_lock["payload"])
        self.assertFalse((config / "includes.chroot/usr/share/fixture-assets").exists())

    def test_reviewed_tool_change_rejects_unchanged_cached_payload(self):
        self.export_inputs()
        self.recipe["mise_installed"] = {"node": ["22.0.0"]}
        self.software_lock["mise_installed"] = self.recipe["mise_installed"]
        self.review_software_recipe()
        config, result = self.prepare_inputs()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Cached mise_installed versions differ from their declared selections", result.stdout)
        self.assertEqual(software_inventory(self.cache / "software"), self.software_lock["payload"])
        self.assertFalse((config / "includes.chroot/usr/share/fixture-assets").exists())


if __name__ == "__main__":
    unittest.main()
