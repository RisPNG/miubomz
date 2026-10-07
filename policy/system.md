# Installation and system behavior

Miubian remains Debian Testing, currently Forky. The live desktop and installed system share the persistent desktop, application and account defaults. Live conveniences and installer components have their own lifecycle and are removed from the installed system.

Calamares retains user choice for language, location, keyboard, account and storage layout. Automatic partitioning supplies a hybrid GPT layout: an 8 MiB BIOS boot partition, a 1 GiB EFI system partition and Btrfs in the remaining space. Btrfs uses `@`, `@home`, `@var_log`, `@var_cache` and `@var_tmp`, with Zstd compression. `/boot` remains in the root subvolume. Manual partitioning remains available.

Automatic installation creates no disk swap and does not present a swap selector. Zram provides compressed RAM swap through its native generator. Hibernation and encrypted rollback are not established parts of the tested configuration.

Timeshift snapshots cover the system while home stays outside rollback. Native scheduling creates the initial and due snapshots; APT creates a snapshot before changing packages. A failed snapshot prevents that transaction. GRUB exposes snapshot previews with temporary root writes, and Timeshift provides permanent restore. Recovery integration skips live sessions and incompatible filesystems. Same-disk snapshots are system checkpoints; personal data still needs an external backup.

The native `sudo` group receives passwordless administration, and I2C support is enabled for the selected hardware tools. Users can edit these defaults after installation. Installed Debian and vendor repositories remain usable; temporary build pins and installation-media sources are removed.

Miubian implements this policy through `variants/miubian/live-build/` and the native source package in `integration/`. Its defaults, recovery, installer and live-settings binary packages have distinct ownership and lifecycles. Calamares itself has a separate patched upstream Debian recipe under `packages/calamares/`.
