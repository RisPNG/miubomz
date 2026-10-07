#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from image_inventory import installed_packages


def output(*command):
    return subprocess.check_output(command, text=True)


def package_identity(path):
    return tuple(output(
        "dpkg-deb", "--show", "--showformat=${Package}\t${Version}\t${Architecture}",
        str(path),
    ).split("\t"))


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


work = Path(sys.argv[1])
cache = Path(sys.argv[2])
artifact = Path(sys.argv[3])
frozen = cache / "reference/packages.chroot"
desired = json.loads(Path("/src/manifests/desired-packages.json").read_text())
reference = {
    (row["name"], row["version"], row["architecture"])
    for row in desired["packages"] if row["name"] != "chatgpt"
}

installed = installed_packages(work / "binary/live/filesystem.squashfs", work)
local = {
    package_identity(path): path
    for path in sorted((work / "local-packages").glob("*.deb"))
}
uninstalled_local = local.keys() - installed
if uninstalled_local:
    raise SystemExit("Source-built package versions missing from image: " + ", ".join(
        f"{name}={version}" for name, version, architecture in sorted(uninstalled_local)
    ))

missing = reference - installed
if missing:
    raise SystemExit("Reference package versions missing from image: " + ", ".join(
        f"{name}={version}" for name, version, architecture in sorted(missing)
    ))

media = {}
for stanza in (work / "binary/dists/forky/main/binary-amd64/Packages").read_text().split("\n\n"):
    fields = dict(line.split(": ", 1) for line in stanza.splitlines()
                  if ": " in line and not line.startswith(" "))
    if "Package" in fields:
        identity = fields["Package"], fields["Version"], fields["Architecture"]
        media[identity] = fields["Filename"]

inputs = {}
for package in sorted(frozen.glob("*.deb")):
    identity = package_identity(package)
    if identity in installed and identity not in local:
        inputs[identity] = (package, "frozen-reference")

candidates = sorted((work / "cache").glob("packages.*/*.deb"))
for package in candidates:
    identity = package_identity(package)
    if identity not in installed or identity in inputs or identity in local:
        continue
    destination = frozen / package.name
    subprocess.run(["cp", "--reflink=auto", str(package), str(destination)], check=True)
    inputs[identity] = (destination, "native-live-build")

for identity, package in local.items():
    if identity in installed:
        destination = frozen / package.name
        subprocess.run(["cp", "--reflink=auto", str(package), str(destination)], check=True)
        inputs[identity] = (destination, "source-built")

unfrozen = installed - inputs.keys()
if unfrozen:
    raise SystemExit("Package archives missing from native build cache: " + ", ".join(
        f"{name}={version}" for name, version, architecture in sorted(unfrozen)
    ))

installer_media = cache / "reference/installer-media"
installer_media.mkdir(exist_ok=True)
for directory in ("pool", "dists"):
    subprocess.run([
        "cp", "-a", "--reflink=auto", str(work / "binary" / directory),
        str(installer_media),
    ], check=True)


def record(identity, path, source, context):
    name, version, architecture = identity
    return {
        "name": name,
        "version": version,
        "architecture": architecture,
        "filename": str(path.relative_to(cache / "reference")),
        "sha256": digest(path),
        "bytes": path.stat().st_size,
        "source": source,
        "reference": identity in reference,
        "context": context,
    }


packages = [
    record(identity, path, source, "live")
    for identity, (path, source) in sorted(inputs.items())
]
packages.extend(
    record(identity, installer_media / filename, "native-live-build", "installer-media")
    for identity, filename in sorted(media.items())
)

locks = {
    path.name: digest(path) for path in sorted(Path("/src/manifests").glob("*.json"))
}
local_packages = []
for (name, version, architecture), path in sorted(local.items()):
    local_packages.append({
        "name": name,
        "version": version,
        "architecture": architecture,
        "filename": path.name,
        "sha256": digest(path),
        "bytes": path.stat().st_size,
        "source": "source-built",
    })

result = {
    "version": "0.1.0",
    "architecture": "amd64",
    "distribution": "forky",
    "reference_snapshot": desired["reference_snapshot"],
    "input_sha256": locks,
    "installed_packages": len(installed),
    "media_packages": len(media),
    "local_packages": local_packages,
    "packages": packages,
}
serialized = json.dumps(result, indent=2) + "\n"
(cache / "reference/build-inputs.json").write_text(serialized)
artifact.write_text(serialized)
print(f"Froze {len(packages)} package archives in {frozen}")
