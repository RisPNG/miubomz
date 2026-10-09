from pathlib import Path
import hashlib
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
                "Maintainer: Ris Peng <hello@rispeng.com>\n"
                "Build-Depends: debhelper-compat (= 13)\n"
                "Standards-Version: 4.7.0\nRules-Requires-Root: no\n\n"
                f"Package: {binary}\nArchitecture: {'any' if source == 'miubomz-settings' else 'all'}\n"
                "Description: native source export regression fixture\n")
            (root / "debian/changelog").write_text(
                f"{source} ({version}) unstable; urgency=medium\n\n"
                "  * Native source export regression fixture.\n\n"
                " -- Ris Peng <hello@rispeng.com>  Wed, 07 Oct 2026 00:00:00 +0000\n")
            (root / "debian/rules").write_text("#!/usr/bin/make -f\n\n%:\n\tdh $@\n")
            if source == "miubomz-settings":
                (root / "fixture.c").write_text("int main(void) { return 0; }\n")
                with (root / "debian/rules").open("a") as rules:
                    rules.write("\noverride_dh_auto_build:\n\t$(CC) -g -o fixture fixture.c\n"
                                "\noverride_dh_auto_clean:\n\trm -f fixture\n")
            (root / "debian/rules").chmod(0o755)
            (root / "fixture.txt").write_text(f"{source} {version}\n")
            (root / "debian" / (binary + ".install")).write_text(f"fixture.txt usr/share/{binary}\n")
            if source == "miubomz-settings":
                with (root / "debian" / (binary + ".install")).open("a") as install:
                    install.write(f"fixture usr/lib/{binary}\n")
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

    def test_native_debug_symbols_are_generated_for_declared_parent(self):
        package, = (self.release / "packages").glob("miubomz-defaults-dbgsym_*.deb")
        fields = subprocess.check_output([
            "dpkg-deb", "--field", str(package), "Package", "Source", "Version",
            "Auto-Built-Package", "Depends",
        ], text=True)
        self.assertIn("Auto-Built-Package: debug-symbols\n", fields)
        self.assertIn("Depends: miubomz-defaults (= 0.2.0)\n", fields)
        descriptor, = (self.release / "sources-miubomz-settings").glob("*.dsc")
        self.assertNotIn("dbgsym", descriptor.read_text())
        result = self.verify_export()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_only_genuine_native_debug_symbol_metadata_is_accepted(self):
        package, = (self.release / "packages").glob("miubomz-defaults-dbgsym_*.deb")
        original = package.read_bytes()
        directory = self.release / "sources-miubomz-settings"
        records = {path: path.read_bytes() for path in directory.iterdir()
                   if path.suffix in (".changes", ".buildinfo")}
        for field, replacement in (
                ("Package", "miubomz-other-dbgsym"), ("Source", "wrong-source"),
                ("Version", "9.8.7"), ("Auto-Built-Package", "manual"),
                ("Auto-Built-Package", None), ("Depends", "miubomz-other (= 0.2.0)")):
            with self.subTest(field=field, value=replacement), tempfile.TemporaryDirectory(
                    prefix="miubomz-debug-symbol-metadata-") as temporary:
                root = Path(temporary) / "package"
                subprocess.run(["dpkg-deb", "--raw-extract", str(package), str(root)],
                               check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                control = root / "DEBIAN/control"
                text = control.read_text()
                changed = re.sub(r"(?m)^" + field + r": .*\n", "" if replacement is None else
                                 f"{field}: {replacement}\n", text)
                self.assertNotEqual(changed, text)
                control.write_text(changed)
                try:
                    subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(root), str(package)],
                                   check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    for extension in ("buildinfo", "changes"):
                        record, = directory.glob("*." + extension)
                        lines = []
                        for line in record.read_text().splitlines():
                            match = re.fullmatch(r" ([0-9a-f]{32}|[0-9a-f]{40}|[0-9a-f]{64}) \d+ (.*)", line)
                            if match:
                                filename = match[2].split()[-1]
                                payload = (self.release / "packages" if filename.endswith(".deb")
                                           else directory) / filename
                                algorithm = {32: "md5", 40: "sha1", 64: "sha256"}[len(match[1])]
                                fingerprint = hashlib.new(algorithm, payload.read_bytes()).hexdigest()
                                line = f" {fingerprint} {payload.stat().st_size} {match[2]}"
                            lines.append(line)
                        record.write_text("\n".join(lines) + "\n")
                    result = self.verify_export()
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn("not an automatic debug-symbol package", result.stdout)
                finally:
                    package.write_bytes(original)
                    for record, content in records.items():
                        record.write_bytes(content)

    def test_debug_symbols_cannot_replace_or_disappear_from_native_binary_coverage(self):
        directory = self.release / "sources-miubomz-settings"
        for extension in ("buildinfo", "changes"):
            record, = directory.glob("*." + extension)
            content = record.read_bytes()
            for binaries in (b"miubomz-defaults", b"miubomz-defaults-dbgsym"):
                with self.subTest(record=extension, binaries=binaries):
                    record.write_bytes(re.sub(rb"(?m)^Binary: .*$", b"Binary: " + binaries, content))
                    try:
                        result = self.verify_export()
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                    finally:
                        record.write_bytes(content)

    def test_native_build_records_must_export_the_same_generated_binary_set(self):
        directory = self.release / "sources-miubomz-settings"
        buildinfo, = directory.glob("*.buildinfo")
        text = re.sub(r"(?m)^Binary: .*$", "Binary: miubomz-defaults", buildinfo.read_text())
        text = "\n".join(line for line in text.splitlines() if "miubomz-defaults-dbgsym_" not in line) + "\n"
        buildinfo.write_text(text)
        changes, = directory.glob("*.changes")
        lines = []
        for line in changes.read_text().splitlines():
            match = re.fullmatch(r" ([0-9a-f]{32}|[0-9a-f]{40}|[0-9a-f]{64}) \d+ (.*)", line)
            if match and match[2].split()[-1] == buildinfo.name:
                algorithm = {32: "md5", 40: "sha1", 64: "sha256"}[len(match[1])]
                fingerprint = hashlib.new(algorithm, buildinfo.read_bytes()).hexdigest()
                line = f" {fingerprint} {buildinfo.stat().st_size} {match[2]}"
            lines.append(line)
        changes.write_text("\n".join(lines) + "\n")
        result = self.verify_export()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("Native build records name different binary sets", result.stdout)

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
