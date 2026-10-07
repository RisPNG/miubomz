# Miubian integration

This directory is the native `miubomz-settings` Debian source package. Its maintained sources live by responsibility; `debian/` maps those sources directly to their installed paths.

| Source | Responsibility | Binary package |
| --- | --- | --- |
| `defaults/` and `helpers/` | Desktop and application preferences, shell, account initialization, administrator policy, I2C and zram | `miubomz-defaults` |
| `installer/calamares/` | Native Debian Calamares configuration, jobs and launcher | `miubomz-installer` |
| `live/` | Live-config adapter using the same account initializer | `miubomz-live-settings` |
| `recovery/` and `vendor/grub-btrfs/` | Timeshift, APT snapshots, GRUB snapshot menus and recovery services | `miubomz-recovery` |

The image builder copies this source package into its generated working directory and invokes `dpkg-buildpackage -us -uc`. Debhelper installs the canonical sources, records native conffiles, generates service lifecycle scripts and builds all four binary packages. Generated package state belongs outside this source directory.

GNOME defaults have no locks; user preferences override them. Application and shell seeds initialize new accounts without replacing later changes. `/usr/lib/miubomz/initialize-user` initializes portable account assets once and is shared by the live-config component, installer target job and desktop autostart. Existing user homes are not rewritten by package installation. Debian Bash retains ownership of `/etc/skel/.bashrc`; account initialization copies the shell seed from `/usr/share/miubomz/skel/.bashrc` only when the home file is missing or still matches Debian's skeleton. Customized homes remain unchanged.

Desktop preferences preserve the clean Desired Results reference. Monitor-specific Dash to Panel placement uses its supported numeric monitor fallback rather than a reference display serial. Firefox's Biscuit theme and selected preferences use a clean profile registry with the installation-directory hash for Debian's `/usr/lib/firefox-esr`; the install section prevents Firefox from creating a separate profile instead of using its seed. Vivaldi receives completed welcome-page preferences, an empty bookmark tree and no reference browsing data. Its launcher selects X11 and the supplied persistent horizontal menu stylesheet.

The shell expects ble.sh at `/usr/share/blesh`, Homebrew at `/home/linuxbrew/.linuxbrew` and the supplied mise, easyvenv, Starship and fetch tools. Software inputs provide the pinned toolchains, Fluent theme variants, per-user GNOME extensions, mpv/uosc, Flatpaks and qView's AppImage. The cursor name is `fluent-dark`; the icon theme is `Fluent-dark`. Account initialization creates GTK 4 links to the shared Fluent theme once.

qView lives in the user's `AppImages` directory with Gear Lever's native desktop entry, icon and clean registration. Initialization substitutes the selected home directory in its desktop entry and Gear Lever configuration before first use. Gear Lever retains foreground updates, application detection and removal; background updates remain disabled. The existing `initialized-0.1.0` state filename identifies this unchanged initialization schema rather than the image release.

System defaults own passwordless administration for the native `sudo` group, I2C module loading and zram's native memory-based default. These settings remain editable after installation.

Calamares retains Debian's locale, keyboard, account, manual partitioning, live-media, machine-id, display-manager, bootloader and initramfs flow. Automatic partitioning uses its native hybrid GPT layout with an 8 MiB BIOS boot partition, a 1 GiB EFI partition and Btrfs with `@`, `@home`, `@var_log`, `@var_cache` and `@var_tmp`. `/boot` stays inside `@`; automatic partitioning creates no disk swap. Mounts use `compress=zstd`. The supplied software requires at least 64 GiB disk and 6 GiB RAM. The installer removes both Miubomz live packages and Debian's live-only packages before regenerating initramfs.

Recovery uses the selected installed filesystem UUID rather than reference-machine identity. Timeshift excludes home from system rollback and retains seven weekly, eight daily and two boot snapshots. Native scheduling creates due snapshots, while the protocol-2 APT hook creates a daily-tagged snapshot before package changes, including removals. Snapshot failure stops the transaction. Live sessions and incompatible filesystems are skipped.

`grub-btrfsd --timeshift-auto` maintains snapshot menus. Snapshot previews use Debian `overlayroot=tmpfs:recurse=0`: root writes disappear on reboot while separately mounted home, EFI, logs and caches remain persistent. Restore permanently through Timeshift from the normal system or live media. Same-disk snapshots do not provide an external user-data backup. Encrypted rollback and hibernation remain unvalidated.

The installer preserves vendor repositories and removes temporary build pins and media sources. Installed Debian sources track Forky `main non-free-firmware`. Offline BIOS and UEFI bootloader packages come from native live-build binary package lists. Debian Calamares configuration and assets originate from `calamares-settings-debian` 14.0.2; its license is retained under `vendor/`. The separately packaged Calamares source patch corrects its legacy root boot flag on GPT.

Vendored grub-btrfs v4.14 is pinned to commit `2fcfbe967637166b88dadd49c834807243a941bf`. Its scripts, manual pages and license remain unchanged; `recovery/` owns the Debian and Timeshift configuration. Package-level tests and VM checks live in the sibling `tests/` directory.
