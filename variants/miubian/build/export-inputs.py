#!/usr/bin/python3
"""Export verified input bytes as the immutable source bundle."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from image_inventory import input_bundle_identity, software_inventory, verify_software_selection


VARIANT = Path(__file__).resolve().parent.parent
PROJECT = VARIANT.parent.parent

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("cache", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--legacy-cache", action="store_true",
                    help="Import the verified first release's reference export cache")
arguments = parser.parse_args()
cache = arguments.cache.resolve()
destination = arguments.output.resolve()
destination.mkdir(parents=True, exist_ok=True)
apt_lock = json.loads((VARIANT / "inputs/locks/apt.json").read_text())
software_lock = json.loads((VARIANT / "inputs/locks/software.json").read_text())
recipe_path = VARIANT / "inputs/software.json"
recipe = json.loads(recipe_path.read_text())
software = cache / ("reference/includes.chroot" if arguments.legacy_cache else "software")
verify_software_selection(software, recipe, software_lock)
if software_inventory(software) != software_lock["payload"]:
    raise SystemExit("Exported software bytes differ from the tracked software lock.")
archive_paths = []
for package in apt_lock["packages"]:
    path = cache / package["filename"]
    if arguments.legacy_cache:
        path = cache / "reference/packages.chroot" / Path(package["filename"]).name
        if not path.exists():
            matches = list((cache / "reference/installer-media/pool").rglob(path.name))
            if len(matches) != 1:
                raise SystemExit(f"Expected one locked archive in exported media: {path.name}")
            path = matches[0]
    with path.open("rb") as source:
        fingerprint = hashlib.file_digest(source, "sha256").hexdigest()
    if fingerprint != package["sha256"] or path.stat().st_size != package["bytes"]:
        raise SystemExit(f"Exported package differs from the tracked lock: {path}")
    archive_paths.append(str(path.relative_to(cache)))
with tempfile.TemporaryDirectory(prefix=".miubian-input-export-", dir=destination) as temporary:
    stage = Path(temporary)
    manifest = input_bundle_identity(apt_lock, software_lock)
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (stage / "archives.list").write_bytes(b"\0".join(os.fsencode(path) for path in sorted(archive_paths)) + b"\0")
    archive = stage / "inputs.tar.zst"
    command = ["tar", "--create", "--file=-", "--sort=name", "--mtime=@0", "--owner=0", "--group=0",
               "--numeric-owner", "--transform=flags=rh;s,^reference/includes.chroot,software,",
               "--transform=flags=rh;s,^reference/packages.chroot/,apt/,",
               "--transform=flags=rh;s,^reference/installer-media/pool/.*/,apt/,",
               "--directory", str(stage), "manifest.json", "--directory", str(cache),
               str(software.relative_to(cache)), "--null", "--files-from", str(stage / "archives.list")]
    with archive.open("wb") as output:
        tar = subprocess.Popen(command, stdout=subprocess.PIPE)
        compression = subprocess.run(["zstd", "-3", "--threads=" + os.environ.get("MIUBOMZ_BUILD_JOBS", "4")],
                                     stdin=tar.stdout, stdout=output)
        tar.stdout.close()
        if tar.wait() != 0 or compression.returncode != 0:
            raise SystemExit("Native tar/zstd failed while exporting the immutable input bundle.")
    with archive.open("rb") as source:
        fingerprint = hashlib.file_digest(source, "sha256").hexdigest()
    final = destination / ("miubian-inputs-" + fingerprint + ".tar.zst")
    archive.replace(final)
    recipe = json.loads(recipe_path.read_text())
    recipe["bundle"] = {"path": str(final.relative_to(PROJECT)), "sha256": fingerprint,
                        "bytes": final.stat().st_size}
    recipe_path.write_text(json.dumps(recipe, indent=2) + "\n")
    final.with_suffix(final.suffix + ".sha256").write_text(fingerprint + "  " + final.name + "\n")
    if os.geteuid() == 0:
        owner = recipe_path.stat()
        for path in (final, final.with_suffix(final.suffix + ".sha256")):
            os.chown(path, owner.st_uid, owner.st_gid)
    print(json.dumps(recipe["bundle"], indent=2))
