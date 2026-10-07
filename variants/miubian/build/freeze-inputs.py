#!/usr/bin/python3
"""Record the exact declared and source-built inputs of a completed image."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from image_inventory import installed_packages, source_inputs


variant = Path(__file__).resolve().parent.parent
release = json.loads((variant / "release.json").read_text())
lock = json.loads((variant / "inputs/locks/apt.json").read_text())
work = Path(sys.argv[1])
cache = Path(sys.argv[2])
artifact = Path(sys.argv[3])
resolve = os.environ.get("MIUBOMZ_RESOLVE_INPUTS") == "1"
installed = installed_packages(work / "binary/live/filesystem.squashfs", work)
locked = {(p["name"], p["version"], p["architecture"]): p for p in lock["packages"]}
local = {}
local_packages = []
for path in sorted((work / "local-packages").glob("*.deb")):
    identity = tuple(subprocess.check_output([
        "dpkg-deb", "--show", "--showformat=${Package}\t${Version}\t${Architecture}", str(path),
    ], text=True).split("\t"))
    with path.open("rb") as source:
        fingerprint = hashlib.file_digest(source, "sha256").hexdigest()
    local[identity] = path
    name, version, architecture = identity
    local_packages.append({"name": name, "version": version, "architecture": architecture,
                           "filename": path.name, "sha256": fingerprint, "bytes": path.stat().st_size,
                           "source": "source-built"})
required = {identity for identity, package in locked.items() if "live" in package["contexts"]} | local.keys()
missing = required - installed
if not resolve and missing:
    raise SystemExit("Declared package versions missing from image: " + ", ".join(
        f"{name}={version}" for name, version, architecture in sorted(missing)))
unlocked = installed - required
if not resolve and unlocked:
    raise SystemExit("Installed package versions missing from the reviewed lock: " + ", ".join(
        f"{name}={version}" for name, version, architecture in sorted(unlocked)))

media = {}
indexes = work / "binary/dists" / release["distribution"]
for index in sorted(indexes.glob("*/binary-*/Packages")):
    for stanza in index.read_text().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in stanza.splitlines()
                      if ": " in line and not line.startswith(" "))
        if "Package" in fields:
            identity = fields["Package"], fields["Version"], fields["Architecture"]
            media[identity] = fields
required_media = {identity for identity, package in locked.items() if "installer-media" in package["contexts"]}
if not resolve and media.keys() != required_media:
    raise SystemExit("Offline installer repository differs from its reviewed package closure.")

if resolve:
    if local.keys() - installed:
        raise SystemExit("Source-built package versions are missing from the resolved image.")
    archives = {identity: cache / package["filename"] for identity, package in locked.items()}
    candidates = sorted((work / "cache").glob("packages.*/*.deb"))
    candidates.extend(sorted((work / "binary/pool").rglob("*.deb")))
    for path in candidates:
        identity = tuple(subprocess.check_output([
            "dpkg-deb", "--show", "--showformat=${Package}\t${Version}\t${Architecture}", str(path),
        ], text=True).split("\t"))
        archives[identity] = path
    exported = set((variant / "live-build/config/package-lists/05-exported-inputs.list.chroot").read_text().splitlines())
    for identity, package in locked.items():
        if package["name"] in exported:
            archives[identity] = cache / package["filename"]
    resolved = {}
    for identity in sorted((installed - local.keys()) | media.keys()):
        path = archives.get(identity)
        if path is None or not path.is_file():
            raise SystemExit(f"Resolved package archive is missing from native build outputs: {identity}")
        destination = cache / "apt" / path.name
        if path.resolve() != destination.resolve():
            subprocess.run(["cp", "--reflink=auto", str(path), str(destination)], check=True)
        with destination.open("rb") as source:
            fingerprint = hashlib.file_digest(source, "sha256").hexdigest()
        name, version, architecture = identity
        contexts = (["live"] if identity in installed else []) + (["installer-media"] if identity in media else [])
        resolved[identity] = {"name": name, "version": version, "architecture": architecture,
                              "filename": "apt/" + destination.name, "sha256": fingerprint,
                              "bytes": destination.stat().st_size, "contexts": sorted(contexts),
                              "provenance": "exported-package" if name in exported else "native-package-archive"}
    lock = {"schema": 1, "architecture": release["architecture"], "distribution": release["distribution"],
            "recipe_sha256": {name: value for name, value in source_inputs(variant).items()
                              if name.startswith(("live-build/config/package-lists/", "live-build/config/archives/"))},
            "packages": list(resolved.values())}
    Path(sys.argv[4]).write_text(json.dumps(lock, indent=2) + "\n")
    locked = resolved

packages = []
for identity, package in sorted(locked.items()):
    path = cache / package["filename"]
    with path.open("rb") as source:
        fingerprint = hashlib.file_digest(source, "sha256").hexdigest()
    if fingerprint != package["sha256"] or path.stat().st_size != package["bytes"]:
        raise SystemExit(f"Consumed archive differs from the tracked lock: {path}")
    for context in package["contexts"]:
        record = {key: package[key] for key in ("name", "version", "architecture", "filename", "sha256", "bytes")}
        record.update(source="locked-bundle", context=context)
        if context == "installer-media":
            shipped = work / "binary" / media[identity]["Filename"]
            with shipped.open("rb") as source:
                fingerprint = hashlib.file_digest(source, "sha256").hexdigest()
            if fingerprint != package["sha256"]:
                raise SystemExit(f"Shipped offline archive differs from the tracked lock: {shipped}")
            record["media_filename"] = media[identity]["Filename"]
        packages.append(record)
for package in local_packages:
    packages.append(dict(package, context="live"))

result = {"version": release["version"], "variant": release["variant"],
          "architecture": release["architecture"], "distribution": release["distribution"],
          "input_sha256": source_inputs(variant), "installed_packages": len(installed),
          "media_packages": len(media), "local_packages": local_packages, "packages": packages,
          "resolution_candidate": resolve}
if resolve:
    with Path(sys.argv[4]).open("rb") as source:
        result["candidate_apt_lock_sha256"] = hashlib.file_digest(source, "sha256").hexdigest()
serialized = json.dumps(result, indent=2) + "\n"
artifact.write_text(serialized)
(cache / "build-inputs.json").write_text(serialized)
print(f"Recorded {len(packages)} exact image and offline-media package inputs")
