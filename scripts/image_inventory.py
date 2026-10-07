from pathlib import Path
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
