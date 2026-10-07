#!/usr/bin/python3
"""Stage the reviewed reference artifacts for native Debian live-build."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


PROJECT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("MIUBOMZ_CACHE_DIR", PROJECT / ".cache/miubomz"))
FOREIGN_PACKAGES = (
    "actions-for-nautilus", "code", "libfuse2t64", "vivaldi-stable", "fetch",
    "ibus-mozc", "mozc-data", "mozc-server", "mozc-utils-gui", "spdx-licenses",
    "libavcodec62", "libavfilter11", "libavformat62",
    "linux-base-7.2.6+deb14-amd64", "linux-binary-7.2.6+deb14-amd64",
    "linux-modules-7.2.6+deb14-amd64", "linux-image-7.2.6+deb14-amd64",
    "coinor-libcgl1", "fonts-evertype-conakry", "fonts-fantasque-sans",
    "fonts-farsiweb", "fonts-ferrite-core", "fonts-gamaliel", "fonts-gfs-gazis",
    "fonts-gnutypewriter", "fonts-kode-mono", "gir1.2-gtk-4.0", "gir1.2-nautilus-4.1",
    "gstreamer1.0-gtk4", "gtk-update-icon-cache", "libgtk-4-1", "libgtk-4-bin",
    "libgtk-4-common", "libmd-dev", "libmd0", "libmozjs-140-0",
    "libnautilus-extension4", "nautilus-data", "nautilus", "python3-dbus",
)


def copy(source, destination, excludes=()):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir() and not source.is_symlink():
        destination.mkdir(parents=True, exist_ok=True)
        subprocess.run(["rsync", "-aH", "--chown=0:0", *["--exclude=" + item for item in excludes],
                        str(source) + "/", str(destination) + "/"], check=True)
    else:
        shutil.copy2(source, destination, follow_symlinks=False)


def digest_tree(root):
    digest = hashlib.sha256()
    files = 0
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root)).encode()
        if path.is_symlink():
            digest.update(b"symlink\0" + relative + b"\0" + os.readlink(path).encode())
        elif path.is_file():
            digest.update(b"file\0" + relative + b"\0")
            with path.open("rb") as stream:
                while block := stream.read(1024 * 1024):
                    digest.update(block)
            files += 1
    return {"sha256": digest.hexdigest(), "files": files}


def capture(reference):
    home = reference / "home/miubomz"
    output = CACHE / "reference/includes.chroot"
    mappings = [
        (home / ".themes", "usr/share/themes", ()),
        (home / ".local/share/icons", "usr/share/icons", ()),
        (home / ".icons/fluent", "usr/share/icons/fluent", ()),
        (home / ".icons/fluent-dark", "usr/share/icons/fluent-dark", ()),
        (home / ".local/share/gnome-shell/extensions", "etc/skel/.local/share/gnome-shell/extensions", ()),
        (home / ".local/share/blesh", "usr/share/blesh", ("cache.d", "tmp")),
        (home / ".local/bin/mise", "usr/bin/mise", ()),
        (home / ".local/bin/easyvenv", "usr/bin/easyvenv", ()),
        (home / ".local/bin/venv", "usr/bin/venv", ()),
        (reference / "usr/local/bin/starship", "usr/bin/starship", ()),
        (reference / "usr/bin/pacstall", "usr/bin/pacstall", ()),
        (reference / "usr/share/pacstall", "usr/share/pacstall", ()),
        (reference / "home/linuxbrew/.linuxbrew", "home/linuxbrew/.linuxbrew",
         ("var/log/*", "var/homebrew/locks/*", "**/.git/logs/***")),
        (home / ".local/share/mise/installs", "etc/skel/.local/share/mise/installs", ()),
        (home / ".cache/mise/python/pyenv", "etc/skel/.cache/mise/python/pyenv",
         ("**/.git/logs/***",)),
        (home / ".cargo/bin", "etc/skel/.cargo/bin", ()),
        (home / ".rustup/toolchains", "etc/skel/.rustup/toolchains", ()),
        (home / ".rustup/settings.toml", "etc/skel/.rustup/settings.toml", ()),
        (home / "AppImages/qview.appimage", "etc/skel/AppImages/qview.appimage", ()),
        (reference / "var/lib/pacstall/metadata/fetch-git", "var/lib/pacstall/metadata/fetch-git", ()),
    ]
    for name in ("scripts", "fonts", "script-opts"):
        mappings.append((home / ".config/mpv" / name, "etc/skel/.config/mpv/" + name, ()))
    mappings.append((reference / "var/lib/flatpak", "var/lib/flatpak",
                     (".changed", "appstream", "repo/tmp/*", "repo/state/*")))
    for name in ("microsoft.gpg", "vivaldi-16BD9233.gpg"):
        mappings.append((reference / "usr/share/keyrings" / name, "usr/share/keyrings/" + name, ()))
    for name in ("vscode.sources", "vivaldi.sources"):
        mappings.append((reference / "etc/apt/sources.list.d" / name, "etc/apt/sources.list.d/" + name, ()))
    origins = []
    for source, relative, excludes in mappings:
        print("Capturing", relative, flush=True)
        copy(source, output / relative, excludes)
        origins.append({"source": str(source.relative_to(reference)), "destination": relative})

    for link in output.rglob("*"):
        if link.is_symlink() and os.readlink(link).startswith("/home/miubomz/"):
            relative = os.readlink(link).removeprefix("/home/miubomz/")
            if relative.startswith(".themes/"):
                target = output / "usr/share/themes" / relative.removeprefix(".themes/")
            elif relative.startswith(".local/share/icons/"):
                target = output / "usr/share/icons" / relative.removeprefix(".local/share/icons/")
            elif relative.startswith(".icons/"):
                target = output / "usr/share/icons" / relative.removeprefix(".icons/")
            else:
                target = output / "etc/skel" / relative
            link.unlink()
            link.symlink_to(os.path.relpath(target, link.parent))

    mise_config = output / "etc/skel/.config/mise/config.toml"
    mise_config.parent.mkdir(parents=True, exist_ok=True)
    copy(home / ".config/mise/config.toml", mise_config)
    mc = output / "root/.config/mc/ini"
    mc.parent.mkdir(parents=True, exist_ok=True)
    mc.write_text("[Midnight-Commander]\nskin=yadt256-defbg\n")
    package_dir = CACHE / "reference/packages.chroot"
    package_dir.mkdir(parents=True, exist_ok=True)
    for package in FOREIGN_PACKAGES:
        if not list(package_dir.glob(package + "_*.deb")):
            subprocess.run(["dpkg-repack", "--root=" + str(reference), package], cwd=package_dir, check=True)

    environment = os.environ | {"FLATPAK_SYSTEM_DIR": str(reference / "var/lib/flatpak")}
    rows = subprocess.check_output(["flatpak", "list", "--system", "--columns=ref,origin,active,version"],
                                   env=environment, text=True).splitlines()
    flatpaks = []
    for row in rows:
        ref, origin, commit, *version = row.split("\t")
        kind = "app" if (reference / "var/lib/flatpak/app" / ref.split("/")[0]).exists() else "runtime"
        commit = subprocess.check_output(["flatpak", "info", "--system", "--show-commit", ref],
                                         env=environment, text=True).strip()
        flatpaks.append({"ref": kind + "/" + ref, "origin": origin,
                         "commit": commit, "version": version[0] if version else ""})
    lock = {"version": "0.1.0", "reference_snapshot": "Desired Results",
            "origins": origins, "flatpaks": flatpaks, "payload": digest_tree(output),
            "mise_installed": {tool.name: sorted(version.name for version in tool.iterdir()
                                                if re.fullmatch(r"\d+\.\d+\.\d+.*", version.name))
                               for tool in (output / "etc/skel/.local/share/mise/installs").iterdir()
                               if tool.is_dir()},
            "homebrew_cellar": {formula.name: sorted(p.name for p in formula.iterdir() if p.is_dir())
                               for formula in (output / "home/linuxbrew/.linuxbrew/Cellar").iterdir()},
            "foreign_packages": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in package_dir.glob("*.deb")}}
    (CACHE / "reference/software-lock.json").write_text(json.dumps(lock, indent=2) + "\n")
    (CACHE / "reference/complete").touch()


def configure_packages(config, local_packages=None):
    desired = json.loads((PROJECT / "manifests/desired-packages.json").read_text())
    excluded = {"chatgpt"}
    packages = [p["name"] + "=" + p["version"] for p in desired["packages"] if p["name"] not in excluded]
    (config / "package-lists/reference.list.chroot").write_text("\n".join(sorted(packages)) + "\n")
    apt = config / "apt"
    apt.mkdir(parents=True, exist_ok=True)
    versions = {}
    inputs = CACHE / "reference/build-inputs.json"
    if inputs.exists():
        versions.update({p["name"]: p["version"] for p in json.loads(inputs.read_text())["packages"]})
    versions.update({p["name"]: p["version"] for p in desired["packages"] if p["name"] not in excluded})
    if local_packages is not None:
        for package in sorted(local_packages.glob("*.deb")):
            name, version = subprocess.check_output(
                ["dpkg-deb", "--show", "--showformat=${Package}\t${Version}", str(package)],
                text=True,
            ).split("\t")
            versions[name] = version
    (apt / "reference.pref").write_text("\n".join(
        f'Package: {name}\nPin: version {version}\nPin-Priority: 1001\n'
        for name, version in sorted(versions.items())))


def main():
    config = Path(sys.argv[1])
    complete = CACHE / "reference/complete"
    if not complete.exists():
        reference = os.environ.get("MIUBOMZ_REFERENCE_ROOT")
        if not reference:
            raise SystemExit("Set MIUBOMZ_REFERENCE_ROOT to a read-only Desired Results snapshot for the first artifact capture.")
        capture(Path(reference))
    copy(CACHE / "reference/includes.chroot", config / "includes.chroot")
    copy(CACHE / "reference/packages.chroot", config / "packages.chroot")
    if (CACHE / "reference/installer-media/dists/forky").exists():
        archives = config / "archives"
        archives.mkdir(parents=True, exist_ok=True)
        (archives / "frozen-media.list.chroot").write_text(
            "deb [trusted=yes] file:///cache/reference/installer-media forky main\n")
        (archives / "frozen-media.pref.chroot").write_text(
            'Package: *\nPin: origin ""\nPin-Priority: 1001\n')
        for directory in ("pool", "dists"):
            copy(CACHE / "reference/installer-media" / directory,
                 config / "includes.binary" / directory)
    lock = CACHE / "reference/software-lock.json"
    copy(lock, config / "includes.chroot/usr/share/miubomz/software-lock.json")
    copy(PROJECT / "manifests/desired-packages.json", config / "includes.chroot/usr/share/miubomz/reference-packages.json")


if __name__ == "__main__":
    main()
