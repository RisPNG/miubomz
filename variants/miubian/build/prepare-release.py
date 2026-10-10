#!/usr/bin/env python3
"""Prepare verified image exports for a multipart GitHub release."""

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess


VARIANT = Path(__file__).resolve().parent.parent
PART_BYTES = 2_000_000_000

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("artifacts", type=Path)
parser.add_argument("destination", type=Path)
parser.add_argument("--repository", required=True)
parser.add_argument("--commit", required=True)
parser.add_argument("--tag", required=True)
parser.add_argument("--part-bytes", type=int, default=PART_BYTES)
arguments = parser.parse_args()
if not 0 < arguments.part_bytes < 2 ** 31:
    parser.error("Each release part must be smaller than 2 GiB.")

release = json.loads((VARIANT / "release.json").read_text())
if arguments.tag != f"miubian-{release['version']}":
    parser.error(f"The tag must match the release version: miubian-{release['version']}")
artifact = release["artifact"]
source = arguments.artifacts.resolve()
destination = arguments.destination.resolve()
destination.mkdir(parents=True, exist_ok=False)
subprocess.run(["sha256sum", "--check", artifact + ".iso.sha256"], cwd=source, check=True)
subprocess.run(["split", "--bytes=" + str(arguments.part_bytes), "--numeric-suffixes=0",
                "--suffix-length=3", str(source / (artifact + ".iso")),
                str(destination / (artifact + ".iso.part"))], check=True)
parts = sorted(destination.glob(artifact + ".iso.part[0-9][0-9][0-9]"))

for suffix in (".iso.sha256", ".packages", ".build.json", ".inputs.json"):
    shutil.copy2(source / (artifact + suffix), destination / (artifact + suffix))
for category in ("packages", "sources"):
    subprocess.run(["tar", "--create", "--zstd", "--sort=name", "--mtime=@0", "--owner=0",
                    "--group=0", "--numeric-owner", "--file",
                    str(destination / (artifact + "." + category + ".tar.zst")),
                    "--directory", str(source / category), artifact], check=True)

bundle = json.loads((VARIANT / "inputs/software.json").read_text())["bundle"]
provenance = {
    "schema": 1,
    "repository": arguments.repository,
    "commit": arguments.commit,
    "tag": arguments.tag,
    "version": release["version"],
    "architecture": release["architecture"],
    "artifact": artifact,
    "input_bundle": bundle,
    "iso_parts": [path.name for path in parts],
}
(destination / "release.json").write_text(json.dumps(provenance, indent=2) + "\n")

image_name = shlex.quote(artifact + ".iso")
checksum_name = shlex.quote(artifact + ".iso.sha256")
part_names = " ".join(shlex.quote(path.name) for path in parts)
joiner = destination / "join-iso.sh"
joiner.write_text(
    "#!/usr/bin/env bash\nset -euo pipefail\n"
    'cd -- "$(dirname -- "${BASH_SOURCE[0]}")"\n'
    f"if [[ -e {image_name} ]]; then\n"
    f"    printf '%s\\n' 'The ISO already exists. Move it before joining these parts.' >&2\n"
    "    exit 1\nfi\n"
    "sha256sum --check SHA256SUMS\n"
    f"temporary={image_name}.partial\n"
    "trap 'rm -f -- \"$temporary\"' EXIT\n"
    "trap 'exit 1' HUP INT TERM\n"
    f"cat -- {part_names} > \"$temporary\"\n"
    f"mv -- \"$temporary\" {image_name}\n"
    f"sha256sum --check {checksum_name}\n"
)
joiner.chmod(0o755)
(destination / "NOTES.md").write_text(
    f"Miubian {release['version']}, built from `{arguments.commit}` tagged `{arguments.tag}`.\n\n"
    "Download all release assets into one folder, then run:\n\n"
    "```sh\nbash join-iso.sh\n```\n\n"
    f"This checks the downloaded files and reconstructs `{artifact}.iso`. "
    "The ISO parts are not independently bootable. The source and Debian package archives "
    "contain the matching build exports. `release.json` records the commit and locked input bundle.\n\n"
    "The automated build checks the integration tests and image contents. "
    "Boot, installation and recovery checks still require separate VM testing.\n"
)
checksums = []
for path in sorted(destination.iterdir()):
    if path.stat().st_size >= 2 ** 31:
        raise SystemExit(f"Release asset exceeds GitHub's limit: {path.name}")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    checksums.append(digest + "  " + path.name + "\n")
(destination / "SHA256SUMS").write_text("".join(checksums))
print(destination)
