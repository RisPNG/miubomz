# Miubian tests

Tests are AI-generated and audited when a specific behaviour requires a closer review. Passing the tests does not guarantee that the setup is perfect, but it should be close to it.

## Integration

Run these tests from the project root with `mise run test`. They use temporary files and small example packages to check the build and setup behaviour.

| File | What it covers |
| --- | --- |
| [test_account_initialization.py](integration/test_account_initialization.py) | New accounts receive Miubian's shell defaults, theme links and Mise shims. MIME families and aliases receive the selected applications. Native GIO selects mpv while Harmonoid is absent, switches after manual installation and returns to mpv after removal without rewriting preferences. Custom shell settings, Gear Lever registrations and changes made after initialisation are preserved. Files created as root are assigned to the account. |
| [test_nautilus_tabs.py](integration/test_nautilus_tabs.py) | Native Nautilus folder launches, file reveals and selection, tab order, rapid requests and the disabled preference. Requires the compiled extension, Nautilus, `libgtk-4-bin` and `python3-nautilus` in a disposable environment; skips when that runtime is absent. |
| [test_image_inventory.py](integration/test_image_inventory.py) | Cached packages and software must match their recorded contents and permissions. Changes are rejected even when an earlier check passed. The package inventory includes installed packages and excludes leftover settings from removed packages. |
| [test_input_workflow.py](integration/test_input_workflow.py) | Exporting, unpacking and reusing build inputs preserves package contents, permissions and links. Only selected assets are included, maintained defaults are preserved, and bootstrap changes leave the original package cache intact. Changed recipes, extensions and tools require matching locks; package resolution uses the intended exported and locally built versions. |
| [test_installer_recovery.py](integration/test_installer_recovery.py) | Installation retains vendor repositories, removes temporary build settings and uses the target's account, package version and filesystem UUID. BIOS and UEFI bootloader packages come from offline media, with encrypted-root tools retained. Package changes create one recovery snapshot on installed Btrfs systems; live sessions, other filesystems and empty transactions are skipped. A snapshot failure stops the package transaction. |
| [test_source_export.py](integration/test_source_export.py) | Released packages must have complete, matching source archives and build records. Missing, duplicate, corrupted or mismatched records, and changed binary packages, are rejected. |
| [test_release_workflow.py](integration/test_release_workflow.py) | Release downloads reconstruct the original ISO, record the tagged commit and include source and package exports. Corrupt downloads, oversized parts and tags that differ from the release version are rejected, an existing ISO is preserved, and completed or failed builds remove their own container. |

## Image

This check runs when the build exports its release files. It checks the ISO's contents; booting and installing it are checked separately in a VM.

| File | What it covers |
| --- | --- |
| [validate-image.py](image/validate-image.py) | The ISO has BIOS and UEFI boot entries, disables Plymouth for normal live boots and contains the complete built filesystem. Installed and offline installer packages match their locks, required Miubian files have the intended package ownership, and the embedded software inventory matches its lock. Debian identity is retained, while build-only settings, retired packages, ChatGPT and the installed-system marker are excluded. |

## VM

Use `mise run qa -- --help` to see the VM commands. Installation and visual checks still need to be carried out in the guest.

| File | What it covers |
| --- | --- |
| [check-system.sh](vm/check-system.sh) | Automated checks inside a live or installed guest cover package versions, account defaults, themes, I²C group membership, active zram and required configuration files. Live checks confirm installer availability. Installed checks confirm removal of live-only components, Btrfs, the correct Timeshift device, enabled recovery services and a GRUB configuration. |
| [qa-install.py](vm/qa-install.py) | A driver for a disposable offline VM, with BIOS or UEFI boot, keyboard and mouse input, screenshots, guest commands and command logs. Its `check` command runs `check-system.sh` and returns the result. The driver does not complete the graphical installer or independently confirm the desktop's appearance. |
