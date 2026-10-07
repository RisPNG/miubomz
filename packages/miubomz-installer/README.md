# Installer and recovery packages

`build.sh OUTPUT_DIRECTORY` builds `miubomz-installer_0.1.0_all.deb` and
`miubomz-recovery_0.1.0_all.deb` with `dpkg-deb`, without installing them.
The installer replaces `calamares-settings-debian`; the installed system keeps
the recovery package. The image must provide `/usr/lib/miubomz/initialize-user`
with an account-name argument for the desktop's portable per-user assets.

Calamares retains Debian's locale, keyboard, account, manual partitioning,
live-media, machine-id, display-manager, bootloader and initramfs flow. Automatic
partitioning uses Calamares' native hybrid GPT layout with a BIOS boot partition,
a 1 GiB EFI partition, and Btrfs with
`@`, `@home`, `@var_log`, `@var_cache` and `@var_tmp`. `/boot` remains inside `@`.
Automatic partitioning creates no disk swap and hides the swap selector. Mounts
use plain `compress=zstd`; zram uses the generator's native memory-based default.
Manual layouts remain available, but Timeshift recovery requires a compatible
Btrfs root. Encryption controls remain Debian's defaults; encrypted rollback
and hibernation are not yet validated.
The full first-image payload requires at least 64 GiB disk and 6 GiB RAM in
the live desktop and installer. Debian's live RAM overlay uses a 90% size
ceiling to accommodate the supplied user toolchains.

The target job discovers the installed filesystem UUID and chosen account;
it never copies the reference UUID or username. Its machine-independent
`/usr/lib/miubomz/timeshift-default.json` template creates the installed
Timeshift configuration without replacing Timeshift's own package files.
It sets Timeshift Btrfs mode,
excludes home from backup and restoration, retains 7 weekly, 8 daily and 2 boot
snapshots, and enables native scheduling. Timeshift's native schedule check
creates due snapshots and maintains its own cron jobs on installed boot.
The APT protocol-2 pre-install hook runs before the
transaction's dpkg operations, including removals. Its snapshots carry package
context and a daily tag, sharing the eight-daily-snapshot retention policy.
Snapshot failure stops that package transaction. The hook consumes its input
but skips live sessions and incompatible filesystems.

`grub-btrfsd --timeshift-auto` maintains the snapshot menu. GRUB stays visible
for five seconds. Snapshot previews use Debian `overlayroot` with
`overlayroot=tmpfs:recurse=0`; root writes disappear on reboot, while home, EFI,
logs, caches and other separately mounted data remain writable and persistent.
The preview boot parameters mask Debian's root-remount and GRUB boot-record
services; the snapshot-menu daemon also skips this temporary overlay boot.
Normal installed boots retain all three services.
Restore permanently using Timeshift from the normal system or live media,
keeping home excluded. Snapshot previews and permanent restore are separate
operations and both require VM validation, including a kernel update. These
same-disk snapshots do not supply an external user-data backup.

Installed APT sources track Forky `main non-free-firmware`. Only Debian source
entries are replaced; vendor repositories and their preferences remain. The
image's temporary reference-version pins and frozen-media source are removed,
including their saved originals, so installed systems receive ordinary Forky
upgrade candidates. The native live-build binary
package lists include the full BIOS/UEFI GRUB dependency closures. The target
installs the matching platform's GRUB metapackage from that offline media
repository, preserving Debian's bootloader update behavior without consulting
network repositories. Encryption prerequisites are image inputs.
The image's live-only packages are removed before initramfs regeneration;
Calamares' native APT backend also removes their unused dependencies. The approved
passwordless administrator policy uses the native `sudo` group and grants
Polkit actions to active local members, without a reference-account name.

## Upstream inputs

Debian assets and untouched module settings come from
[`calamares-settings-debian` 14.0.2](https://salsa.debian.org/live-team/calamares-settings-debian/-/tree/14.0.2).
The native Calamares source package in `packages/calamares` corrects its legacy
root boot flag on GPT while preserving the upstream automatic partition flow.
The sequence preserves the Debian live-install ordering; the Python jobs replace
its hardcoded Trixie sources and mount-table-based target discovery.
[`Calamares` native mount configuration](https://github.com/calamares/calamares/blob/calamares/src/modules/mount/mount.conf)
owns subvolume creation and publishes its mount options to `fstab`.
The vendored [`grub-btrfs` v4.14](https://github.com/Antynea/grub-btrfs/tree/v4.14)
is pinned to commit `2fcfbe967637166b88dadd49c834807243a941bf`; its scripts are
unchanged, and the configuration adds the reviewed Debian/Timeshift settings.
Their licenses ship in each package's documentation directory.
