# Miubian

Miubian is the Debian Testing GNOME variant of Miubomz. The [setup manual](dev/setup-manual-steps.md) records what it changes on top of Debian's live GNOME defaults. Keep that document up to date when adding, changing or removing part of the setup.

The folders below contain the maintained sources. Build commands are in [dev/README.md](dev/README.md), and the test coverage is described in [tests/README.md](tests/README.md).

## live-build/

Maintain Debian package selections in `config/package-lists/`, grouped by their purpose. The archive settings, firmware preseed and image hooks belong under `config/`; `auto/` contains the native live-build entry points.

Package lists describe what to include, while `inputs/locks/apt.json` records the resolved versions and archive hashes. When selections change, resolve and review a replacement lock before building a release. Keep live-session changes separate from settings intended for the installed system.

## inputs/

`software.json` selects software assets, Flatpaks, GNOME extensions and supplied development toolchains. It also identifies the input bundle needed for an empty cache. `locks/software.json` records the verified payload, file permissions and resolved versions, or commits. `locks/apt.json` records Debian and supplied package archives, including packages needed by the offline installer.

Keep selections, locks and the supplied bundle consistent. Changing software requires a reviewed replacement payload and lock; changing Debian package selection uses the APT resolution workflow. Cached inventories are generated records, so they should not replace these maintained inputs.

Configuration maintained in `integration/` must stay out of the asset overlay. In particular, keep the Mise and Rustup defaults and root's Midnight Commander settings in the integration package.

## integration/

This is the `miubomz-settings` Debian source package. It builds the defaults, recovery, installer and live-session packages.

| Folder | What to maintain or watch |
| --- | --- |
| `defaults/` | GNOME, application, shell and system defaults. Keep browser seeds free of personal data and use portable paths and monitor settings. GNOME defaults remain editable by the user. |
| `helpers/` | Account initialisation, shortcuts, Nautilus actions and shell history. Fresh accounts receive their setup once; existing profiles and later user changes must be preserved. |
| `installer/` | Calamares settings, branding, launcher and target jobs. Keep the Btrfs layout, zram-only automatic partitioning, offline installation and removal of live-only settings consistent. |
| `live/` | Live-config account setup. Use the shared account initialiser so the live desktop and installed accounts receive the same defaults. |
| `recovery/` | Timeshift, APT snapshots, GRUB entries and recovery services. Use the installed filesystem's identity, keep home outside system rollback and check both snapshot previews and permanent restores. |
| `vendor/` | Supplied upstream grub-btrfs files and Debian Calamares licensing. Retain licences and keep upstream files unchanged; product configuration belongs in the folders above. |
| `debian/` | Package ownership, installed paths, dependencies, permissions and service lifecycle. Keep manifests in step with source moves and use Ris Peng `<hello@rispeng.com>` for maintainer details. |

Generated Debian package files belong in the build directory. Keep account setup independent of a particular username, home directory, or display. Initialise assets without repeatedly replacing the user's preferences.

## packages/

`calamares/` contains the Debian source checksums, native build recipe and GPT boot-flag patch. The patch prevents a BIOS installation on GPT from marking the Linux root as an EFI partition.

When updating Calamares, verify the new official source checksums and whether the patch is still needed. Keep its package version, patch metadata and exported source package consistent. Calamares configuration belongs in `integration/installer/`.

## build/

Maintain the Debian builder, input verification, native package and image build, and release export here. Keep generated state under `.build/miubian/`, cached inputs under `.cache/miubian/` and released output under `artifacts/miubian/` at the project root.

Changes must keep lock verification, offline installer packages and source-package exports working together. The builder and bootstrap use Debian's network archive, so locked release inputs do not imply byte-identical ISO rebuilds.

`prepare-release.py` packages the verified exports for GitHub and requires a `miubian-<version>` tag matching `release.json`. Keep its ISO parts below GitHub's per-file limit and retain the complete-image checksum, source archives and commit record.

## release.json

Keep the variant, version, architecture, Debian suite and output names here. The version must agree with `integration/debian/changelog`. Update the setup manual and release verification when those details change.
