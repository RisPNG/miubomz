import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True
VARIANT = Path(__file__).resolve().parents[2]
RELEASE = json.loads((VARIANT / "release.json").read_text())
ARTIFACT = RELEASE["artifact"]
TAG = "miubian-" + RELEASE["version"]


class ReleaseWorkflowTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="miubomz-release-check-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.release = self.root / "release"
        self.image = b"verified native image bytes"
        (self.artifacts / (ARTIFACT + ".iso")).write_bytes(self.image)
        (self.artifacts / (ARTIFACT + ".iso.sha256")).write_text(
            hashlib.sha256(self.image).hexdigest() + "  " + ARTIFACT + ".iso\n")
        for suffix in (".packages", ".build.json", ".inputs.json"):
            (self.artifacts / (ARTIFACT + suffix)).write_text("fixture\n")
        for category in ("sources", "packages"):
            directory = self.artifacts / category / ARTIFACT
            directory.mkdir(parents=True)
            (directory / "fixture.txt").write_text(category + " export\n")

    def prepare(self, part_bytes="7", tag=TAG):
        return subprocess.run([
            sys.executable, str(VARIANT / "build/prepare-release.py"),
            str(self.artifacts), str(self.release), "--repository", "RisPNG/miubomz",
            "--commit", "a" * 40, "--tag", tag, "--part-bytes", part_bytes,
        ], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)

    def test_release_reassembles_verified_bytes_and_records_tagged_source(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stdout)
        provenance = json.loads((self.release / "release.json").read_text())
        self.assertEqual(provenance["commit"], "a" * 40)
        self.assertEqual(provenance["tag"], TAG)
        self.assertEqual(provenance["version"], RELEASE["version"])
        self.assertEqual(len(provenance["iso_parts"]), 4)
        for category in ("packages", "sources"):
            contents = subprocess.check_output([
                "tar", "--zstd", "--extract", "--to-stdout", "--file",
                str(self.release / (ARTIFACT + "." + category + ".tar.zst")),
                ARTIFACT + "/fixture.txt",
            ], text=True)
            self.assertEqual(contents, category + " export\n")
        result = subprocess.run(["bash", str(self.release / "join-iso.sh")],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual((self.release / (ARTIFACT + ".iso")).read_bytes(), self.image)

    def test_corrupted_download_is_rejected_before_joining(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stdout)
        next(self.release.glob("*.part000")).write_bytes(b"changed")
        result = subprocess.run(["bash", str(self.release / "join-iso.sh")],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertFalse((self.release / (ARTIFACT + ".iso")).exists())

    def test_existing_iso_is_preserved(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stdout)
        image = self.release / (ARTIFACT + ".iso")
        image.write_bytes(b"existing image")
        result = subprocess.run(["bash", str(self.release / "join-iso.sh")],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(image.read_bytes(), b"existing image")

    def test_changed_original_export_is_rejected(self):
        (self.artifacts / (ARTIFACT + ".iso")).write_bytes(b"changed original")
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(list(self.release.iterdir()), [])

    def test_release_parts_must_fit_github_asset_limit(self):
        result = self.prepare(str(2 ** 31))
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertFalse(self.release.exists())

    def test_tag_must_match_the_release_version_before_preparing_downloads(self):
        for tag in ("v" + RELEASE["version"], TAG + "-other"):
            with self.subTest(tag=tag):
                result = self.prepare(tag=tag)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertFalse(self.release.exists())

    def test_native_build_removes_its_container_on_success_and_failure(self):
        project = self.root / "project"
        build = project / "variants/miubian/build"
        build.mkdir(parents=True)
        shutil.copy2(VARIANT / "build/build.sh", build / "build.sh")
        commands = self.root / "commands"
        commands.mkdir()
        docker = commands / "docker"
        docker.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "with open(os.environ['DOCKER_LOG'], 'a') as log:\n"
            "    log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if sys.argv[1] == 'run':\n"
            "    raise SystemExit(int(os.environ['DOCKER_RESULT']))\n")
        docker.chmod(0o755)
        log = self.root / "docker.jsonl"
        for status in (0, 7):
            with self.subTest(status=status):
                log.write_text("")
                environment = os.environ.copy()
                environment.update({
                    "PATH": str(commands) + os.pathsep + environment["PATH"],
                    "DOCKER_LOG": str(log), "DOCKER_RESULT": str(status),
                    "MIUBOMZ_BUILDER_IMAGE": "fixture-builder",
                    "MIUBOMZ_BUILD_CONTAINER": "fixture-build-container",
                })
                result = subprocess.run(["bash", str(build / "build.sh")], env=environment,
                                        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                self.assertEqual(result.returncode, status, result.stdout)
                calls = [json.loads(line) for line in log.read_text().splitlines()]
                run = next(call for call in calls if call[0] == "run")
                self.assertEqual(run[run.index("--name") + 1], "fixture-build-container")
                self.assertEqual(calls[-1], ["container", "rm", "--force", "fixture-build-container"])


if __name__ == "__main__":
    unittest.main()
