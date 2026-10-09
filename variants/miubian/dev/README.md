# Miubian development

Run these commands from the project root. The [variant overview](../README.md) explains the source folders, [setup-manual-steps.md](setup-manual-steps.md) records the maintained setup, and the [test overview](../tests/README.md) describes the checks.

## Requirements

Building needs mise, access to Docker's daemon and at least 100 GiB of free disk space for the current software and VM checks. [mise.toml](../../../mise.toml) pins Python and the GitHub CLI used to publish releases; install them with `mise install` when needed. Debian image-building tools run inside the builder.

The integration tests need native Debian utilities, including `debhelper`, `dpkg-dev`, `rsync`, `squashfs-tools` and `zstd`. Input export also uses Flatpak, Git and GNU tar, with noninteractive sudo to read builder-owned files. VM checks need QEMU, KVM access and OVMF for UEFI. These come from the host system.

## Building

An empty cache needs the input bundle declared in [software.json](../inputs/software.json). Provide it at the recorded project path, or use `MIUBOMZ_INPUT_BUNDLE=/path/to/bundle.tar.zst mise run build`. Its contents, permissions, size and SHA-256 are checked against the maintained inputs.

```sh
mise run test
mise run build
```

The build prepares verified inputs, builds the integration and patched Calamares packages, runs native live-build and validates the image before exporting it. Debian bootstrap and builder dependencies still use the network archive. Release inputs are locked, but the builder and ISO timestamps do not guarantee byte-identical rebuilds.

Output goes under `artifacts/miubian/`, using the artifact name in [release.json](../release.json):

- The ISO, its `.iso.sha256`, package list, `.build.json` image report and `.inputs.json` source and package inventory.
- `packages/<artifact>/` and `sources/<artifact>/`, with the native binary and source packages and their checksums.

Build logs are under `.build/miubian/logs/`. Resource and builder settings can be changed through:

| Setting | Default or purpose |
| --- | --- |
| `MIUBOMZ_BUILD_JOBS` | Four CPUs and parallel build jobs |
| `MIUBOMZ_BUILD_MEMORY` | `4g` builder memory limit |
| `MIUBOMZ_SQUASHFS_MEMORY` | `1G` compressor cache |
| `MIUBOMZ_DEBIAN_MIRROR` | Build-time Debian mirror; defaults to `https://deb.debian.org/debian` |
| `MIUBOMZ_BUILDER_IMAGE` | Use an explicitly prepared compatible builder image instead of rebuilding the default |
| `MIUBOMZ_BUILD_CONTAINER` | Override the build container's unique name; used by CI to stop it during cancellation |

The mutable bootstrap cache is separate from the locked package archives. Bootstrap can refresh its own copies without changing the release inputs.

## Tagged builds

[Build Miubian ISO](../../../.github/workflows/build-iso.yml) runs when a tag is pushed. It checks out that tag's exact commit, checks the integration behaviour, builds and validates the image, then publishes a GitHub release. The version and image name come from the tagged commit's `release.json`; tagging does not change them. The tagged commit must contain the workflow.

The runner is a Debian 13 VM on the Windows build machine. Give the VM four CPUs, 8 GiB RAM and enough storage to leave at least 100 GiB free after installing its tools and copying the input bundle. Keep its files on the VM's Linux filesystem. The Windows machine and VM must stay running and online while accepting builds.

Install the runner's native dependencies inside Debian:

```sh
sudo apt update
sudo apt install docker.io git curl ca-certificates debhelper dpkg-dev rsync squashfs-tools zstd
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out and back in so the Docker group takes effect. Follow GitHub's [Linux runner registration instructions](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners) for this repository, add the custom label `miubomz`, and run the runner as a service. Its default labels must include `self-hosted`, `linux` and `x64`. Mise installs the pinned host tools during each job.

Copy the bundle named in the tagged commit's `inputs/software.json` to `~/miubomz-inputs/` in the runner account. This directory must be outside the runner's checkout. To use another directory, set the repository Actions variable `MIUBOMZ_INPUTS_DIR` to its absolute path. The workflow checks the bundle's size and SHA-256 before building. Retain older bundles when older commits still need rebuilding, and copy each replacement bundle before tagging a commit that uses it.

Push a tag pointing at the intended commit. For example, replace `<commit-sha>` with the commit to release:

```sh
git tag v0.2.0 <commit-sha>
git push origin v0.2.0
```

The ISO exceeds GitHub's per-file release limit, so [prepare-release.py](../build/prepare-release.py) splits it into parts below 2 GiB. Download all release assets into one folder and run `bash join-iso.sh` to verify them and reconstruct the complete ISO. Each release also contains the package list, image and input reports, source and binary package archives, checksums and `release.json` with its tagged commit.

Releases remain drafts until all files upload successfully. A failed draft can be retried; a published release is preserved, so use a new tag for another build. CI stops its build container and removes its disposable build files, extracted cache and builder image afterwards. The supplied input bundles stay outside that cleanup. Docker retains shared base layers and build cache for later builds; maintain that cache on the dedicated VM as its available disk space changes. Automated image checks do not replace the boot, installation and recovery checks below.

## Changing the setup

Update [setup-manual-steps.md](setup-manual-steps.md) whenever Miubian adds, changes, or removes something above Debian Testing's live GNOME defaults. Keep it focused on the maintained setup, and make the matching changes in the [variant sources](../README.md).

Keep MiuUtil up to date whenever Miubian adds, changes, or removes part of the setup above Debian Testing's GNOME defaults. Make the applicable desktop, application and system changes available as selectable options, with matching descriptions, checks and applied settings. Preserve existing user data and preferences unrelated to the selected options. Installer-only behaviour stays in Calamares.

For Debian package selection changes, edit the live-build package lists or archive settings, then resolve them:

```sh
MIUBOMZ_RESOLVE_INPUTS=1 mise run build
```

This exports `.apt-lock.candidate.json` and `.inputs.candidate.json` under the artifact name without publishing a release ISO. Review package additions, removals, versions and hashes, then replace [the APT lock](../inputs/locks/apt.json) with the accepted candidate. The software lock remains enforced throughout resolution.

Software asset changes need a separately prepared and reviewed payload and [software lock](../inputs/locks/software.json). Export the verified cache and run an ordinary locked build afterwards:

```sh
mise run export-inputs .cache/miubian artifacts/miubian/inputs
mise run build
```

Export verifies the existing locks and updates the bundle path, size and hash in `software.json`. It does not resolve new selections or replace the locks. Keep the export destination inside the project so its path can be recorded. The `--legacy-cache` option is only for importing the preserved first-release cache.

## Checking the image

Check the changed behaviour in a fresh live session and installed system. The QA helper creates a disposable VM with no network device, four CPUs, 6 GiB RAM and an 80 GiB disk. Installation and visual checks are carried out in the guest. Use automatic partitioning for the standard Btrfs QA installation, and check the fresh account before personalising its defaults. The current live ISO requires Secure Boot disabled.

```sh
mise run qa start --firmware uefi
mise run qa screenshot
```

Before running a guest check, open a terminal inside the VM and run these two commands to attach a root shell to its serial device:

```sh
sudo /bin/bash --noprofile --norc
exec /bin/bash --noprofile --norc </dev/ttyS0 >/dev/ttyS0 2>&1
```

Then run the live check from the host:

```sh
mise run qa check live --username miubomz
```

Complete the graphical installation and shut down the live session with the ISO still attached. Stop the VM and boot its existing disk without installation media:

```sh
mise run qa stop
mise run qa start --firmware uefi --installed
mise run qa screenshot
```

After login, reopen the serial shell inside the guest, then run `mise run qa check installed --username miuqa`, replacing `miuqa` with the account created during installation. `--installed` requires the existing `system.qcow2`. Supply `--inputs-dir` again on restart if the test uses an input share.

Repeat the checks for BIOS in a separate work directory. Put `--work-dir` before the subcommand on every BIOS command, and use `--firmware bios` on both live and installed starts:

```sh
mise run qa -- --work-dir .build/miubian/qa-bios start --firmware bios
mise run qa -- --work-dir .build/miubian/qa-bios check live --username miubomz
mise run qa -- --work-dir .build/miubian/qa-bios stop
```

Use `mise run qa -- --help` for screenshots, keyboard and pointer input, guest commands and other controls. Before releasing an image, check real APT snapshots, GRUB snapshot previews and a permanent Timeshift restore followed by a cold boot. Confirm that home changes persist through system rollback.

When inspecting Homebrew's supplied formulae from the guest user's terminal, disable its metadata refresh so the check works offline:

```sh
HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_FROM_API=1 brew list --versions
```

Save reports and screenshots with the exact image they checked. Existing 0.2.0 evidence is under `artifacts/miubian/miubomz-0.2.0-amd64.qa.json` and `artifacts/miubian/qa/miubomz-0.2.0-amd64/`. It covers that artifact; later source changes need their own image verification. Installed-system Secure Boot, encrypted installation, hibernation, physical monitor DDC, and restores from live media or across kernel changes require separate validation.

## Cleaning up

Stop the disposable VM with `mise run qa stop`, using its work directory for BIOS. Stopping preserves the VM disk and logs; remove its disposable directory separately after saving the evidence.

```sh
mise run clean
```

Cleaning removes generated integration and image assembly state. It preserves the input cache, release artifacts, build logs and QA directories.
