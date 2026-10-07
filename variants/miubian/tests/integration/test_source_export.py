from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True
VARIANT = Path(__file__).resolve().parents[2]


class SourceExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="miubomz-native-source-export-")
        cls.addClassCleanup(temporary.cleanup)
        cls.baseline = Path(temporary.name) / "baseline"
        (cls.baseline / "packages").mkdir(parents=True)
        for source, binary, version in (
                ("miubomz-settings", "miubomz-defaults", "0.2.0"),
                ("calamares", "calamares", "3.4.2")):
            parent = Path(temporary.name) / "builds" / source
            root = parent / source
            (root / "debian/source").mkdir(parents=True)
            (root / "debian/source/format").write_text("3.0 (native)\n")
            (root / "debian/control").write_text(
                f"Source: {source}\nSection: misc\nPriority: optional\n"
                "Maintainer: Miubomz <miubomz@localhost>\n"
                "Build-Depends: debhelper-compat (= 13)\n"
                "Standards-Version: 4.7.0\nRules-Requires-Root: no\n\n"
                f"Package: {binary}\nArchitecture: all\n"
                "Description: native source export regression fixture\n")
            (root / "debian/changelog").write_text(
                f"{source} ({version}) unstable; urgency=medium\n\n"
                "  * Native source export regression fixture.\n\n"
                " -- Miubomz <miubomz@localhost>  Wed, 07 Oct 2026 00:00:00 +0000\n")
            (root / "debian/rules").write_text("#!/usr/bin/make -f\n\n%:\n\tdh $@\n")
            (root / "debian/rules").chmod(0o755)
            (root / "fixture.txt").write_text(f"{source} {version}\n")
            (root / "debian" / (binary + ".install")).write_text(f"fixture.txt usr/share/{binary}\n")
            result = subprocess.run([
                "dpkg-buildpackage", "-us", "-uc", "-sa",
            ], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            if result.returncode:
                raise AssertionError(result.stdout)
            exported = cls.baseline / ("sources-" + source)
            exported.mkdir()
            for path in parent.iterdir():
                if path.is_file():
                    destination = cls.baseline / "packages" if path.suffix == ".deb" else exported
                    shutil.copy2(path, destination / path.name)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="miubomz-source-export-check-")
        self.addCleanup(temporary.cleanup)
        self.release = Path(temporary.name) / "release"
        shutil.copytree(self.baseline, self.release)

    def verify_export(self):
        return subprocess.run([
            "perl", str(VARIANT / "build/verify-source-packages.pl"),
            str(self.release / "packages"),
            str(self.release / "sources-miubomz-settings"),
            str(self.release / "sources-calamares"),
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)

    def test_complete_native_source_and_binary_exports_are_accepted(self):
        result = self.verify_export()
        self.assertEqual(result.returncode, 0, result.stdout)
        for source in ("miubomz-settings", "calamares"):
            self.assertIn(f"Verified {source} source package and native build records", result.stdout)

    def test_each_missing_native_source_component_is_rejected(self):
        for source in ("miubomz-settings", "calamares"):
            for extension in ("dsc", "tar.xz", "buildinfo", "changes"):
                with self.subTest(source=source, missing=extension):
                    path, = (self.release / ("sources-" + source)).glob("*." + extension)
                    content = path.read_bytes()
                    path.unlink()
                    try:
                        result = self.verify_export()
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                    finally:
                        path.write_bytes(content)

    def test_duplicate_source_descriptors_are_rejected(self):
        for source in ("miubomz-settings", "calamares"):
            with self.subTest(source=source):
                directory = self.release / ("sources-" + source)
                descriptor, = directory.glob("*.dsc")
                duplicate = directory / (source + "_duplicate.dsc")
                shutil.copy2(descriptor, duplicate)
                try:
                    result = self.verify_export()
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn(f"Expected one complete {source} source package", result.stdout)
                finally:
                    duplicate.unlink()

    def test_each_corrupt_native_source_component_is_rejected(self):
        for source in ("miubomz-settings", "calamares"):
            for extension in ("dsc", "tar.xz", "buildinfo", "changes"):
                with self.subTest(source=source, corrupt=extension):
                    path, = (self.release / ("sources-" + source)).glob("*." + extension)
                    content = path.read_bytes()
                    if extension == "tar.xz":
                        offset = len(content) // 2
                        changed = content[:offset] + bytes([content[offset] ^ 1]) + content[offset + 1:]
                    elif extension == "changes":
                        changed = re.sub(rb"(?m)^Source: .*$", b"Source: wrong-source", content)
                    else:
                        offset = content.index(b"Checksums-Sha256:\n ") + len(b"Checksums-Sha256:\n ")
                        changed = content[:offset] + (b"0" if content[offset:offset + 1] != b"0" else b"1") + content[offset + 1:]
                    self.assertNotEqual(changed, content)
                    path.write_bytes(changed)
                    try:
                        result = self.verify_export()
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                    finally:
                        path.write_bytes(content)

    def test_native_build_records_must_match_source_version_and_binary_set(self):
        for source in ("miubomz-settings", "calamares"):
            for extension in ("changes", "buildinfo"):
                path, = (self.release / ("sources-" + source)).glob("*." + extension)
                content = path.read_bytes()
                for field, replacement in ((b"Source", b"wrong-source"), (b"Version", b"9.8.7"),
                                           (b"Binary", b"wrong-binary")):
                    with self.subTest(source=source, record=extension, field=field):
                        changed = re.sub(rb"(?m)^" + field + rb": .*$", field + b": " + replacement, content)
                        self.assertNotEqual(changed, content)
                        path.write_bytes(changed)
                        try:
                            result = self.verify_export()
                            self.assertNotEqual(result.returncode, 0, result.stdout)
                        finally:
                            path.write_bytes(content)

    def test_released_native_binary_byte_changes_are_rejected(self):
        for path in sorted((self.release / "packages").glob("*.deb")):
            with self.subTest(binary=path.name):
                content = path.read_bytes()
                offset = len(content) // 2
                path.write_bytes(content[:offset] + bytes([content[offset] ^ 1]) + content[offset + 1:])
                self.assertEqual(path.stat().st_size, len(content))
                try:
                    result = self.verify_export()
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                finally:
                    path.write_bytes(content)


if __name__ == "__main__":
    unittest.main()
