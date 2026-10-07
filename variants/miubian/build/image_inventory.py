import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def installed_packages(filesystem, temporary_parent):
    with tempfile.TemporaryDirectory(prefix="miubomz-package-state-", dir=temporary_parent) as temporary:
        status = subprocess.check_output([
            "unsquashfs", "-cat", str(filesystem), "var/lib/dpkg/status",
        ])
        (Path(temporary) / "status").write_bytes(status)
        rows = subprocess.check_output([
            "dpkg-query", f"--admindir={temporary}", "-W",
            "-f=${Package}\t${Version}\t${Architecture}\t${Status}\n",
        ], text=True)
    packages = set()
    for line in rows.splitlines():
        name, version, architecture, status = line.split("\t")
        if status == "install ok installed":
            packages.add((name, version, architecture))
    return packages


def source_inputs(variant):
    sources = [variant / "release.json", variant / "inputs/software.json"]
    sources.extend(sorted((variant / "inputs/locks").glob("*.json")))
    for directory in ("live-build", "integration", "packages/calamares", "build", "tests/image"):
        sources.extend(sorted((variant / directory).rglob("*")))
    inventory = {}
    for path in sources:
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            with path.open("rb") as source:
                inventory[str(path.relative_to(variant))] = hashlib.file_digest(source, "sha256").hexdigest()
    return inventory


def software_inventory(root):
    digest = hashlib.sha256()
    modes = hashlib.sha256()
    modes.update(b"root\0" + str(root.lstat().st_mode).encode() + b"\0")
    files = 0
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root)).encode()
        modes.update(relative + b"\0" + str(path.lstat().st_mode).encode() + b"\0")
        if path.is_symlink():
            digest.update(b"symlink\0" + relative + b"\0" + os.readlink(path).encode())
        elif path.is_file():
            digest.update(b"file\0" + relative + b"\0")
            with path.open("rb") as source:
                while block := source.read(1024 * 1024):
                    digest.update(block)
            files += 1
    return {"sha256": digest.hexdigest(), "files": files, "modes_sha256": modes.hexdigest()}


def verify_cached_inputs(cache, apt_lock, software_lock):
    actual = software_inventory(cache / "software")
    if actual != software_lock["payload"]:
        raise SystemExit(f"Software payload differs from the tracked lock: {actual}")
    for package in apt_lock["packages"]:
        path = cache / package["filename"]
        with path.open("rb") as source:
            actual = hashlib.file_digest(source, "sha256").hexdigest()
        if actual != package["sha256"] or path.stat().st_size != package["bytes"]:
            raise SystemExit(f"Package archive differs from the tracked lock: {path}")


def verify_software_selection(root, recipe, lock):
    assets = {asset["destination"] for asset in recipe["assets"]}
    selected = set(recipe["flatpak_applications"] + recipe["flatpak_runtimes"])
    locked = {package["ref"]: package for package in lock["flatpaks"]}
    if selected != locked.keys():
        raise SystemExit("Flatpak selections differ from their reviewed input lock.")
    dependencies = {package["ref"]: package for package in lock["flatpak_dependencies"]}
    if selected or dependencies:
        if "var/lib/flatpak" not in assets:
            raise SystemExit("Flatpak selections require the declared var/lib/flatpak asset.")
        flatpak = root / "var/lib/flatpak"
        with tempfile.TemporaryDirectory(prefix="miubian-flatpak-inventory-") as temporary:
            installation = Path(temporary)
            for name in ("app", "runtime", "exports"):
                (installation / name).symlink_to((flatpak / name).resolve())
            repo = installation / "repo"
            repo.mkdir()
            for path in (flatpak / "repo").iterdir():
                if path.name in ("objects", "refs"):
                    (repo / path.name).symlink_to(path.resolve())
                elif path.is_file():
                    shutil.copy2(path, repo / path.name)
                else:
                    (repo / path.name).mkdir()
            environment = dict(os.environ, FLATPAK_SYSTEM_DIR=str(installation))
            refs = subprocess.check_output([
                "flatpak", "list", "--system", "--all", "--columns=ref",
            ], env=environment, text=True).splitlines()
            actual = {}
            for ref in refs:
                ref, origin, commit = subprocess.check_output([
                    "flatpak", "info", "--system", "--show-ref", "--show-commit", "--show-origin", ref,
                ], env=environment, text=True).split()
                actual[ref] = {"ref": ref, "commit": commit, "origin": origin}
            expected = {ref: {name: package[name] for name in ("ref", "commit", "origin")}
                        for ref, package in (locked | dependencies).items()}
            if actual != expected:
                raise SystemExit("Cached Flatpak deployments differ from their reviewed selections and commits.")
            remotes = dict(line.split("\t") for line in subprocess.check_output([
                "flatpak", "remotes", "--system", "--columns=name,url",
            ], env=environment, text=True).splitlines())
            if remotes != {recipe["flatpak_remote"]["name"]: recipe["flatpak_remote"]["url"]}:
                raise SystemExit("Cached Flatpak remotes differ from their declared origin.")

    extensions = root / "etc/skel/.local/share/gnome-shell/extensions"
    actual = {}
    if extensions.is_dir():
        for path in sorted(extensions.glob("*/metadata.json")):
            metadata = json.loads(path.read_text())
            if metadata["uuid"] != path.parent.name:
                raise SystemExit("Cached GNOME extension directory differs from its declared UUID.")
            actual[metadata["uuid"]] = {"version": metadata["version"], "upstream": metadata["url"]}
    expected = {extension["uuid"]: {name: extension[name] for name in ("version", "upstream")}
                for extension in recipe["gnome_extensions"]}
    locked_extensions = {extension["uuid"]: {name: extension[name] for name in ("version", "upstream")}
                         for extension in lock["gnome_extensions"]}
    if actual != expected or expected != locked_extensions:
        raise SystemExit("Cached GNOME extensions differ from their declared UUIDs and versions.")
    if expected and "etc/skel/.local/share/gnome-shell/extensions" not in assets:
        raise SystemExit("GNOME extension selections require their declared asset.")

    installs = root / "etc/skel/.local/share/mise/installs"
    actual = {}
    if installs.is_dir():
        with tempfile.TemporaryDirectory(prefix="miubian-mise-inventory-") as temporary:
            isolated = Path(temporary)
            (isolated / "data").mkdir()
            (isolated / "data/installs").symlink_to(installs.resolve())
            (isolated / "config.toml").touch()
            environment = dict(os.environ, MISE_OFFLINE="1", MISE_DATA_DIR=str(isolated / "data"),
                               MISE_CACHE_DIR=str(isolated / "cache"), MISE_STATE_DIR=str(isolated / "state"),
                               MISE_CONFIG_DIR=str(isolated / "config"),
                               MISE_CONFIG_FILE=str(isolated / "config.toml"),
                               MISE_GLOBAL_CONFIG_FILE=str(isolated / "config.toml"))
            tools = json.loads(subprocess.check_output([
                str((root / "usr/bin/mise").resolve()), "ls", "--installed", "--json",
            ], cwd=isolated, env=environment, text=True))
            actual = {name: sorted(tool["version"] for tool in versions if tool["installed"])
                      for name, versions in tools.items()}
    if actual != recipe["mise_installed"] or actual != lock["mise_installed"]:
        raise SystemExit("Cached mise_installed versions differ from their declared selections.")
    if actual and not {"usr/bin/mise", "etc/skel/.local/share/mise/installs"} <= assets:
        raise SystemExit("Mise selections require their declared executable and installs assets.")

    cellar = root / "home/linuxbrew/.linuxbrew/Cellar"
    actual = {}
    if cellar.is_dir():
        actual = {tool.name: sorted(path.name for path in tool.iterdir() if path.is_dir())
                  for tool in cellar.iterdir() if tool.is_dir()}
    if actual != recipe["homebrew_cellar"] or actual != lock["homebrew_cellar"]:
        raise SystemExit("Cached homebrew_cellar versions differ from their declared selections.")
    if actual and "home/linuxbrew/.linuxbrew" not in assets:
        raise SystemExit("Homebrew selections require their declared prefix asset.")

    pyenv = root / "etc/skel/.cache/mise/python/pyenv"
    commit = subprocess.check_output([
        "git", "--git-dir=" + str(pyenv / ".git"), "rev-parse", "HEAD",
    ], text=True).strip() if pyenv.is_dir() else None
    if commit != recipe["mise_pyenv_commit"] or commit != lock["mise_pyenv_commit"]:
        raise SystemExit("Cached pyenv commit differs from its declared selection.")
    if commit and "etc/skel/.cache/mise/python/pyenv" not in assets:
        raise SystemExit("The pyenv selection requires its declared asset.")


def input_bundle_identity(apt_lock, software_lock):
    packages = [{name: package[name] for name in
                 ("name", "version", "architecture", "filename", "sha256", "bytes")}
                for package in apt_lock["packages"]]
    packages.sort(key=lambda package: (package["name"], package["version"], package["architecture"], package["filename"]))
    fingerprint = hashlib.sha256(json.dumps(
        packages, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"schema": 1, "software": software_lock["payload"], "apt_sha256": fingerprint}
