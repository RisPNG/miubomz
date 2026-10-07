import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

import libcalamares


def target():
    return Path(libcalamares.globalstorage.value("rootMountPoint"))


def write(relative, text):
    path = target() / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def unsafe_io():
    write("etc/dpkg/dpkg.cfg.d/calamares-force-unsafe-io", "force-unsafe-io\n")


def unsafe_io_undo():
    (target() / "etc/dpkg/dpkg.cfg.d/calamares-force-unsafe-io").unlink()
    subprocess.run(["sync"], check=True)


def sources_media():
    medium = next(path for path in (Path("/run/live/medium"), Path("/run/initramfs/live"))
                  if path.is_mount())
    mounted = target() / medium.relative_to("/")
    mounted.mkdir(parents=True, exist_ok=True)
    subprocess.run(["mount", "--bind", str(medium), str(mounted)], check=True)
    libcalamares.globalstorage.insert("miubomzLiveMedium", str(medium))
    write("etc/apt/sources.list.d/debian-live-media.list",
          f"deb [trusted=yes] file:{medium} forky main\n")


def sources_media_unmount():
    medium = libcalamares.globalstorage.value("miubomzLiveMedium")
    subprocess.run(["umount", str(target() / medium.lstrip("/"))], check=True)
    (target() / "etc/apt/sources.list.d/debian-live-media.list").unlink()


def debian_uri(uri):
    hostname = urlsplit(uri).hostname or ""
    return hostname == "debian.org" or hostname.endswith(".debian.org")


def vendor_sources(text, suffix):
    if suffix == ".list":
        return "".join(line for line in text.splitlines(keepends=True)
                       if not (re.match(r"\s*deb(?:-src)?\s", line)
                               and any(debian_uri(uri) for uri in
                                       re.findall(r"https?://[^\s\]]+", line))))
    retained = []
    changed = False
    for paragraph in re.split(r"\n\s*\n", text):
        match = re.search(r"^URIs:\s*(.*(?:\n[ \t]+[^\n]+)*)", paragraph, re.M)
        if match:
            uris = [uri for uri in match[1].split() if not debian_uri(uri)]
            if not uris:
                changed = True
                continue
            if len(uris) != len(match[1].split()):
                changed = True
                paragraph = paragraph[:match.start(1)] + " ".join(uris) + paragraph[match.end(1):]
        if paragraph.strip():
            retained.append(paragraph.rstrip())
    if not changed:
        return text
    return "\n\n".join(retained) + ("\n" if retained else "")


def sources_final():
    for relative in (
            "etc/apt/preferences.d/locked-inputs.pref",
            "etc/apt/preferences.d/locked-inputs.pref.orig"):
        (target() / relative).unlink(missing_ok=True)
    directory = target() / "etc/apt/sources.list.d"
    for path in sorted(directory.glob("*")):
        if path.suffix in (".list", ".sources"):
            original = path.read_text()
            retained = vendor_sources(original, path.suffix)
            if retained.strip():
                if retained != original:
                    path.write_text(retained)
            else:
                path.unlink()
    main = target() / "etc/apt/sources.list"
    retained = vendor_sources(main.read_text(), ".list") if main.exists() else ""
    write("etc/apt/sources.list",
          "deb https://deb.debian.org/debian forky main non-free-firmware\n"
          "deb-src https://deb.debian.org/debian forky main non-free-firmware\n"
          + retained)
    version = subprocess.check_output([
        "chroot", str(target()), "dpkg-query", "--show", "--showformat=${Version}",
        "miubomz-defaults",
    ], text=True)
    write("var/lib/miubomz/installed", f"Miubomz {version}\n")


def initialize_target():
    root = target()
    filesystem, uuid = subprocess.check_output(
        ["findmnt", "--noheadings", "--output", "FSTYPE,UUID", "--target", str(root)],
        text=True).split()
    if filesystem == "btrfs":
        settings = json.loads((root / "usr/lib/miubomz/timeshift-default.json").read_text())
        settings["backup_device_uuid"] = uuid
        write("etc/timeshift/timeshift.json", json.dumps(settings, indent=2) + "\n")
    username = libcalamares.globalstorage.value("username")
    subprocess.run(["chroot", str(root), "/usr/lib/miubomz/initialize-user", username],
                   check=True)
    brew = root / "home/linuxbrew/.linuxbrew"
    if brew.is_dir():
        subprocess.run(["chroot", str(root), "chown", "-R", f"{username}:",
                        "/home/linuxbrew/.linuxbrew"], check=True)
    subprocess.run(["systemctl", "--root", str(root), "enable", "cron.service",
                    "miubomz-recovery-start.service", "grub-btrfsd.service"], check=True)


def bootloader_config():
    partitions = libcalamares.globalstorage.value("partitions")
    if any(partition.get("luksMapperName") for partition in partitions):
        write("etc/initramfs-tools/conf.d/initramfs-permissions", "UMASK=0077\n")
        subprocess.run(["chroot", str(target()), "apt-mark", "manual",
                        "cryptsetup-initramfs", "keyutils"], check=True)
    apt = ["chroot", str(target()), "apt-get",
           "-o", "Dir::Etc::sourcelist=/etc/apt/sources.list.d/debian-live-media.list",
           "-o", "Dir::Etc::sourceparts=-"]
    subprocess.run(apt + ["update"], check=True)
    package = "grub-efi-amd64" if libcalamares.globalstorage.value("firmwareType") == "efi" else "grub-pc"
    if package == "grub-pc":
        boot_loader = libcalamares.globalstorage.value("bootLoader")
        install_path = boot_loader["installPath"] if boot_loader else None
        selections = (
            f"grub-pc grub-pc/install_devices multiselect {install_path or ''}\n"
            f"grub-pc grub-pc/install_devices_empty boolean {'false' if install_path else 'true'}\n"
        )
        subprocess.run(["chroot", str(target()), "debconf-set-selections"],
                       input=selections, text=True, check=True)
    subprocess.run(apt + ["-y", "--no-install-recommends", "install", package], check=True,
                   env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"})
    write("etc/default/grub.d/20-miubomz-installer.cfg", "GRUB_DISABLE_OS_PROBER=false\n")
