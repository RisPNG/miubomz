# Building Miubian

Miubian is Miubomz's Debian Testing GNOME variant. The installed operating system remains Debian, and users can change the supplied defaults after installation. Version 0.2.0 uses Debian Forky, native Debian live-build and Calamares.

The source expresses the desired experience, the Miubian implementation and its exact release inputs separately. The reference workstation records how the experience was established. Building does not require mounting that workstation or its VM.

## Use the image

Open `artifacts/miubian/miubomz-0.2.0-amd64.iso` in GNOME Boxes or another virtual machine. Allocate at least 6 GiB RAM and a 64 GiB installation disk; an 80 GiB disk leaves room for the supplied software and snapshots. The tested configuration uses four CPUs and 2D Virtio graphics. Start the live desktop and open **Install Miubomz**.

Choose language, location, keyboard and account normally. Automatic partitioning supplies a GPT disk with an 8 MiB BIOS boot partition, a 1 GiB EFI partition and Btrfs for the remaining space. It creates no disk swap; zram supplies compressed RAM swap. Manual partitioning remains available. After installation, shut down the live session, detach the ISO and boot the installed system.

The first installed boot initializes native Timeshift scheduling and its initial snapshot. APT transactions create additional system snapshots before changing packages. Home stays outside system rollback. Use GRUB snapshot entries for previews; perform permanent Timeshift restores from the normal installed system or live media. GNOME, application and shell preferences initialize fresh accounts without repeatedly resetting later changes.

The supplied development tools are available offline. Requested Python-version provisioning uses Mise's ordinary upstream refresh; use its native offline mode for a supplied version, for example `MISE_OFFLINE=1 venv create project 3.11 --yes`.

Homebrew normally refreshes its API metadata during inspection. To list the supplied formula versions offline, use its native flags:

```sh
HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_FROM_API=1 brew list --versions
```

## Source layout

| Path | Maintained responsibility |
| --- | --- |
| `policy/` | Desired desktop, application, development and system behavior, with rationale |
| `variants/miubian/release.json` | Variant, version, architecture, Debian suite and artifact names |
| `variants/miubian/live-build/` | Native `auto/` entry points, semantic package lists, archive configuration, preseeding and image hooks |
| `variants/miubian/integration/` | Canonical defaults, runtime helpers, installer jobs, live adapter, recovery integration and their native Debian source package |
| `variants/miubian/packages/calamares/` | Pinned upstream Calamares source checksums, one quilt patch and native build recipe |
| `variants/miubian/inputs/` | Non-APT software selection and reviewed APT/software resolution locks |
| `variants/miubian/reference/` | Historical setup and clean desired-results inventories used for provenance and parity |
| `variants/miubian/build/` | Debian builder environment, input preparation, native build, inventory and artifact export |
| `variants/miubian/tests/` | Integration, assembled-image and disposable-VM verification |
| `.build/miubian/` | Generated native build and VM state, including logs |
| `.cache/miubian/` | Verified input bytes and downloaded upstream Calamares sources |
| `artifacts/miubian/` | Exported input bundle, ISO, manifests, native packages and source packages |

`integration/` is one self-contained Debian source package. Debhelper maps its domain sources to installed paths through ordinary `debian/*.install` files. It produces four packages with distinct ownership:

- `miubomz-defaults`: persistent desktop, application, account, shell and system defaults.
- `miubomz-recovery`: Timeshift, APT snapshots, GRUB snapshot menus and recovery services.
- `miubomz-installer`: Calamares settings, jobs and launcher; removed during installation.
- `miubomz-live-settings`: live-config adapter calling the same account initializer; removed during installation.

Calamares itself is the fifth source-built binary package. Build output is generated outside the canonical source package. There are no maintained parallel `root/etc` and `root/usr` payload trees.

## Inputs and locks

Native live-build package lists express Debian package selection without versions. The APT lock records the resolved live-system and offline-installer package closure, exact versions, archive sizes and SHA-256 hashes. `inputs/software.json` selects upstream assets, Flatpak references, extensions and toolchains; its software lock records exact payload identity and resolved versions or commits. Selection changes require a reviewed replacement lock. Image assembly fails if recipes, cached bytes, installed versions or the offline repository differ from those locks.

The first release's selected upstream bytes and native package archives are distributed as a verified immutable `.tar.zst` input bundle. Its content-addressed filename, size and SHA-256 are declared in `inputs/software.json`. This bundle is a required release input for an empty cache. Obtain the declared bundle alongside the source and place it at the recorded project-relative path, or supply its path explicitly:

```sh
MIUBOMZ_INPUT_BUNDLE=/path/to/miubian-inputs-<sha256>.tar.zst mise run build
```

No remote location is assumed for this locally exported bundle. An empty cache is reconstructed from it and checked against the tracked locks. Later builds recheck and reuse `.cache/miubian/software/` and `.cache/miubian/apt/`. Historical `reference/desired-results/` files are not build selection inputs. The software payload retains unmodified upstream assets; maintained product configuration comes from `integration/` and is excluded from the asset overlay.

Preparation also seeds `.cache/miubian/bootstrap/` with independent copies of the verified package archives. Native debootstrap uses this mutable cache, checking each reused archive against the current official Debian index and downloading missing bootstrap versions there. It can replace its cached files without changing the reviewed archives under `apt/`. This cache speeds bootstrap and does not select or pin release packages; it is not included in the declared input bundle.

Export a new bundle from a verified canonical cache with:

```sh
mise run export-inputs .cache/miubian artifacts/miubian/inputs
```

The one-time first-release migration can import its preserved asset cache explicitly:

```sh
mise run export-inputs --legacy-cache /path/to/first-release/.cache/miubomz artifacts/miubian/inputs
```

Export verifies the selected bytes and updates the recipe's bundle descriptor. It does not capture a running workstation or replace reviewed locks. The host export command requires Python 3, Flatpak, Git, GNU tar and zstd. The export task uses noninteractive sudo to read native builder-owned metadata without changing cache permissions, and returns the bundle and checksum ownership to the source owner.

To change Debian selection, edit the native package lists or archive definitions and resolve through the same native build flow:

```sh
MIUBOMZ_RESOLVE_INPUTS=1 mise run build
```

Resolution keeps the software lock enforced, stages the explicitly selected exported DEB inputs and source-built packages, and lets native APT resolve the remaining unversioned lists. It exports `miubomz-0.2.0-amd64.apt-lock.candidate.json` and `.inputs.candidate.json`, without publishing a release ISO. Review the package/version changes and copy the accepted candidate to `variants/miubian/inputs/locks/apt.json`. Export its verified cache as a new input bundle, then run a normal locked build and release verification. Resolution never rewrites tracked locks automatically. Non-APT software changes likewise need a reviewed replacement payload and software lock before export.

## Build

The host needs mise, Docker, access to its daemon and sufficient free disk space for the unpacked software, native working system, cache and ISO. The first image contains large offline toolchains and applications; allow at least 100 GiB free for building and testing it. Host tools are run through mise. Debian build tools run inside the disposable builder.

```sh
mise run build
```

The privileged Debian container gives native live-build access to the mounts it requires. The source bind mount is read-only; generated work, cache and artifact mounts are explicit and variant-specific. The build first verifies and stages declared inputs, builds the native integration and patched Calamares packages, then invokes `lb config` and `lb build`. Image validation gates export.

The Debian bootstrap and builder dependencies use the official archive over the network. Native live-build uses the builder's bootloader, image and splash tools outside the frozen runtime, keeping temporary build dependencies independent of the shipped package closure. The shipped live-system and installer archives remain locked. This is a pinned release-input workflow, not a claim that the container toolchain or ISO timestamps produce byte-identical rebuilds.

Successful export produces:

- `artifacts/miubian/miubomz-0.2.0-amd64.iso` and `.iso.sha256`.
- `artifacts/miubian/miubomz-0.2.0-amd64.packages`, `.build.json` and `.inputs.json`.
- `artifacts/miubian/packages/miubomz-0.2.0-amd64/`: all source-built binary packages and checksums.
- `artifacts/miubian/sources/miubomz-0.2.0-amd64/`: native integration and patched Calamares source packages, build records and checksums.

The input manifest records the source fingerprints and exact consumed native package archives. The image report records the complete filesystem hash, package closure, software lock, installer and boot checks. Build logs live under `.build/miubian/logs/`.

The default builder uses four CPUs, a 4 GiB memory limit and a 1 GiB Squashfs cache. `MIUBOMZ_BUILD_JOBS`, `MIUBOMZ_BUILD_MEMORY` and `MIUBOMZ_SQUASHFS_MEMORY` control these limits. `MIUBOMZ_DEBIAN_MIRROR` selects the build-time Debian archive; installed systems use Debian's Forky archive. `MIUBOMZ_BUILDER_IMAGE` can select an explicitly prepared compatible builder image.

```sh
mise run clean
```

Cleaning invokes native `lb clean --purge` and removes generated integration and image assembly state. It preserves the verified cache, input bundle, release artifacts, logs and disposable QA directories. Stop and remove a disposable QA VM separately after its evidence is saved.

## Installation and recovery implementation

Calamares uses its native Btrfs subvolume creation and the documented Debian installation sequence. Miubian owns the selected layout and mount defaults; Timeshift and grub-btrfs own snapshot creation and menu maintenance. Native binary package lists resolve the installer goals. Locked builds stage the reviewed GRUB archives and repository through native `includes.binary`, supplying both firmware modes offline without resolving removed versions from a moving mirror. Temporary build pins, installation-media sources and live-only packages are removed from the target.

Debian Calamares 3.4.2-1.1 receives one patch: its legacy BIOS root boot flag applies only to non-GPT tables. KPMcore otherwise changes the GPT Linux root partition type to EFI. Upstream source checksums and the quilt patch are maintained under `packages/calamares/`; its native source output is exported with the image.

Live boot uses native `plymouth.enable=0` because the original cold BIOS tests reproduced a GDM/Plymouth handoff timeout and a second login screen. Installed systems retain Debian's normal boot configuration. Squashfs uses native `-no-duplicates` to avoid the duplicate-checking race observed with the original compressor; file contents and hard links retain their behavior. The live session uses Debian's RAM-backed overlay with a 90% ceiling for the supplied account toolchains.

The live ISO requires Secure Boot disabled. Its EFI image and modules are generated together by the builder's native GRUB tools. Installed targets retain the locked Debian signed GRUB and shim packages; Secure Boot on installed systems has not been validated.

## Verification

```sh
mise run test
mise run qa start --firmware uefi
mise run qa screenshot
mise run qa check live --username miubomz
mise run qa stop
```

The QA helper operates a disposable QEMU VM with no network device. `check` runs the shared live or installed smoke checks through a guest serial shell. In the guest terminal, first open a root shell, then run the second command there to attach it to the serial device:

```sh
sudo /bin/bash --noprofile --norc
exec /bin/bash --noprofile --norc </dev/ttyS0 >/dev/ttyS0 2>&1
```

Use `mise run qa --help` for keyboard, pointer, screenshot, serial guest, installation-media eject and lifecycle commands. BIOS checks use a separate directory, selected consistently with `--work-dir .build/miubian/qa-bios`. Save reports and screenshots before removing disposable VM state.

After installation, shut down the live session while its ISO is still attached. Stop the QA process and start its existing disposable disk without installation media for a cold boot:

```sh
mise run qa stop
mise run qa start --firmware uefi --installed
mise run qa screenshot
mise run qa check installed --username miuqa
```

`start --installed` requires the existing `system.qcow2`, omits the CD drive and boots from disk. It preserves the selected firmware, work directory and optional read-only input share. Open the serial bridge again after login before running installed checks. The ISO path remains in `launch.json` as release provenance.

Integration tests exercise installer sources, account lifecycle, partition-dependent recovery, APT snapshot guards and native image inventory. Input preparation verifies selected bytes, modes and native software inventories before staging. The assembled-image validator checks the complete filesystem extents, locked package closure, required package-owned integration files, retired package identities, ChatGPT, firmware boot entries and offline media. Fresh VM checks verify the deployed software and installed behavior separately.

Version 0.2.0 passed 38 integration tests, fresh offline UEFI and BIOS Calamares installations, installed disk cold boots, exact software inventories, native package ownership, the five-subvolume Btrfs layout and zram-only swap. UEFI recovery checks exercised real APT pre-transaction snapshots, GRUB previews with temporary root writes and permanent Timeshift restore followed by a cold boot; home changes persisted.

The native build completed the filesystem before final EFI assembly was resumed using builder-owned boot tools. Its complete filesystem hash stayed unchanged, and normal export validated the final image, locked inputs and native source packages. `artifacts/miubian/miubomz-0.2.0-amd64.qa.json` records the exact ISO and filesystem, verification scope, observations and evidence under `artifacts/miubian/qa/miubomz-0.2.0-amd64/`.

Permanent restore was tested from the normal installed system with the same kernel and bootloader. Restore from live media or across kernel changes, Secure Boot, encrypted installation, hibernation and physical display DDC require separate testing. Earlier 0.1.0 evidence remains with the preserved first release.
