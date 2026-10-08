# How Miubian is set up

Miubian uses Debian Testing, currently Forky, with GNOME. The installed system keeps Debian's identity and normal update path. This is the setup I settled on for the desktop, applications and installed system, and the specification I use when changing Miubian. The settings below describe Miubian 0.2.0, with the defaults kept in the project so a new installation can start from the same setup.

I leave language, location, keyboard and account details up to the user. The desktop and application settings are defaults too, so they can be changed after installation. New accounts receive their application and shell configuration once, and later package updates preserve changes made by the user.

The live desktop and installed system use the same desktop and application defaults. Account setup uses the installed user's home directory and ownership, with clean profiles and no personal history or credentials.

The build commands are in [BUILD.md](../../../BUILD.md). The [package lists](../live-build/config/package-lists/), [software selection](../inputs/software.json) and [integration sources](../integration/) contain the actual setup described here.

The accompanying [desired-packages.json](specifications/desired-packages.json) and [software-lock.json](specifications/software-lock.json) record the original Desired Results workstation. They preserve the package and software inventories that informed this setup. Current build selections and exact release locks are maintained under [inputs/](../inputs/).

## Installation

Boot the Miubian ISO, start the live desktop, then open **Install Miubomz**. The supplied software needs at least 6 GiB of RAM and 64 GiB of disk space. Secure Boot needs to be disabled for the current live image.

Follow the Calamares prompts for language, location, keyboard and user account. My original choices were American English, Asia/Kuala Lumpur with the `en_GB.UTF-8` locale, and the English (US) keyboard. Those are still the user's choices to make.

For automatic partitioning, Miubian uses a GPT partition table with:

- An 8 MiB BIOS boot partition.
- A 1 GiB FAT32 EFI system partition mounted at `/boot/efi`.
- A Btrfs partition using the remaining space.

The Btrfs partition has these subvolumes:

| Subvolume | Mount point |
| --- | --- |
| `@` | `/` |
| `@home` | `/home` |
| `@var_log` | `/var/log` |
| `@var_cache` | `/var/cache` |
| `@var_tmp` | `/var/tmp` |

The mounts use Zstd compression, and `/boot` stays inside `@`. I keep home, logs, caches and temporary data separate from the system subvolume so they can remain outside a system rollback.

Automatic partitioning creates no disk swap and doesn't present a swap selector. Miubian already uses zram through `systemd-zram-generator`, with its normal memory-based sizing. Manual partitioning is still available for users who want their own layout.

Once installation is complete, shut down the live session, remove the installation media, then boot the installed system. The installer removes its live-only packages, temporary build pins and installation-media sources before finishing.

The layout is kept in the [Calamares partition settings](../integration/installer/calamares/modules/partition.conf), with target configuration in [the installer implementation](../integration/installer/calamares/miubomz_installer.py).

## System setup

The installed system uses Debian's Forky repositories with `main non-free-firmware`. Vivaldi and Visual Studio Code keep their vendor repositories, so updates can continue through APT. Flatpak uses Flathub, and GNOME Software has its Flatpak plugin installed.

Time synchronisation uses `systemd-timesyncd`. Git, the development dependencies, file-management utilities and hardware tools are included through the package lists.

### Administrator access

I set up passwordless administration for members of the `sudo` group. The sudo rule is:

```sudoers
%sudo ALL=(ALL:ALL) NOPASSWD: ALL
```

Polkit also approves actions for members of that group when they are in an active local session. This covers terminal `sudo` commands and desktop administrator prompts. Programs running under an account with these permissions can obtain administrator access without another password prompt.

The rules are kept in [the administrator defaults](../integration/defaults/system/administrator/) and installed as `/etc/sudoers.d/99-miubomz-admin` and `/etc/polkit-1/rules.d/00-miubomz-admin.rules`.

### Monitor controls

Miubian loads `i2c-dev` automatically and adds the installed account to the `i2c` group. It includes `ddcutil`, the DDC control tools and I2C utilities for monitor controls. The brightness shortcuts described below use this setup when accessible DDC/CI monitors are present.

## Browsers

### Firefox

I keep Firefox with the [Biscuit theme](https://addons.mozilla.org/en-US/firefox/addon/biscuit-mojas84/) and a clean profile. From the default setup, I make these changes:

- Use vertical tabs and hide the bookmarks toolbar.
- Turn off spell checking and leave the AI chatbot out of the sidebar tools.
- Enable DRM-controlled content and always show scrollbars.
- Turn off extension and feature recommendations.
- Turn off Firefox Home shortcuts, stories, search, weather and sponsored shortcuts.
- Turn off search suggestions and enable Global Privacy Control.
- Turn off password saving, autofill and password alerts.
- Turn off health and usage uploads, studies and automatic submission of unsubmitted crash reports.
- Disable DNS over HTTPS.

The profile contains the preferences and theme without personal browsing data. The exact preferences are kept in [Firefox's `prefs.js`](../integration/defaults/applications/firefox/miubomz.default-esr/prefs.js).

### Vivaldi

I keep Vivaldi as the default browser and put its tabs on the left. The tab bar auto-hides, while the native title bar and horizontal menu stay visible. The welcome screen is completed, and the profile starts with an empty bookmark tree and dashboard widgets removed.

For appearance and window behaviour, I use:

- The Dark theme with theme scheduling disabled.
- Native window decoration and simple scrollbars.
- A horizontal menu, with only the tab bar selected for auto-hide.
- The panel on the right, with its toggle visible and floating panels enabled.
- Auto-close for inactive panels disabled.
- Bookmarks, Downloads, History, Translate, Windows and Tabs, and Sessions in the initial panel toolbar.
- Exit confirmation and the multiple-tab and multiple-bookmark confirmation prompts disabled.
- Bookmarks opening in a new tab, and the QR code generator enabled.

For browsing, I use Google for ordinary, private-window and image searches, and keep suggestions enabled in the address and search fields. Browsing history uses the profile's 3,650-day retention setting. Downloads go to the default location without asking, and the selected-text translation button is enabled.

I turn off saved passwords, addresses and payment methods, including checking for saved payment methods. Do Not Track is enabled. The profile also disables phishing and malware protection, abusive-ad blocking and navigation-error assistance, and allows pop-ups, insecure content and intrusive ads.

To keep the title bar and menu visible while tabs auto-hide, the launcher uses these flags for ordinary windows, new windows and private windows:

```text
--ozone-platform=x11 --enable-features=VivaldiCssMods
```

The custom UI directory is `/usr/share/miubomz/vivaldi`. Its [persistent horizontal-menu stylesheet](../integration/defaults/applications/persistent-horizontal-menu.css) keeps the menu in place while the other auto-hide controls can hide. This applies outside fullscreen.

The [Vivaldi profile](../integration/defaults/applications/vivaldi/) and [launcher](../integration/defaults/applications/launchers/vivaldi-stable.desktop) keep these settings together.

## GNOME desktop

I use the following extensions:

- AppIndicator and KStatusNotifierItem Support.
- Color Picker.
- ArcMenu.
- Dash to Panel.
- Lock Keys.
- Desktop Icons NG (DING).
- Removable Drive Menu.
- Smile.
- Just Perfection.
- Tiling Assistant.
- Window on Top.
- Force Quit.
- Blur My Shell.

They are enabled by default. GNOME's stock Apps Menu extension is installed but disabled, since ArcMenu supplies the menu used here.

### ArcMenu

I leave the other settings at their defaults and make these changes:

- Display ArcMenu on all panels and hide the overview on startup.
- Enable the theme override, with border width `0`, border radius `20` and font size `12`.
- Set the left panel width to `375` and the right panel width to `200`.
- Show application descriptions, without grouping apps alphabetically in list views.
- Remove the pinned apps and use GNOME Console for the terminal shortcut.
- Show search-result descriptions and highlight the search terms.
- Use All Programs as the default view.
- Use the Debian symbolic icon at size `32`.

### Dash to Panel

I start with no pinned favourites and hide the Show Applications button. The panel uses a border-radius setting of `4`, no app-icon margin and the Ripple animation when hovering over app icons.

Running indicators sit on the right. Focused applications use Segmented indicators, and unfocused applications use Dashes. Dominant icon colours are used for the indicators and focus highlight, with highlight opacity `15`.

The panel background opacity is `90%`. I turn off notification-count badges, isolate applications by workspace and monitor, enable app hotkeys, and include App Details in the secondary menu. Clicking empty space closes the overview, and the overview stays hidden on startup.

Tray and left-box font sizes are `16`. Tray, status-icon and left-box padding are `2`. Panel menu buttons activate on click only.

Panel placement uses Dash to Panel's numeric monitor fallback, so the defaults work with the displays available on the installed machine.

### Desktop and window behaviour

I start at the desktop, turn off the hot corner and automatic screen blanking, and use flat mouse acceleration. Windows that demand attention receive focus. Tiling Assistant's keybindings are disabled.

Desktop Icons NG shows network volumes. File preferences include a permanent-delete option and always show image thumbnails. Hidden files are shown in the GTK file choosers.

The title bar has minimise and maximise buttons. Middle-clicking it minimises the window. Extended keyboard input sources are available.

### Theme, fonts and blur

I use dark mode with these theme settings:

| Setting | Value |
| --- | --- |
| GTK theme | `Fluent-round-Dark-compact` |
| Icons | `Fluent-dark` |
| Cursor | `fluent-dark` |
| Interface font | Noto Sans 11 |
| Document font | Noto Sans 12 |
| Monospace font | Noto Mono 11 |
| Font hinting | Full |

The supplied Fluent themes, icons and cursors come from the upstream [GTK theme](https://github.com/vinceliuice/Fluent-gtk-theme) and [icon theme](https://github.com/vinceliuice/Fluent-icon-theme). New accounts link their GTK 4 `gtk.css`, `gtk-dark.css` and `assets` to the matching dark theme under `/usr/share/themes/Fluent-round-Dark-compact/gtk-4.0/`, so the GTK 4 setup uses the same dark variant.

Blur My Shell has application blur enabled globally, with actor opacity `255` and dynamic opacity disabled. The theme supplies the transparency while the text stays solid. The final exclusion list is:

```text
Plank
com.desktop.ding
Conky
com.rastersoft.ding
```

Both DING identifiers are included because the current desktop window uses `com.rastersoft.ding`. Excluding it keeps the desktop surface out of application blur, so the wallpaper isn't blurred just because desktop icons are enabled.

These desktop choices are kept in [the GNOME defaults](../integration/defaults/gnome/dconf/00-desktop).

## Applications

I include the selected Debian applications alongside the vendor packages, Flatpaks and qView AppImage. Epiphany, mpv and CopyQ are Debian applications. CopyQ starts automatically. I leave ChatGPT out of Miubian.

Applications come from Debian's archive, their official vendor or project channels, and Flathub. I keep each supplied application manageable through its usual package manager after installation.

The Flathub applications are:

- Meld.
- Gear Lever.
- Warehouse.
- Black Box.
- GNOME Boxes.
- GNOME Snapshot.
- Smile.
- Extension Manager.
- LibreOffice.
- Passwords and Keys.
- Remmina.
- GNOME Sound Recorder.
- Parabolic.
- qBittorrent.
- Evince.
- nomacs.
- Qalculate!.
- pgAdmin 4.

Their runtimes are supplied too, so installation doesn't need to download them. The selected applications and their exact references are kept in [the software selection](../inputs/software.json).

### qView

I use qView's AppImage with Gear Lever, registered in the application menu. The AppImage lives in the user's `AppImages` directory, and the account setup adjusts its launcher and Gear Lever registration for the installed user's home directory.

The image includes `libfuse2t64`, since this AppImage needs FUSE 2 compatibility. Gear Lever retains application detection, removal and foreground updates, with background updates disabled.

### mpv and uosc

I use mpv with uosc, with this configuration:

```ini
keep-open=always
idle=yes
force-window=yes
gpu-sw=yes
osc=no
osd-bar=no
```

The window stays open after playback and can open without a file. Software rendering is allowed, which matters in a VM without a hardware GPU. uosc provides the controls instead of mpv's built-in controls and seek or volume bars.

The [mpv preferences](../integration/defaults/applications/mpv/mpv.conf), uosc scripts, fonts and script options are supplied together.

### Text Editor and fonts

GNOME Text Editor shows line numbers, highlights the current line, shows the overview map and right margin, and doesn't restore the previous session.

I include the selected [font packages](../live-build/config/package-lists/30-fonts.list.chroot) and Font Manager. Font Manager uses the Adwaita stylesheet and opens in Manage view.

Midnight Commander uses the `yadt256-defbg` skin for both the normal account and `sudo mc`.

## Terminal and development setup

I use GNOME Console as the default terminal for the desktop, `x-terminal-emulator` and Nautilus's Open in Terminal action. Console has unlimited scrollback. `mcedit` is the default terminal editor.

Black Box remembers its window size, hides the header bar, keeps the drag area and uses Noto Mono 12. Its working directory starts at home. The native Black Box package is used for Nautilus's command runner, and its Flatpak is also included.

### Bash

A new interactive terminal starts `fetch --infinite` before the prompt. Type one ordinary character or press Ctrl+C to dismiss it. A single typed character is preserved for the prompt, so wait for the prompt before pasting a command. Bash then uses Starship and ble.sh. Scripts and the Nautilus command runner skip fetch.

History has no entry or file-size limit. Leading spaces and failed commands are retained. When the exact same command is used again, its earlier entry is removed and the new occurrence stays at the end, including across terminals. The history helper preserves multiline entries and timestamps.

In the interactive shell, explicit `python3` and `pip3` commands use Debian's system Python, while unversioned `python` and `pip` follow Mise. Those shell functions don't change the interpreter used by scripts.

The shell configuration is kept in [the Bash seed](../integration/helpers/bashrc), with [the history helper](../integration/helpers/deduplicate-history.py) handling the saved history.

### Development tools

I include Git, Pacstall, fetch, Starship, ble.sh, Homebrew with GCC, Mise, easyvenv and Visual Studio Code. Rust also keeps its rustup environment. Bash activates the supplied Homebrew and Mise environments.

The Mise configuration selects Python `3.11`, with Go, Java, Node and Rust set to `latest` for later development work. The image itself contains the exact versions recorded in [the build's software lock](../inputs/locks/software.json), so installation and first login use the supplied toolchains.

For Python environments, easyvenv provides the `venv` command. Requesting another Python version can require Mise to refresh its upstream information. A supplied Python version can be used offline with Mise's offline mode, for example:

```bash
MISE_OFFLINE=1 venv create project 3.11 --yes
```

Git's clean configuration uses `credential.helper=store`. It doesn't include a personal name, email or saved credentials.

The [Mise defaults](../integration/defaults/applications/mise/config.toml) and [software selection](../inputs/software.json) keep the configuration and supplied tools explicit.

## Nautilus actions

I add these actions through Actions for Nautilus:

| Action | Behaviour |
| --- | --- |
| Copy details | Copy names, paths or URIs, including multiple selected items |
| Open in Terminal | Open Console in the selected folder or current folder |
| Execute command here | Run an entered command in Black Box in that folder |
| Open in Code | Open the folder in Visual Studio Code |

The three launch actions work with one local folder, including the folder background. Execute command here records the command in history, shows its exit status, then waits for one key before closing.

The [menu configuration](../integration/defaults/applications/actions-for-nautilus/config.json) calls [the Nautilus helper](../integration/helpers/nautilus-actions.py).

## Keyboard shortcuts

I disable the help-browser shortcut and use Super+B to open the default browser. The custom shortcuts are:

| Shortcut | Result |
| --- | --- |
| Super+E | Add a Home tab at the right end of Nautilus, or open a window if needed |
| Super+T | Open a new tab in the default terminal, or open a window if needed |
| Super+. | Open Smile |
| Super+- | Set detected DDC/CI monitors to their minimum brightness |
| Super+= | Set detected DDC/CI monitors to their maximum brightness |
| Ctrl+Shift+Esc | Open GNOME System Monitor |

The built-in Home-folder binding is disabled so Super+E uses the tab action. IBus keeps Super+; for its emoji picker, leaving Super+. for Smile. Super+= doesn't need Shift.

With GNOME Console, the terminal action uses its most recently active window and the current tab's directory. The helper resolves the current default terminal; a different terminal needs to provide a New Tab action for the same behaviour.

The brightness actions change brightness only, using each monitor's reported range. DDC/CI needs to be enabled and accessible on the monitor. Minimum brightness can still leave the display visible. Failures produce a desktop notification.

The bindings are in [the GNOME defaults](../integration/defaults/gnome/dconf/00-desktop), and the tab and brightness actions use [the shortcut helper](../integration/helpers/gnome-shortcut-helper).

## Snapshots and recovery

I use Timeshift in Btrfs mode and keep home outside system backup and restoration. The installer sets Timeshift to the installed root filesystem, so it uses the selected disk rather than a reference-machine device path.

The schedule retains:

- Seven weekly snapshots.
- Eight daily snapshots.
- Two boot snapshots.

Hourly and monthly snapshots are disabled. Timeshift's normal scheduling creates the initial and due snapshots after installation.

APT also creates a Timeshift snapshot before changing packages on the installed Btrfs system, including removals. If the snapshot fails, the package transaction stops. The hook skips the live session and incompatible filesystems.

GRUB shows a menu for five seconds, with snapshots under **Timeshift snapshots**. `grub-btrfsd --timeshift-auto` keeps those entries updated when Timeshift creates or removes snapshots.

Choosing a snapshot boots a preview with root writes held in RAM. Those root changes disappear on reboot. Separately mounted home, EFI, logs, caches and temporary data remain writable, and changes there persist.

For a permanent rollback, use Timeshift's Restore action from the normal installed system, with home restoration excluded. The preview and permanent restoration have different purposes, so I keep the restoration step outside the preview session.

These snapshots share the system disk. I still need an external backup for personal files and disk failure.

The [recovery configuration](../integration/recovery/) keeps Timeshift, the APT snapshot hook and the GRUB integration together.
