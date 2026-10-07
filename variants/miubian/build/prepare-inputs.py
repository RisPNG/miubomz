#!/usr/bin/python3
"""Prepare the declared, verified Miubian inputs for native live-build."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from image_inventory import input_bundle_identity, source_inputs, verify_cached_inputs, verify_software_selection


VARIANT = Path(__file__).resolve().parent.parent
PROJECT = VARIANT.parent.parent
CACHE = Path(os.environ.get("MIUBOMZ_CACHE_DIR", PROJECT / ".cache/miubian"))
RESOLVE_INPUTS = os.environ.get("MIUBOMZ_RESOLVE_INPUTS") == "1"


def configure_packages(config, local_packages=None):
    lock = json.loads((VARIANT / "inputs/locks/apt.json").read_text())
    current = source_inputs(VARIANT)
    recipe = {name: value for name, value in current.items()
              if name.startswith(("live-build/config/package-lists/", "live-build/config/archives/"))}
    if not RESOLVE_INPUTS and recipe != lock["recipe_sha256"]:
        raise SystemExit("Native APT recipes changed; resolve and review their input lock before building.")
    exported = set((VARIANT / "live-build/config/package-lists/05-exported-inputs.list.chroot").read_text().splitlines())
    versions = {package["name"]: package["version"] for package in lock["packages"]
                if not RESOLVE_INPUTS or package["name"] in exported}
    if local_packages is not None:
        for path in sorted(local_packages.glob("*.deb")):
            name, version = subprocess.check_output([
                "dpkg-deb", "--show", "--showformat=${Package}\t${Version}", str(path),
            ], text=True).split("\t")
            versions[name] = version
        (config / "package-lists/local.list.chroot").write_text(
            "\n".join(sorted(subprocess.check_output([
                "dpkg-deb", "--show", "--showformat=${Package}", str(path),
            ], text=True) for path in local_packages.glob("*.deb"))) + "\n")
    pins = "\n".join(
        f"Package: {name}\nPin: version {version}\nPin-Priority: 1001\n"
        for name, version in sorted(versions.items()))
    archives = config / "archives"
    archives.mkdir(parents=True, exist_ok=True)
    (archives / "locked-inputs.pref.chroot").write_text(pins)
    for path in config.joinpath("package-lists").glob("*.list.binary"):
        if not RESOLVE_INPUTS:
            path.unlink()


def main():
    config = Path(sys.argv[1])
    recipe = json.loads((VARIANT / "inputs/software.json").read_text())
    software_lock = json.loads((VARIANT / "inputs/locks/software.json").read_text())
    apt_lock = json.loads((VARIANT / "inputs/locks/apt.json").read_text())
    selection = {name: value for name, value in recipe.items() if name != "bundle"}
    fingerprint = hashlib.sha256(json.dumps(
        selection, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if fingerprint != software_lock["recipe_sha256"]:
        raise SystemExit("Software selections changed; resolve and review their input lock before building.")
    configure_packages(config)
    CACHE.mkdir(parents=True, exist_ok=True)
    if not (CACHE / "software").is_dir() or not (CACHE / "apt").is_dir():
        source = Path(os.environ.get("MIUBOMZ_INPUT_BUNDLE", PROJECT / recipe["bundle"]["path"]))
        if not source.is_file():
            raise SystemExit(f"The declared immutable input bundle is required for an empty cache: {source}")
        with source.open("rb") as stream:
            fingerprint = hashlib.file_digest(stream, "sha256").hexdigest()
        if fingerprint != recipe["bundle"]["sha256"] or source.stat().st_size != recipe["bundle"]["bytes"]:
            raise SystemExit(f"Input bundle differs from its declared SHA-256 or size: {source}")
        with tempfile.TemporaryDirectory(prefix=".miubian-inputs-", dir=CACHE.parent) as temporary:
            stage = Path(temporary)
            subprocess.run(["tar", "--zstd", "--extract", "--file", str(source),
                            "--directory", str(stage)], check=True)
            manifest = json.loads((stage / "manifest.json").read_text())
            if manifest != input_bundle_identity(apt_lock, software_lock):
                raise SystemExit("Bundle inventory differs from the tracked input bytes.")
            verify_cached_inputs(stage, apt_lock, software_lock)
            for name in ("apt", "software"):
                if (CACHE / name).exists():
                    shutil.rmtree(CACHE / name)
                (stage / name).rename(CACHE / name)
    else:
        verify_cached_inputs(CACHE, apt_lock, software_lock)

    verify_software_selection(CACHE / "software", recipe, software_lock)
    bootstrap = CACHE / "bootstrap"
    bootstrap.mkdir(exist_ok=True)
    subprocess.run(["cp", "--reflink=auto", "--update=none",
                    *[str(CACHE / package["filename"]) for package in apt_lock["packages"]],
                    str(bootstrap)], check=True)
    subprocess.run(["rsync", "-aH", "--recursive", "--from0", "--files-from=-", "--chown=0:0",
                    *["--exclude=/" + path for path in recipe["staging_excludes"]],
                    str(CACHE / "software") + "/",
                    str(config / "includes.chroot") + "/"],
                   input="\0".join(asset["destination"] for asset in recipe["assets"]).encode() + b"\0",
                   check=True)
    packages = config / "packages.chroot"
    packages.mkdir(parents=True, exist_ok=True)
    media = config / "includes.binary"
    exported = set((VARIANT / "live-build/config/package-lists/05-exported-inputs.list.chroot").read_text().splitlines())
    for package in apt_lock["packages"]:
        path = CACHE / package["filename"]
        if "live" in package["contexts"] and (not RESOLVE_INPUTS or package["name"] in exported):
            subprocess.run(["cp", "--reflink=auto", str(path), str(packages / path.name)], check=True)
        if "installer-media" in package["contexts"] and not RESOLVE_INPUTS:
            destination = media / "pool/main" / package["name"][0] / package["name"] / path.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["cp", "--reflink=auto", str(path), str(destination)], check=True)
    if not RESOLVE_INPUTS:
        index = media / "dists" / apt_lock["distribution"] / "main" / ("binary-" + apt_lock["architecture"]) / "Packages"
        index.parent.mkdir(parents=True, exist_ok=True)
        with index.open("w") as destination:
            subprocess.run(["apt-ftparchive", "packages", "pool/main"], cwd=media,
                           stdout=destination, check=True)
        with index.with_suffix(".gz").open("wb") as destination:
            subprocess.run(["gzip", "-9", "--stdout", str(index)], stdout=destination, check=True)
        release = index.parent.parent.parent / "Release"
        with release.open("w") as destination:
            subprocess.run(["apt-ftparchive", "release", str(release.parent.relative_to(media))],
                           cwd=media, stdout=destination, check=True)
    shared = config / "includes.chroot/usr/share/miubomz"
    shared.mkdir(parents=True, exist_ok=True)
    shutil.copy2(VARIANT / "inputs/locks/software.json", shared / "software-lock.json")


if __name__ == "__main__":
    main()
