#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
VARIANT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VARIANT / "build"))
from image_inventory import installed_packages, source_inputs


def output(*command):
    return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT)


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


iso = Path(sys.argv[1])
root = Path(sys.argv[2])
profile = json.loads((VARIANT / "release.json").read_text())
apt_lock = json.loads((VARIANT / "inputs/locks/apt.json").read_text())
software_lock = json.loads((VARIANT / "inputs/locks/software.json").read_text())
boot_report = output("xorriso", "-indev", str(iso), "-report_el_torito", "plain")
if "BIOS" not in boot_report or "UEFI" not in boot_report:
    raise SystemExit("ISO must contain both BIOS and UEFI boot entries")

with tempfile.TemporaryDirectory(prefix="miubomz-media-check-", dir=root.parent) as temporary:
    for boot_menu in ("/isolinux/live.cfg", "/boot/grub/grub.cfg"):
        extracted_menu = Path(temporary) / Path(boot_menu).name
        output("xorriso", "-osirrox", "on", "-indev", str(iso), "-extract", boot_menu, str(extracted_menu))
        live_commands = [line.split() for line in extracted_menu.read_text().splitlines()
                         if line.strip().startswith(("append ", "linux\t", "linux "))
                         and "boot=live" in line.split() and "nosplash" not in line.split()]
        if not live_commands or any("plymouth.enable=0" not in command for command in live_commands):
            raise SystemExit(f"Normal live entries must disable Plymouth: {boot_menu}")
    media_index = Path(temporary) / "Packages"
    output(
        "xorriso", "-osirrox", "on", "-indev", str(iso), "-extract",
        f"/dists/{profile['distribution']}/main/binary-{profile['architecture']}/Packages",
        str(media_index),
    )
    media_packages = "\n" + media_index.read_text()
    media_identities = set()
    for stanza in media_packages.split("\n\n"):
        fields = dict(line.split(": ", 1) for line in stanza.splitlines()
                      if ": " in line and not line.startswith(" "))
        if "Package" in fields:
            media_identities.add((fields["Package"], fields["Version"], fields["Architecture"]))
    for name in ("grub-pc", "grub-efi-amd64", "grub-efi-amd64-signed", "shim-signed"):
        if f"\nPackage: {name}\n" not in media_packages:
            raise SystemExit(f"Missing offline installer package: {name}")
    extracted_filesystem = Path(temporary) / "filesystem.squashfs"
    output(
        "xorriso", "-osirrox", "on", "-indev", str(iso), "-extract",
        "/live/filesystem.squashfs", str(extracted_filesystem),
    )
    native_filesystem = root.parent / "binary/live/filesystem.squashfs"
    filesystem_bytes = native_filesystem.stat().st_size
    filesystem_sha256 = digest(native_filesystem)
    if extracted_filesystem.stat().st_size != filesystem_bytes or digest(extracted_filesystem) != filesystem_sha256:
        raise SystemExit("ISO filesystem extents must preserve the complete native Squashfs")
    apt_report = output("unsquashfs", "-ll", str(extracted_filesystem), "etc/apt")
    if "locked-inputs.pref" in apt_report:
        raise SystemExit("Build-only APT configuration remains in image: locked-inputs.pref")
    package_identities = installed_packages(extracted_filesystem, root.parent)
    local_packages = {
        tuple(output("dpkg-deb", "--show", "--showformat=${Package}\t${Version}\t${Architecture}",
                     str(path)).split("\t"))
        for path in sorted((root.parent / "local-packages").glob("*.deb"))
    }
    if not local_packages:
        raise SystemExit("Native package build inventory is missing")
    missing_local = local_packages - package_identities
    if missing_local:
        raise SystemExit("Source-built package versions missing from image: " + ", ".join(
            f"{name}={version}" for name, version, architecture in sorted(missing_local)))
    for context, inventory in (("live", package_identities), ("installer-media", media_identities)):
        expected = {
            (row["name"], row["version"], row["architecture"])
            for row in apt_lock["packages"] if context in row["contexts"]
        }
        if context == "live":
            expected |= local_packages
        missing = expected - inventory
        if missing:
            raise SystemExit(f"Locked {context} package versions missing from image: " + ", ".join(
                f"{name}={version}" for name, version, architecture in sorted(missing)))
        unlocked = inventory - expected
        if unlocked:
            raise SystemExit(f"Unlocked {context} package versions remain in image: " + ", ".join(
                f"{name}={version}" for name, version, architecture in sorted(unlocked)))
    package_files = {}
    required_files = {
        "miubomz-defaults": (
            "/etc/dconf/db/miubomz.d/00-desktop",
            "/etc/sudoers.d/99-miubomz-admin",
            "/etc/polkit-1/rules.d/00-miubomz-admin.rules",
            "/etc/modules-load.d/miubomz-i2c.conf",
            "/usr/lib/systemd/zram-generator.conf.d/50-miubomz.conf",
            "/usr/lib/miubomz/initialize-user",
            "/usr/share/miubomz/skel/.bashrc",
        ),
        "miubomz-recovery": (
            "/etc/apt/apt.conf.d/80-miubomz-snapshots",
            "/etc/grub.d/41_snapshots-btrfs",
            "/usr/lib/miubomz/apt-pre-snapshot",
            "/usr/lib/miubomz/timeshift-default.json",
            "/usr/lib/systemd/system/miubomz-recovery-start.service",
        ),
        "miubomz-installer": (
            "/etc/calamares/settings.conf",
            "/usr/lib/python3/dist-packages/miubomz_installer.py",
            "/usr/share/applications/calamares-install-miubomz.desktop",
        ),
        "miubomz-live-settings": (
            "/usr/lib/live/config/0950-miubomz-software",
        ),
    }
    for package, paths in required_files.items():
        files = set(output("unsquashfs", "-cat", str(extracted_filesystem),
                           f"var/lib/dpkg/info/{package}.list").splitlines())
        missing = set(paths) - files
        if missing:
            raise SystemExit(f"Missing package-owned {package} files: " + ", ".join(sorted(missing)))
        if package == "miubomz-defaults" and "/etc/skel/.bashrc" in files:
            raise SystemExit("The Debian Bash skeleton must retain native package ownership")
        package_files[package] = list(paths)
    bash_files = set(output("unsquashfs", "-cat", str(extracted_filesystem),
                            "var/lib/dpkg/info/bash.list").splitlines())
    if "/etc/skel/.bashrc" not in bash_files:
        raise SystemExit("The Debian Bash package must own its native account skeleton")
    image_software_lock = json.loads(output(
        "unsquashfs", "-cat", str(extracted_filesystem), "usr/share/miubomz/software-lock.json"))
    if image_software_lock != software_lock:
        raise SystemExit("Image software inventory must match the tracked software lock")
    release_text = output("unsquashfs", "-cat", str(extracted_filesystem), "usr/lib/os-release")
    policy_root = Path(temporary) / "apt-policy"
    output(
        "unsquashfs", "-no-progress", "-d", str(policy_root),
        str(extracted_filesystem), "etc/apt", "var/lib/apt/lists", "var/lib/dpkg/status",
        "var/lib/miubomz",
        *(path.lstrip("/") for paths in required_files.values() for path in paths),
    )
    for paths in required_files.values():
        for path in paths:
            if not (policy_root / path.lstrip("/")).is_file():
                raise SystemExit(f"Package-owned file is missing from image: {path}")
    apt_update_policy = output(
        "apt-cache", "-o", f"Dir={policy_root}",
        "-o", f"Dir::State::status={policy_root}/var/lib/dpkg/status",
        "policy", "libmd0", "libgtk-4-1",
    )
    if (policy_root / "var/lib/miubomz/installed").exists():
        raise SystemExit("Installation marker must not be included in the live image")

os_release = dict(line.split("=", 1) for line in release_text.splitlines()
                  if line and not line.startswith("#"))
if os_release.get("ID") != "debian":
    raise SystemExit("Installed operating-system identity must remain Debian")

packages = {name: version for name, version, architecture in package_identities}
for name in ("gnome-shell", "calamares", *required_files):
    if name not in packages:
        raise SystemExit(f"Missing required package: {name}")
for name in required_files:
    if packages[name] != profile["version"]:
        raise SystemExit(f"Unexpected {name} version: {packages[name]}")
for name in ("miubomz-desktop", "miubomz-software"):
    if name in packages:
        raise SystemExit(f"Retired package remains in image: {name}")
if any("chatgpt" in name.lower() for name in packages):
    raise SystemExit("ChatGPT must be excluded from the image")

locks = source_inputs(VARIANT)

result = {
    "variant": profile["variant"],
    "version": profile["version"],
    "architecture": profile["architecture"],
    "distribution": profile["distribution"],
    "iso_bytes": iso.stat().st_size,
    "filesystem_bytes": filesystem_bytes,
    "filesystem_sha256": filesystem_sha256,
    "boot_firmware": ["bios", "uefi"],
    "live_plymouth_disabled": True,
    "offline_grub_packages": True,
    "packages": len(packages),
    "gnome_shell": packages["gnome-shell"],
    "local_packages": [
        {"name": name, "version": version, "architecture": architecture}
        for name, version, architecture in sorted(local_packages)
    ],
    "package_files": package_files,
    "apt_update_policy": apt_update_policy,
    "live_build": output("lb", "--version").strip(),
    "input_sha256": locks,
    "validation": "structural; boot and installed-system checks are recorded separately",
}
print(json.dumps(result, indent=2))
