# Reference workstation setup

These are the original setup records for the Desired Results VM. They document the reference result; the maintained Miubian recipe lives in `live-build/`, `integration/`, and `inputs/`. Commands below are historical steps, not build instructions.

## Initial Installation

First, I boot from the `debian-live-testing-amd64-gnome.iso`.

1.  Start the "Live system (amd64)".
2.  Run the "Install Debian" application.
3.  Follow the Calamares installer prompts, the following are just my choice, still leave the following up to user's choice of course:
    *   Language: "American English" (Default)
    *   Location: "Asia", "Kuala Lumpur", with locale "en\_GB.UTF-8"
    *   Keyboard: "English (US)", "Default"
4.  For partitioning, choose "Manual Partitioning", the following are just my choice to easily install, though I'd want this part to follow Butterbian (or better) approach of BTRFS setup as stated in the document:
    *   Create a "New Partition Table" with the "GPT" scheme.
    *   Create a 1024 MiB `fat32` partition for `/boot/efi` and set the `boot` flag.
    *   Create a `btrfs` partition using the remaining space for the root directory (`/`).
    *   If you have any additional disks, you can create a `btrfs` partition for the directory (`/ext1`, `/ext2`, ...).
5.  Proceed to set up your user account and complete the installation.

## Post Install

Opened Firefox, installed Vivaldi.

Configure Firefox from default these are what I did on top of default, switch tabs to vertical tabs, switch off "Check your spelling as you type", turn "Never show" for "Bookmarks toolbar", turn off "AI chatbot" from "Customize sidebar", switch on DRM-controlled content, switch on always show scrollbars, switch off recommend extensions as you browse, switch off recommend features as you browse, dismiss everything in Firefox Home, switch off everything under "Firefox Home Content", switch off everything under "Search Suggestions", switch on Tell websites not to see or share my data, switch off everything under "Passwords", switch off everything under "Firefox Data Collection and Use", switch off "Enable DNS over HTTPS using:", download and apply theme of https://addons.mozilla.org/en-US/firefox/addon/biscuit-mojas84/, before closing Firefox I press "Clear Data" under "Cookies and Site Data" ticking everything + when everything.

Opened Vivaldi, pressed continue without toggling on "Set up Vivaldi for keyboard use and assistive technology" and without toggling on "Share crash reports to help us improve product quality". Skip Vivaldi account creation, uncheck "Keep Vivaldi in Taskbar", keep check "Set Vivaldi as Default Browser", uncheck "Import from Other Browsers". Select "No Blocking", chose a default style of "Auto-hide" before configuring further on top of that. Kept Vivaldi theme with "Follow Operating System Theme Color" checked. when asked to "Pick your panels", I only kept "Bookmarks", "Downloads", "History", "Translate", "Windows and Tabs", "Sessions". For "Easy access to your favorites", everything is unchecked. Toggled off "Enable Mail, Calendar and Feeds". Remove all shortcuts and widgets from start page, remove all bookmarks and emptied its trash. Uncheck "Show start page navigation"

Configure Vivaldi further through Settings. On top of what's already defaulted checked/unchecked. Uncheck "Show Exit Confirmation Dialog". only en-US in the "Accept Languages" list. Check "Use Simple Scrollbars". For "Enable UI Auto-hide", just check "Tab Bar". Menu Position is Horizontal. Set Theme Schedule to No Schedule, and set Theme to Dark. Put Tabs on the Left. Untick "Confirm When Closing {x} or More Tabs". Panel Position set to Right Side. Enable Show Panel Toggle. Enable Floating Panel, Disable Auto-Close Inactive Panel. Enable QR Code Generator. Check "Open Bookmarks in New Tab". Uncheck "Confirm When Opening {x} or More Bookmarks". Set to "Google" for Default Search Engine, Private Window Search Engine, as well as Image Search Engine. Check "Ask Websites Not to Track Me". Uncheck "Block Ads on Abusive Sites". Uncheck "Phishing and Malware Protection", Uncheck "DNS to Help Resolve Navigation Errors". Set "Save Browsing History" to "Forever". Uncheck "Save Webpage Passwords". Uncheck "Save and Fill Payment Methods". Uncheck "Allow Sites to Check for Saved Payment Methods". Uncheck "Save and Fill Addresses". Under "Website Permissions", Allow Popups, Allow Insecure Content, Allow Intrusive Ads. Remove all "Location Overrides". Pick "Never Save Energy". Check "Save Files to Default Location Without Asking". Check "Show Selected Text Translate Button". Turn on "Suggestions in Address Field" and Turn on "Suggestions in Search Field". Also added `--ozone-platform=x11` argument everytime vivaldi start. now at the moment there's no way to keep top menu to always show while having tab to still auto-hide I had to do a workaround according to the following:
"""
Vivaldi is configured to keep its native GNOME title bar and horizontal menu visible while the tab bar auto-hides. The setup uses **Use Native Window**, the **X11 backend**, and a small custom CSS rule for the horizontal menu. This single record documents the diagnosis, exact changes, verification, and reversal on 4 October 2026.

## Initial configuration

The machine runs Debian with GNOME in a Wayland desktop session. Vivaldi is version `8.2.4133.80 stable`. The original main process was launched as `/opt/vivaldi/vivaldi-bin --new-window`; its renderer and GPU processes used `--ozone-platform=wayland`.

The existing profile at `/home/miubomz/.config/vivaldi/Default/Preferences` already contained:

```json
{
  "vivaldi.windows.use_native_decoration": true,
  "vivaldi.appearance.disable_title_bar": false,
  "vivaldi.auto_hide.enabled": true,
  "vivaldi.auto_hide.tab_bar": true,
  "vivaldi.auto_hide.address_bar": false,
  "vivaldi.auto_hide.bookmarks_bar": false,
  "vivaldi.auto_hide.panel": false,
  "vivaldi.auto_hide.status_bar": false
}
```

These are flattened preference paths for readability; the actual JSON uses nested objects.

## Diagnosis

Vivaldi’s installed UI code puts its own title bar inside the top auto-hide wrapper when UI Auto-Hide is enabled. The wrapper moves offscreen as a unit. There is no separate title-bar auto-hide preference. The native-window setting selects window controls outside that Vivaldi UI structure and requires restarting the browser.

The relevant installed files inspected were `/opt/vivaldi/resources/vivaldi/bundle.js`, `/opt/vivaldi/resources/vivaldi/style/common.css`, and `/opt/vivaldi/resources/vivaldi/prefs_definitions.json`. The inspected code sets the built-in title bar’s auto-hide state when its controls container is `titlebar`, and the CSS translates `.auto-hide-wrapper.top` offscreen.

The native-window setting alone did not provide the requested result in the original Wayland session. Testing the X11 backend established that GNOME could supply a separate native title bar in this environment. The precise underlying Wayland cause was not established; an old Vivaldi bug report was not treated as proof of a current bug.

## Exact steps performed

1. Read the existing profile preferences and running process arguments. Confirmed that Use Native Window and Show Title Bar were already enabled and that only Tab Bar was selected for auto-hide.

2. Checked Vivaldi’s official appearance and auto-hide documentation and Chromium’s documented backend-selection flag.

3. Created a temporary, separate Vivaldi test profile with native decoration enabled and tab auto-hide enabled. Launched it using:

```bash
/usr/bin/vivaldi-stable --user-data-dir=/tmp/vivaldi-titlebar-test-7d_6q5bq --ozone-platform=x11 --no-first-run --no-default-browser-check about:blank
```

4. Inspected the test window with `xprop`. GNOME reported `_NET_FRAME_EXTENTS = 0, 0, 37, 0`, confirming a separate 37-pixel top decoration on the maximized test window.

5. Backed up the original profile’s Preferences, Secure Preferences, and Sessions directory under `/home/miubomz/.config/vivaldi/titlebar-backup-20261004/` before restarting.

6. Created the per-user launcher `/home/miubomz/.local/share/applications/vivaldi-stable.desktop` from `/usr/share/applications/vivaldi-stable.desktop`. Added `--ozone-platform=x11` to each of its three Exec entries:

```ini
Exec=/usr/bin/vivaldi-stable --ozone-platform=x11 %U
Exec=/usr/bin/vivaldi-stable --ozone-platform=x11 --new-window
Exec=/usr/bin/vivaldi-stable --ozone-platform=x11 --incognito
```

7. Sent SIGTERM to the test browser’s main process and the original browser’s main process, waiting for each to exit. No forced kill was used. The original profile recorded its exit state as `SessionEnded`.

8. Relaunched the original profile with:

```bash
/usr/bin/vivaldi-stable --ozone-platform=x11 --restore-last-session
```

9. Refreshed the per-user desktop application database with:

```bash
update-desktop-database /home/miubomz/.local/share/applications
```

10. Rechecked the running original profile’s backend, window decoration properties, and saved auto-hide preferences. Removed the temporary test profile after its process had exited.

## Verification and limits

The original profile’s relaunched main process contained `--ozone-platform=x11 --restore-last-session`. Its native window again reported:

```text
_NET_FRAME_EXTENTS(CARDINAL) = 0, 0, 37, 0
_MOTIF_WM_HINTS(_MOTIF_WM_HINTS) = 0x2, 0x0, 0x1, 0x0, 0x0
_NET_WM_STATE(ATOM) = _NET_WM_STATE_MAXIMIZED_HORZ, _NET_WM_STATE_MAXIMIZED_VERT
```

The preference checks still showed native decoration enabled, UI Auto-Hide enabled, and Tab Bar auto-hide enabled. The native title bar belongs to GNOME’s window frame, so Vivaldi’s internal tab auto-hide wrapper cannot move it offscreen.

Initial title-bar verification used the live window manager’s properties and the installed UI implementation. Native screenshot and pointer controls were unavailable, so the initial hover behavior was not separately verified visually. The title bar is expected in normal and maximized windows; true fullscreen intentionally removes native window decorations. The later horizontal-menu verification is documented below.

## Keeping the horizontal menu visible

After the title-bar change, the user reported that the horizontal menu was missing. The saved setting `vivaldi.menu.display=1` was already correct: the installed preference enum maps `1` to Horizontal (`top`). The user confirmed that the menu appeared on hover and requested that it remain visible all the time.

The installed React code places the horizontal menu in the top auto-hide wrapper whenever UI Auto-Hide is enabled. A custom CSS rule keeps that wrapper in place, leaves its menu interactive, and hides only its other children when the wrapper is not shown. `visibility:hidden` preserves the dimensions used by Vivaldi’s native reveal hotspot. A matching 30-pixel header reservation prevents the menu from covering the address bar. The rule applies to Linux native windows outside fullscreen.

### Exact menu changes

1. Created `/home/miubomz/.config/vivaldi/custom-ui/persistent-horizontal-menu.css` containing the CSS below.

2. Tested it in a browser fixture using Vivaldi’s installed `common.css` and the horizontal-menu structure from its installed React implementation. Clicked the menu while tabs were hidden, revealed and clicked a tab, and hid tabs again. The menu stayed visible and clickable. The final maximized layout measured menu height 30px, header height 30px, address-bar top 30px, and wrapper height 70px. Hidden tabs had `visibility:hidden` and `pointer-events:none`; revealed tabs had `visibility:visible` and `pointer-events:auto`. The wrapper’s height stayed unchanged. In the fullscreen fixture, the custom rules stopped applying and the hidden menu moved offscreen.

3. Backed up the current launcher as `/home/miubomz/.config/vivaldi/titlebar-backup-20261004/vivaldi-stable.desktop.before-menu`.

4. Added `--enable-features=VivaldiCssMods` to each of the launcher’s three Exec entries, preserving `--ozone-platform=x11`.

5. Gracefully stopped the current main browser process with SIGTERM. Backed up its saved preferences as `/home/miubomz/.config/vivaldi/titlebar-backup-20261004/Preferences.before-menu`.

6. Set `vivaldi.appearance.css_ui_mods_directory` to `/home/miubomz/.config/vivaldi/custom-ui` while Vivaldi was stopped. Retained horizontal menu, native window decoration, and tab auto-hide settings.

7. Relaunched the original profile with `vivaldi-stable --ozone-platform=x11 --enable-features=VivaldiCssMods --restore-last-session` and refreshed the per-user desktop application database.

8. Watched the custom CSS file during launch with Linux inotify. Observed both `IN_OPEN` and `IN_ACCESS`, confirming Vivaldi opened and read the file. Rechecked the saved CSS directory and active launch flags. GNOME still reported the separate 37-pixel native title bar.

### Final launcher entries

```ini
Exec=/usr/bin/vivaldi-stable --ozone-platform=x11 --enable-features=VivaldiCssMods %U
Exec=/usr/bin/vivaldi-stable --ozone-platform=x11 --enable-features=VivaldiCssMods --new-window
Exec=/usr/bin/vivaldi-stable --ozone-platform=x11 --enable-features=VivaldiCssMods --incognito
```

### Exact custom CSS

```css
/* Vivaldi 8.2: keep the horizontal menu visible while tabs auto-hide.
 * Scoped to Linux native windows, outside fullscreen. Remove this file and
 * restart Vivaldi to restore the built-in menu auto-hide behavior.
 */
#browser.linux.native.auto-hide:not(.fullscreen):has(> .auto-hide-wrapper.top > .topmenu) {
  --persistent-menu-height: 30px;
}

/* Reserve menu space above the address bar and page. */
#browser.linux.native.auto-hide:not(.fullscreen):has(> .auto-hide-wrapper.top > .topmenu) > #header {
  display: block !important;
  flex: 0 0 var(--persistent-menu-height) !important;
  height: var(--persistent-menu-height) !important;
  min-height: var(--persistent-menu-height) !important;
}

/* Preserve child dimensions for Vivaldi's tab reveal hotspot. */
#browser.linux.native.auto-hide:not(.fullscreen) > .auto-hide-wrapper.top:has(> .topmenu) {
  top: 0 !important;
  left: 0 !important;
  width: 100% !important;
  transform: none !important;
  border-radius: 0 !important;
}

#browser.linux.native.auto-hide:not(.fullscreen) > .auto-hide-wrapper.top:has(> .topmenu):not(.show) {
  background: transparent !important;
  box-shadow: none !important;
}

#browser.linux.native.auto-hide:not(.fullscreen) > .auto-hide-wrapper.top > .topmenu {
  flex: 0 0 var(--persistent-menu-height) !important;
  height: var(--persistent-menu-height) !important;
  min-height: var(--persistent-menu-height) !important;
  border-radius: 0 !important;
  margin: 0 !important;
  pointer-events: auto !important;
  touch-action: auto !important;
}

/* Hide only the other auto-hide children; keep their measured sizes. */
#browser.linux.native.auto-hide:not(.fullscreen) > .auto-hide-wrapper.top:has(> .topmenu):not(.show) > :not(.topmenu) {
  visibility: hidden !important;
  pointer-events: none !important;
}
```

The installed binary confirms `VivaldiCssMods` as the feature name and `vivaldi-css-mods` as its flag ID. Vivaldi’s `window.html` already includes its CSS-mod datasource stylesheet. The feature exposes Custom UI Modifications in Appearance settings.

Verification confirmed the stylesheet’s layout and click behavior in the fixture and that the live browser read the file. Native desktop screenshot and pointer controls remained unavailable, so the final live menu and hotspot interaction were not separately verified visually. CSS selectors depend on Vivaldi’s current UI structure and may need adjustment after a browser update.

## Reproduce or reverse the change

To reproduce the title bar: enable **Settings → Appearance → Window Appearance → Use Native Window**, retain **Appearance → UI Auto-Hide → Tab Bar**, fully exit Vivaldi, and start it with `vivaldi-stable --ozone-platform=x11`. To keep the horizontal menu visible too, save the exact CSS above in the custom-ui directory, select that directory in Custom UI Modifications, and enable the `VivaldiCssMods` feature. Use the final launcher entries above for persistence through GNOME’s application launcher. A terminal launch must include the same flags.

To reverse only the menu change while retaining the native title bar, rename `persistent-horizontal-menu.css` to `persistent-horizontal-menu.css.disabled` and restart Vivaldi. Remove `--enable-features=VivaldiCssMods` from all three launcher Exec entries if Custom UI Modifications is no longer needed. To also reverse the X11 backend change, remove `--ozone-platform=x11`. After launcher edits, run `update-desktop-database /home/miubomz/.local/share/applications`, fully exit Vivaldi, and launch it again. The original preferences and session backup, plus the state before the menu change, remain at `/home/miubomz/.config/vivaldi/titlebar-backup-20261004/`. Restoring the full profile backup is not needed for these reversals.

## Sources

- [Vivaldi browser appearance customization](https://help.vivaldi.com/desktop/appearance-customization/browser-appearance-customization-on-desktop/) documents Use Native Window, the required restart, and Show Title Bar.

- [Vivaldi auto-hide browser toolbars](https://help.vivaldi.com/desktop/appearance-customization/auto-hide-interface/) documents the available auto-hide controls.

- [Chromium Ozone overview](https://chromium.googlesource.com/chromium/src/+/main/docs/ozone_overview.md) documents runtime backend selection using `--ozone-platform` and the X11 backend.

The 37-pixel frame measurements, launcher edits, process arguments, and profile preferences are local observations from this debugging session.
"""

Open terminal, install Git.

then I had to fix the forky trixie mismatch (weird) eventhough installed directly from debian testing gnome live iso channel with:
```
sudo tee /etc/apt/sources.list >/dev/null <<'EOF'
deb http://deb.debian.org/debian forky main non-free-firmware
deb-src http://deb.debian.org/debian forky main non-free-firmware
EOF
```

and
`sudo apt full-upgrade`

installed flatpak with `sudo apt install flatpak` and `sudo apt install gnome-software-plugin-flatpak` and `flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo`

then I installed time sync fix with
```
sudo apt install systemd-timesyncd
sudo systemctl enable --now systemd-timesyncd
```

then I restarted

Open https://extensions.gnome.org, install and enable
https://extensions.gnome.org/extension/615/appindicator-support/
https://extensions.gnome.org/extension/3396/color-picker/
https://extensions.gnome.org/extension/3628/arcmenu/
https://extensions.gnome.org/extension/1160/dash-to-panel/
https://extensions.gnome.org/extension/36/lock-keys/
https://extensions.gnome.org/extension/2087/desktop-icons-ng-ding/
https://extensions.gnome.org/extension/7/removable-drive-menu/
https://extensions.gnome.org/extension/6096/smile-complementary-extension/
https://extensions.gnome.org/extension/3843/just-perfection/
https://extensions.gnome.org/extension/3733/tiling-assistant/
https://extensions.gnome.org/extension/6619/window-on-top/
https://extensions.gnome.org/extension/770/force-quit/
https://extensions.gnome.org/extension/3193/blur-my-shell/

then I install `sudo apt-get install -y sassc libsass1`
then I install `sudo apt install gir1.2-gnomedesktop-3.0 gir1.2-gnomedesktop-4.0 libgnome-menu-3-dev gnome-shell-extension-apps-menu gnome-shell-extension-arc-menu -y`

then I restart

then I unpin everything from dash to panel

arcmenu settings, leave what is already default and toggle on "Display ArcMenu on All Panels". Toggle on "Hide Overview on Startup". Menu Theme, Toggle on "Override Theme" and change Border Width to 0, Boredr Radius to 20, and Font Size to 12. Menu Visual Appearance, Left Panel Width 375, Right Panel Width 200. Fine Tune, Toggle on Show Application Descriptions, Toggle off "Group Apps Alphabetically on List Views". Remove all the Pinned Apps. Install GNOME Console, and set Application Shortcuts default of org.gnome.Terminal.desktop to org.gnome.Console.desktop. "Search Options", Toggle on "Show Search Result Descriptions" and toggle on "Highlight search result terms". ArcMenu Layout Tweaks, Default View change to All Programs. Choose distro-debian-symbolic for icon and set Icon Size 32

dash to panel settings, leave what is already default and unvisible "Show Applications button". Border Radius 16, App Icon Margin 0. Toggle on "Animate hovering app icons" and animation type "Ripple". Running indicator position on the right. running Focused set to segmented, settings toggle on icon dominant color, highlight opacity 15, toggle on indicator color - icon dominant and running unfocused set to dashes. toggle on override panel theme background opacity and set panel background opacity to 90%. behaviour toggle off show notification counter badge. Toggle on Isolate Workspaces. Toggle on Isolate Monitors. Toggle on click empty space to close overview and toggle on disable show overview on startup. Toggle on use hotkeys to activate apps. Toggle on App details menu item in secondary menu options. Tray font size 16 and leftbox font size 16. tray item padding 2, status icon padding 2, and leftbox padding 2. Toggle on Activate panel menu buttons on click only.

Desktop Icons NG (DING) settings, leave what is already default. toggle on show network drives in the desktop, toggle on show hidden files, toggle on show a context menu item to delete permanently, and set show image thumbnails to always.

Just Perfection settings, leave what is already default. turn on Window Demands Attention Focus on. change Startup Status to Desktop.

Tiling Assistant, leave what is already default, and disable all keybindings.

I also installed ChatGPT, but please ignore that.

go to https://github.com/vinceliuice/Fluent-icon-theme, downlaod zip, and do `./install.sh --all`.

turn on show hidden files for file manager. made a .icons folder, and inside that folder made a fluent and fluent-dark folders. copied content from Fluent-icon-theme-master/cursors/dist into the fluent folder and Fluent-icon-theme-master/cursors/dist-dark into the fluent-dark folder.

go to https://github.com/vinceliuice/Fluent-gtk-theme, download zip, extract, and do `./install.sh --theme all --libadwaita --tweaks blur round`

open GNOME tweaks. on top of what is already default, set rendering hinting to full. set interface text to noto sans regular, document text to noto sans regular, and monospace text to noto mono regular. in styles, set cursor to Fluent-dark. icons to Fluent-dark (make sure to select the one I selected because there's multiple) and legacy applications to Fluent-round-Dark-compact. toggle on keyboard show extended input sources. turn on titlebar buttons for maximize and minimize. and set titlebar actions middle-click to minimize.

there was a dark mode and transparency blur issue so I had to use chatgpt to fix it and document it for me to get what I desired:
"""
GNOME Fluent Dark theme fix
Applied 4 October 2026 at 16:31 MYT.

Cause: GNOME already preferred dark mode, but the GTK 4 user stylesheet
pointed to Fluent-round-grey-Light and forced white backgrounds. Settings,
Tweaks and the Desktop Icons NG right-click menu use GTK 4.

Process:
1. Checked the GNOME color preference and current GTK theme.
2. Traced the GTK 4 stylesheet and asset symlinks to Light variants.
3. Confirmed dark=True in a libadwaita probe, while user CSS forced black text.
4. Backed up the complete GTK 4 configuration, preserving its symlinks.
5. Repointed gtk.css, gtk-dark.css and assets in
   /home/miubomz/.config/gtk-4.0/ to matching components in
   /home/miubomz/.themes/Fluent-round-Dark-compact/gtk-4.0/.
6. Verified dark=True, white text and zero CSS parser messages.
7. Restarted Desktop Icons NG; it is enabled and active with a new process.

Current configuration: Fluent Dark is applied to GTK 4. Blur my Shell
application blur is enabled globally with no app exclusions. Actor opacity
remains 255, allowing Fluent to control transparency while text stays solid.
Focused windows retain blur. The visual result has not been inspected.

Backup and exact change record:
/home/miubomz/.config/gtk-4.0-backups/20261004-163141/
/home/miubomz/.config/gtk-4.0-backups/20261004-163141/change-record.json

Undo: restore gtk.css, gtk-dark.css and assets from that backup, preserving
symlinks; reopen affected apps and restart Desktop Icons NG.

GTK CSS loading: https://gnome.pages.gitlab.gnome.org/gtk/gtk4/class.CssProvider.html
GTK user CSS priority: https://docs.gtk.org/gtk4/const.STYLE_PROVIDER_PRIORITY_USER.html

The earlier cloud troubleshooting Page could not be updated because its
read operation returned page_read_forbidden.

Transparent application blur fix
Applied 4 October 2026 at 16:46 MYT.
Fluent's blur variant supplies transparent GTK backgrounds. Blur my Shell
v72 was active and supports GNOME 50, but its application blur switch was
off and its whitelist was empty.

Backed up preferences, then enabled application blur and added Tweaks and
Settings (their Wayland app IDs and X11 class names) to the whitelist.
Kept dynamic blur, which blurs actual content behind the window. Set actor
opacity to 255 so the theme controls background transparency and text stays
solid. Disabled dynamic-opacity because it hides blur on focused windows.

Verified saved settings, the active extension and its application service.
No recent relevant Shell errors appeared. The visual result was not inspected.

Backup: /home/miubomz/.config/blur-my-shell-backups/20261004-164619/
Undo only this change:
python3 /home/miubomz/.config/blur-my-shell-backups/20261004-164619/restore.py

Upstream explanation: https://github.com/aunetx/blur-my-shell#functionalities

All applications blur
Applied 4 October 2026 at 16:47 MYT, as requested.
Changed application enable-all from false to true. Application blur remains
on. Kept the existing blacklist (Plank, com.desktop.ding, Conky), opacity 255,
dynamic-opacity off and dynamic blur. The previous Tweaks/Settings whitelist
is retained but inactive while all-applications mode is on.

Backup: /home/miubomz/.config/blur-my-shell-backups/20261004-164748/
Undo only global mode and return to the previous application selection:
python3 /home/miubomz/.config/blur-my-shell-backups/20261004-164748/restore.py

Removed all application exclusions
Applied 4 October 2026 at 16:49 MYT, as requested.
Cleared the application blacklist. Global application blur remains on.
Plank, Desktop Icons NG and Conky are now eligible along with other apps.
Verified enable-all=true, blur=true and an empty blacklist.

Backup: /home/miubomz/.config/blur-my-shell-backups/20261004-164905/
Undo only this change and restore the previous exclusions:
python3 /home/miubomz/.config/blur-my-shell-backups/20261004-164905/restore.py
"""

open settings, on top of what is already default. toggle off power saving automatic screen blank. toggle off hot corner. change appearance to Dark. turn off mouse acceleration.

then again I noticed the desktop background is blurred even when nothing is open so I had to add the defaults again. The exclusions are Plank, Desktop Icons NG (your desktop icons and right-click surface), and Conky. Those are Blur my Shell’s existing defaults.
"""
GNOME Fluent Dark theme fix
Applied 4 October 2026 at 16:31 MYT.

Cause: GNOME already preferred dark mode, but the GTK 4 user stylesheet
pointed to Fluent-round-grey-Light and forced white backgrounds. Settings,
Tweaks and the Desktop Icons NG right-click menu use GTK 4.

Process:
1. Checked the GNOME color preference and current GTK theme.
2. Traced the GTK 4 stylesheet and asset symlinks to Light variants.
3. Confirmed dark=True in a libadwaita probe, while user CSS forced black text.
4. Backed up the complete GTK 4 configuration, preserving its symlinks.
5. Repointed gtk.css, gtk-dark.css and assets in
   /home/miubomz/.config/gtk-4.0/ to matching components in
   /home/miubomz/.themes/Fluent-round-Dark-compact/gtk-4.0/.
6. Verified dark=True, white text and zero CSS parser messages.
7. Restarted Desktop Icons NG; it is enabled and active with a new process.

Current configuration: Fluent Dark is applied to GTK 4. Blur my Shell
application blur is enabled globally with Plank, Desktop Icons NG and Conky
excluded (see the desktop wallpaper fix below). Actor opacity remains 255,
allowing Fluent to control transparency while text stays solid.
Focused windows retain blur. The visual result has not been inspected.

Backup and exact change record:
/home/miubomz/.config/gtk-4.0-backups/20261004-163141/
/home/miubomz/.config/gtk-4.0-backups/20261004-163141/change-record.json

Undo: restore gtk.css, gtk-dark.css and assets from that backup, preserving
symlinks; reopen affected apps and restart Desktop Icons NG.

GTK CSS loading: https://gnome.pages.gitlab.gnome.org/gtk/gtk4/class.CssProvider.html
GTK user CSS priority: https://docs.gtk.org/gtk4/const.STYLE_PROVIDER_PRIORITY_USER.html

The earlier cloud troubleshooting Page could not be updated because its
read operation returned page_read_forbidden.

Vivaldi follow-up
Vivaldi's browser interface uses its own theme. Checked only appearance
preferences in /home/miubomz/.config/vivaldi/Default/Preferences: the active
theme is Vivaldi1 (Vivaldi), with light background #f5f5f5. Theme scheduling
is disabled (enabled=0, confirmed as off in the installed preference schema).
The available Dark theme is Vivaldi2. Its configured OS dark slot already
uses Dark, but that slot is inactive while scheduling is off. The custom
UI CSS controls menu layout and does not force light colors.

To switch immediately: Vivaldi Settings > Themes > select Dark.
To follow GNOME: Settings > Themes > Theme schedule > Operating system,
with Dark assigned to the dark-mode slot. No Vivaldi settings were changed.
Official guide: https://help.vivaldi.com/desktop/appearance-customization/browser-themes/

Transparent application blur fix
Applied 4 October 2026 at 16:46 MYT.
Fluent's blur variant supplies transparent GTK backgrounds. Blur my Shell
v72 was active and supports GNOME 50, but its application blur switch was
off and its whitelist was empty.

Backed up preferences, then enabled application blur and added Tweaks and
Settings (their Wayland app IDs and X11 class names) to the whitelist.
Kept dynamic blur, which blurs actual content behind the window. Set actor
opacity to 255 so the theme controls background transparency and text stays
solid. Disabled dynamic-opacity because it hides blur on focused windows.

Verified saved settings, the active extension and its application service.
No recent relevant Shell errors appeared. The visual result was not inspected.

Backup: /home/miubomz/.config/blur-my-shell-backups/20261004-164619/
Undo only this change:
python3 /home/miubomz/.config/blur-my-shell-backups/20261004-164619/restore.py

Upstream explanation: https://github.com/aunetx/blur-my-shell#functionalities

All applications blur
Applied 4 October 2026 at 16:47 MYT, as requested.
Changed application enable-all from false to true. Application blur remains
on. Kept the existing blacklist (Plank, com.desktop.ding, Conky), opacity 255,
dynamic-opacity off and dynamic blur. The previous Tweaks/Settings whitelist
is retained but inactive while all-applications mode is on.

Backup: /home/miubomz/.config/blur-my-shell-backups/20261004-164748/
Undo only global mode and return to the previous application selection:
python3 /home/miubomz/.config/blur-my-shell-backups/20261004-164748/restore.py

Removed all application exclusions
Applied 4 October 2026 at 16:49 MYT, as requested.
Cleared the application blacklist. Global application blur remains on.
Plank, Desktop Icons NG and Conky are now eligible along with other apps.
Verified enable-all=true, blur=true and an empty blacklist.

Backup: /home/miubomz/.config/blur-my-shell-backups/20261004-164905/
Undo only this change and restore the previous exclusions:
python3 /home/miubomz/.config/blur-my-shell-backups/20261004-164905/restore.py

Desktop wallpaper blur fix and restored exclusions
Applied 4 October 2026 at 17:07 MYT.

Cause: Desktop Icons NG (DING) draws the desktop icons and right-click
surface in a nearly transparent window covering the desktop. With Blur my
Shell application blur enabled for all applications and the blacklist empty,
this desktop window was also eligible for blur. That explains why the
wallpaper could be blurred even with no ordinary application covering it.

This installation uses GNOME Shell 50.5, Blur my Shell v72 and DING v99.
DING now uses the window class com.rastersoft.ding. Blur my Shell's built-in
blacklist still uses its older name, com.desktop.ding. Restoring only the
built-in defaults would therefore miss the installed desktop window.

Fix:
1. Backed up Blur my Shell preferences and the previous documentation.
2. Restored the built-in exclusions for Plank, legacy Desktop Icons NG and
   Conky, and added the current Desktop Icons NG identifier.
3. Saved the application blacklist as:
   ['Plank', 'com.desktop.ding', 'Conky', 'com.rastersoft.ding']
4. Kept global application blur enabled, opacity 255, dynamic-opacity off
   and dynamic blur. The wallpaper image and desktop icons remain intact.
5. The extension re-evaluates existing windows on blacklist changes, so
   the exclusion applies live without a session restart.

Verification: GNOME Shell logs confirmed the live four-entry blacklist
update and the desktop window class com.rastersoft.ding. Blur my Shell and
DING are both active. A full before/after settings diff showed that only
blacklist changed. Temporary diagnostic logging was restored to its prior
state. No new GNOME Shell error lines appeared during this change.
The visual appearance was not independently inspected: the GNOME Wayland
screenshot interface denied screenshot access.

To repeat the fix on this installation:
gsettings --schemadir /home/miubomz/.local/share/gnome-shell/extensions/blur-my-shell@aunetx/schemas set org.gnome.shell.extensions.blur-my-shell.applications blacklist "['Plank', 'com.desktop.ding', 'Conky', 'com.rastersoft.ding']"

Backup and exact change record:
/home/miubomz/.config/blur-my-shell-backups/20261004-170701-desktop/
The folder includes before/after settings, settings.diff, change-record.json,
the prior documentation and focused runtime verification logs.

Undo this entire desktop exclusion fix and return to the previous empty list:
python3 /home/miubomz/.config/blur-my-shell-backups/20261004-170701-desktop/restore.py
This undo restores only the application blacklist; it can bring back the
unwanted desktop wallpaper blur.

Source details checked in the installed extensions:
DING app/ding.js:212 defines com.rastersoft.ding; app/desktopGrid.js:52-58
creates the transparent desktop application window; app/stylesheet.css:36-39
sets its near-transparent background.
Blur my Shell components/applications.js:310-335 matches the blacklist
against the window class; extension.js:551-557 applies blacklist changes
live. The installed schema lists the three built-in exclusions at line 440.
Upstream application blur modes:
https://github.com/aunetx/blur-my-shell#functionalities
"""

I should note that all of this theme setup, switching light/dark mode, and setting blur properly should be a considered for MiuUtil Cheats.

then I ran `sudo apt purge gnome-calculator gnome-contacts gnome-calendar evolution fcitx5 gnome-font-viewer goldendict-ng loupe gnome-music malcontent shotwell thunderbird gnome-tour totem gnome-weather xiterm+thai kasumi -y && sudo apt update && sudo apt autoclean -y && sudo apt autopurge -y && sudo apt autoremove -y && sudo apt clean -y`

then I applied "disable uac" with:
"""
# Disable administrator password prompts on Debian GNOME

Applied on 4 October 2026 at 17:24 MYT for `miubomz` on Debian forky/sid with GNOME. You chose to remove both terminal `sudo` password prompts and desktop administrator prompts. Both rules are now installed and verified. This guide explains their configuration, checks, and undo steps.

## Current installation

| File | Owner | Permissions |
| --- | --- | --- |
| `/etc/sudoers.d/99-miubomz-nopasswd` | `root:root` | `0440` |
| `/etc/polkit-1/rules.d/00-miubomz-local-nopasswd.rules` | `root:root` | `0644` |

The installer recorded the previous state in `/var/backups/passwordless-admin-miubomz-u9w808fb`. Both target files were absent before installation, so the removal commands in the undo section restore their earlier state. The existing `/etc/sudoers` and packaged rules were not edited.

The reusable installer is saved beside this guide as `apply-passwordless-admin.py`. It validates the sudo policy before and after installation, preserves existing target files, and restores changed policy files if verification fails.

## Chosen behavior

| Area | Configuration | Scope |
| --- | --- | --- |
| Terminal commands | Passwordless `sudo` for every command | Only `miubomz`; any target user or group; also applies to SSH sessions and background programs using this account |
| Desktop authorization | Automatically approve all polkit actions | Only `miubomz` in an active local session |

These settings allow programs running as your account to obtain unrestricted administrator access without asking you. The desktop rule also approves polkit actions that would otherwise be denied, because it grants every action for the matching session. The local session restriction does not protect you from programs already running in that session.

Linux uses several authentication systems. This covers `sudo` and polkit, which handles many GNOME administrator dialogs. Login, screen unlock, disk encryption, keyring unlock, `su`, and applications with their own authentication can still request credentials. Polkit also handles some command-line tools, including `pkexec`; it is not limited to graphical applications. [Polkit manual](https://polkit.pages.freedesktop.org/polkit/polkit.8.html)

## Why improve the original snippet

Your original rule is valid for passwordless `sudo`. Setting ownership to `root:root`, mode to `0440`, and checking the complete policy are appropriate. However, writing the live file with `tee` before validating it can activate a malformed rule. `visudo` checks edits before saving them. Your snippet also leaves polkit authorization unchanged. [Debian visudo manual](https://manpages.debian.org/unstable/sudo/visudo.8.en.html)

The rule below uses `(ALL:ALL)` to cover any target user and group, matching Debian's usual administrator permissions. Your original `(ALL)` allows any target user but does not independently grant every target group. [Debian sudoers manual](https://manpages.debian.org/unstable/sudo/sudoers.5.en.html)

## Keep a recovery terminal open

Open a terminal as `miubomz` and run:

```bash
sudo -i
```

Enter your existing password if requested. Keep this root shell open until both checks succeed. Run the installation commands below in this shell, without adding `sudo`. Use a second terminal as your normal user for testing.

First check the existing policy:

```bash
visudo -c
cat /etc/sudoers
```

Continue only if the policy parses successfully. Confirm that `/etc/sudoers` contains `@includedir /etc/sudoers.d` or the older `#includedir /etc/sudoers.d`. If it does not, use `visudo` to add that line, then check again. A filename containing a dot or ending in `~` is ignored by this include mechanism. [Debian sudoers manual](https://manpages.debian.org/unstable/sudo/sudoers.5.en.html)

The next steps use two dedicated files. If either already exists, inspect it and save a backup outside the policy directories before editing or replacing it:

```text
/etc/sudoers.d/99-miubomz-nopasswd
/etc/polkit-1/rules.d/00-miubomz-local-nopasswd.rules
```

## Enable passwordless sudo

In the root shell, open the drop-in through `visudo`:

```bash
visudo -O -P -f /etc/sudoers.d/99-miubomz-nopasswd
```

Make the file contain this one line:

```sudoers
miubomz ALL=(ALL:ALL) NOPASSWD: ALL
```

Save and close the editor. `-O -P` makes `visudo` enforce the default owner and permissions, normally `root:root` and `0440` on Debian. If it reports a syntax error, choose `e` to fix it or `x` to abandon the edit. Do not choose `Q`, which saves despite errors. [Debian visudo manual](https://manpages.debian.org/unstable/sudo/visudo.8.en.html)

Check the entire policy:

```bash
visudo -c
```

Confirm that `/etc/sudoers.d/99-miubomz-nopasswd` appears as `parsed OK`.

In the second terminal, as `miubomz`, run:

```bash
sudo -k
sudo -n /usr/bin/id -u
```

The result should be `0`, with no password prompt. Clearing the cached credential first distinguishes the new rule from an earlier successful authentication; `-n` fails instead of prompting.

## Enable passwordless desktop authorization

In the root shell, run this block. It stages the rule under a name polkit ignores, sets ownership and permissions, then renames it into place:

```bash
install -o root -g root -m 0644 /dev/stdin /etc/polkit-1/rules.d/00-miubomz-local-nopasswd.rules.tmp <<'POLKIT'
polkit.addRule(function(action, subject) {
    if (subject.user === "miubomz" && subject.local && subject.active) {
        return polkit.Result.YES;
    }
});
POLKIT
```

After that command succeeds, run:

```bash
mv -T -- /etc/polkit-1/rules.d/00-miubomz-local-nopasswd.rules.tmp /etc/polkit-1/rules.d/00-miubomz-local-nopasswd.rules
```

Polkit reads `.rules` files in filename order and automatically reloads rules when they change. The `00-` prefix places this rule before the packaged rules found on this desktop. No reboot or service restart is needed. [Polkit manual](https://polkit.pages.freedesktop.org/polkit/polkit.8.html)

In the second terminal, launched inside your local GNOME desktop, run:

```bash
pkexec /usr/bin/id -u
```

The result should be `0`, with no authentication dialog. Also retry a desktop action that previously requested administrator authentication. Testing `sudo` alone does not test polkit.

In the root shell, check for rule loading errors:

```bash
journalctl -u polkit.service --since "5 minutes ago" --no-pager
```

There should be no JavaScript parsing or execution errors naming the new rule. After both tests succeed, close the recovery shell with `exit`.

## If a prompt remains

For `sudo`, inspect `sudo -l` and the full `visudo -c` output. Rules are processed in order; a later matching `PASSWD` entry can override an earlier `NOPASSWD` entry. Fix the relevant ordering with `visudo`. [Debian sudoers manual](https://manpages.debian.org/unstable/sudo/sudoers.5.en.html)

For polkit, check the journal for errors and confirm that the request comes from `miubomz` in an active local session. Remote or inactive sessions do not match this desktop rule. An earlier rule can take precedence. If `pkexec` succeeds without asking but an application still asks, identify whether that application uses a different authentication system. [Polkit manual](https://polkit.pages.freedesktop.org/polkit/polkit.8.html)

## Undo these changes

Use the recovery shell if it is still open. Otherwise, open a normal terminal and start a new root shell:

```bash
sudo -i
```

In that root shell, remove the two files created by this guide:

```bash
rm -- /etc/polkit-1/rules.d/00-miubomz-local-nopasswd.rules
rm -- /etc/sudoers.d/99-miubomz-nopasswd
visudo -c
```

If you edited pre-existing files instead of creating new ones, restore your backups instead of deleting them. If you added an include directive specifically for this guide, use `visudo` to restore the earlier main file as well.

In your normal terminal, invalidate all cached sudo credentials:

```bash
sudo -K
sudo -n /usr/bin/id -u
```

The second command should now fail with a password requirement if your original policy required one. Other pre-existing passwordless rules can still apply. Polkit reloads automatically, but previously cached temporary authorizations may persist briefly. Undoing the rules also does not stop any processes already running as root.

## Alternatives considered

| Option | Effect |
| --- | --- |
| Allow only selected commands and desktop actions | Removes prompts for specific tasks; best choice when those tasks can be listed precisely |
| Extend sudo's password cache | For example, `Defaults:miubomz timestamp_timeout=60` keeps authentication valid for 60 minutes, normally per terminal; it does not affect desktop polkit prompts |
| Make only sudo passwordless | Your original goal as expressed by the snippet; desktop polkit prompts remain |
| Make sudo and desktop polkit passwordless | Your selected approach, implemented above |

Restricted sudo rules need care: allowing a shell, package manager, editor with shell commands, or writable script can still provide unrestricted root access. A shorter list is useful only when the permitted commands and arguments enforce the intended limits. The cache setting is documented in the [Debian sudoers manual](https://manpages.debian.org/unstable/sudo/sudoers.5.en.html).

## Validation of this guide

The installed sudo rule passed the full `visudo -c` check. Running `sudo -k -n /usr/bin/id -u` as `miubomz` returned `0`, confirming administrator execution without relying on a cached password. Polkit authorization for `org.freedesktop.policykit.exec` succeeded without interaction for a `miubomz` process in the active local desktop session and for the current desktop application process. Running `pkexec --disable-internal-agent /usr/bin/id -u` also returned `0` without an authentication dialog. The installed files have the owners and permissions shown above, and the polkit journal showed no rule parsing or execution errors during verification.
"""

then I did `sudo apt install gir1.2-gnomedesktop-3.0 gir1.2-gnomedesktop-4.0 libgnome-menu-3-dev gnome-shell-extension-apps-menu gnome-shell-extension-arc-menu git wget gnome-shell-extension-apps-menu gnome-disk-utility fastfetch font-manager gnome-tweaks gnome-system-monitor yt-dlp libmpv-dev aptitude mc ncdu ddcutil ddccontrol gddccontrol ddccontrol-db i2c-tools curl ca-certificates fuse gir1.2-gnomedesktop-3.0 python3-dbus python3-gi gir1.2-glib-2.0 dbus python3-full xclip wl-clipboard devilspie2 ffmpeg ripgrep libsdl2-dev -y`

then I also did `sudo modprobe i2c-dev
sudo gpasswd -a "$USER" i2c`

then I downloaded the latest release of actions for nautilus: https://github.com/bassmanitram/actions-for-nautilus/releases

I also installed fetch with
```
sudo bash -c "$(curl -fsSL https://pacstall.dev/q/install)"

```

also installed starship with:
`curl -sS https://starship.rs/install.sh | sh`
and added `eval "$(starship init bash)"` to bashrc.


also installed ble.sh with
```
# TRIAL without installation

curl -L https://github.com/akinomyoga/ble.sh/releases/download/nightly/ble-nightly.tar.xz | tar xJf -
source ble-nightly/ble.sh

# Quick INSTALL to BASHRC (If this doesn't work, please follow Sec 1.3)

curl -L https://github.com/akinomyoga/ble.sh/releases/download/nightly/ble-nightly.tar.xz | tar xJf -
bash ble-nightly/ble.sh --install ~/.local/share
echo 'source -- ~/.local/share/blesh/ble.sh' >> ~/.bashrc
```

also installed homebrew with
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo >> /home/miubomz/.bashrc
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"' >> /home/miubomz/.bashrc
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"
sudo apt-get install build-essential
brew install gcc
```

also installed mise with
```
sudo apt install autoconf build-essential curl flex fop gcc git icu-devtools inotify-tools libcurl4-openssl-dev libedit-dev libgl1-mesa-dev libglu1-mesa-dev libicu-dev libncurses-dev libpam0g-dev libpng-dev libreadline-dev libssh-dev libssl-dev libwxgtk-webview3.2-dev libwxgtk3.2-dev libxml2-dev libxml2-utils libxslt1-dev m4 make unixodbc-dev unzip uuid-dev xsltproc zlib1g-dev bison -y

curl https://mise.run | sh
if ! grep -q 'mise activate' ~/.bashrc; then
    echo "eval \"\$(/home/$USER/.local/bin/mise activate bash)\"" >> ~/.bashrc
fi

eval "$(/home/$USER/.local/bin/mise activate bash)"
source ~/.bashrc
git config --global credential.helper store
mise use --global python@3.11
mise use --global rust@latest
mise use --global go@latest
mise use --global java@latest
mise use --global node@latest
```

I also installed vscode from https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-x64 and also applied the microsoft repo(? I think) when prompted during installation

I installed Black Box, and configure from the defaults. Toggle on Remember Window Size, Toggle off Show Header Bar, toggle on Drag Area, switch font to Noto Mono Regular 12. change working directory default to home directory.

I open console, and configure from defaults. toggle on unlimited scrollback,

the following is what I did to configure my terminal behaviour, defaults, and nautilus to my desired state:
```
# Terminal and Nautilus setup

Complete final configuration for `miubomz` on Debian Forky/Sid with GNOME, recorded 4 October 2026. Follow the numbered sections in order. All configuration and helper code is included here; no earlier guide is required. Commands are for Bash. Use your normal user account, with `sudo` only where shown.

The resulting setup:

- GNOME Console (`org.gnome.Console.desktop`, executable `kgx`) is this user's desktop default, the system `x-terminal-emulator` command, and Nautilus **Open in Terminal**.
- A new interactive terminal starts `fetch --infinite`. Type one ordinary character or press Ctrl+C to dismiss it; a single typed character is preserved. Wait for the prompt before pasting a command. Bash then uses Starship and ble.sh.
- Bash history has no entry or file size limit. Exact duplicate commands move to their newest position, including across terminals. Leading spaces and failed commands are retained.
- `mcedit` is the terminal editor. Explicit `python3` and `pip3` use Debian's system Python; unversioned `python` and `pip` follow Mise.
- Nautilus offers **Copy details**, **Open in Terminal**, **Execute command here**, and **Open in Code**. Execute uses Black Box, saves the entered command, shows its exit status, then waits for one key before closing.

## 1. Starting state and dependencies

At the start, fetch, Starship, and ble.sh were already installed, and `.bashrc` ended with Starship initialization and a direct ble.sh source command. Its old history limits were 1,000 entries in memory and 2,000 in the saved file. This guide replaces that shell configuration with the final version below.

The final `.bashrc` also activates the installed Homebrew and Mise environments. It expects Homebrew at `/home/linuxbrew/.linuxbrew/bin/brew` and Mise at `/home/miubomz/.local/bin/mise`. VS Code is already installed at `/usr/bin/code`. Keep those paths for this account; on a different account, adapt every `/home/miubomz` path in this guide.

Check the existing tools:

```bash
command -v fetch starship pacstall code
test -r "$HOME/.local/share/blesh/ble.sh"
test -x /home/linuxbrew/.linuxbrew/bin/brew
test -x "$HOME/.local/bin/mise"
```

Install the Debian dependencies that are missing. `mc` supplies `mcedit`; `util-linux` supplies `flock`. These commands use the configured Debian repositories:

```bash
sudo apt update
sudo apt install build-essential procps file git bash-completion curl xz-utils python3 python3-pip util-linux   mc gnome-console blackbox-terminal xdg-terminal-exec zenity wl-clipboard xclip   nautilus python3-nautilus python3-gi gir1.2-nautilus-4.1
```

Actions For Nautilus 2.0.1 is the extension used here. Skip this installation if it is already installed. Otherwise, install its Debian release package; no vendor code patch is needed:

```bash
terminal_setup_download=$(mktemp -d)
curl -fL https://github.com/bassmanitram/actions-for-nautilus/releases/download/v2.0.1/actions-for-nautilus_2.0.1_all.deb   -o "$terminal_setup_download/actions-for-nautilus_2.0.1_all.deb"
sudo apt install "$terminal_setup_download/actions-for-nautilus_2.0.1_all.deb"
rm -rf -- "$terminal_setup_download"
unset terminal_setup_download
```

If one of the original shell tools is missing, its installation commands are included here. Pacstall's installer installs Pacstall itself; the fetch recipe is named `fetch-git`, and its executable is `fetch`:

```bash
# Only if Pacstall is missing:
sudo bash -c "$(curl -fsSL https://pacstall.dev/q/install)"

# Only if fetch is missing:
pacstall -I fetch-git

# Only if Starship is missing:
curl -sS https://starship.rs/install.sh | sh

# Only if ble.sh is missing:
terminal_setup_download=$(mktemp -d)
curl -fL https://github.com/akinomyoga/ble.sh/releases/download/nightly/ble-nightly.tar.xz   -o "$terminal_setup_download/ble-nightly.tar.xz"
tar -xJf "$terminal_setup_download/ble-nightly.tar.xz" -C "$terminal_setup_download"
bash "$terminal_setup_download/ble-nightly/ble.sh" --install "$HOME/.local/share"
rm -rf -- "$terminal_setup_download"
unset terminal_setup_download
```

The complete `.bashrc` below already initializes Starship and ble.sh. Do not append separate initialization commands afterward.

If Homebrew is missing and you want the same environment activation, install it with its official installer:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Mise and VS Code were existing tools for this setup. If you do not use Homebrew or Mise, omit the corresponding activation line from the `.bashrc` block below. **Open in Code** requires `/usr/bin/code`.

## 2. Preserve existing history and back up configuration

In each currently open Bash terminal, run the following before closing it. Keep one terminal open to perform the setup; close the others afterward so an old shell cannot later save history using the old limits:

```bash
HISTSIZE=-1 HISTFILESIZE=-1
HISTTIMEFORMAT='%F %T '
shopt -s cmdhist lithist
history -a
```

In the retained terminal, create a private backup of files that already exist. The backup path is printed for later use. The preparation above also enables timestamped multiline history before entering the setup blocks below:

```bash
terminal_setup_backup="$HOME/.local/share/terminal-setup-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p -m 700 "$terminal_setup_backup"
for terminal_setup_file in   .bashrc .bash_history   .config/gnome-xdg-terminals.list .config/xdg-terminals.list   .local/share/bash/deduplicate-history.py   .local/share/actions-for-nautilus/config.json   .local/share/actions-for-nautilus/actions.py
do
  if [[ -f "$HOME/$terminal_setup_file" ]]; then
    mkdir -p "$(dirname "$terminal_setup_backup/$terminal_setup_file")"
    cp -p -- "$HOME/$terminal_setup_file" "$terminal_setup_backup/$terminal_setup_file"
  fi
done
printf 'Backup: %s\n' "$terminal_setup_backup"
unset terminal_setup_file
mkdir -p "$HOME/.local/share/bash" "$HOME/.local/share/actions-for-nautilus" "$HOME/.config"
```

Keep the existing history file. This preserves the history still available at setup time; entries already discarded by the old limits cannot be recovered. Older history without timestamps has no reliable multiline boundaries; timestamped entries preserve multiline commands going forward.

## 3. Install the history helper

Write this helper before activating the new `.bashrc`. It keeps the newest exact occurrence of each command, preserves timestamps, and replaces the history file atomically. Its caller takes the history lock.

```bash
cat > "$HOME/.local/share/bash/deduplicate-history.py" <<'HISTORY_HELPER_EOF'
#!/usr/bin/python3
"""Keep the last occurrence of each Bash history entry. Caller holds the lock."""

import os
from pathlib import Path
import re
import sys
import tempfile


def deduplicate(data):
    entries = []
    timestamp = b""
    command = []
    lines = data.split(b"\n")
    for index, part in enumerate(lines):
        if index == len(lines) - 1 and not part:
            continue
        line = part + (b"\n" if index < len(lines) - 1 else b"")
        if re.fullmatch(rb"#[0-9]+\n?", line):
            if command:
                entries.append((timestamp, b"".join(command)))
            timestamp, command = line, []
        elif timestamp:
            command.append(line)
        else:
            # Older history without timestamps stores one entry per line.
            entries.append((b"", line))
    if command:
        entries.append((timestamp, b"".join(command)))

    seen, newest = set(), []
    for stamp, text in reversed(entries):
        key = text[:-1] if text.endswith(b"\n") else text
        if key and key not in seen:
            seen.add(key)
            newest.append(stamp + key + b"\n")
    return b"".join(reversed(newest))


def main():
    path = Path(sys.argv[1]).resolve()
    if not path.exists():
        return
    original = path.read_bytes()
    result = deduplicate(original)
    if result == original:
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".bash-history-", delete=False) as output:
            temporary = output.name
            os.fchmod(output.fileno(), 0o600)
            output.write(result)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            os.unlink(temporary)


if __name__ == "__main__":
    main()
HISTORY_HELPER_EOF
```

## 4. Install the complete Bash configuration

Replace `.bashrc` with this complete final version. It retains the usual aliases, colors, completion, and window-size handling; loads ble.sh early without attaching; installs history hooks and Starship; runs fetch; activates Homebrew/Mise; sets editor and Python defaults; then attaches ble.sh.

```bash
cat > "$HOME/.bashrc" <<'BASHRC_EOF'
# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# Keep every unique interactive command, with repeats moved to the newest entry.
HISTSIZE=-1
HISTFILESIZE=-1
HISTCONTROL=erasedups
unset HISTIGNORE
HISTFILE=${HISTFILE:-"$HOME/.bash_history"}
HISTTIMEFORMAT='%F %T '
shopt -s histappend cmdhist lithist

# Load the line editor before prompt/completion setup; attach at the end.
if [[ -t 0 && -t 1 && -t 2 && ${TERM:-dumb} != dumb &&
      -r "$HOME/.local/share/blesh/ble.sh" && ! ${BLE_VERSION-} ]]; then
    source -- "$HOME/.local/share/blesh/ble.sh" --attach=none
fi

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
#[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
#force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
    # We have color support; assume it's compliant with Ecma-48
    # (ISO/IEC-6429). (Lack of such support is extremely rare, and such
    # a case would tend to support setf rather than setaf.)
    color_prompt=yes
    else
    color_prompt=
    fi
fi

if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    #alias dir='dir --color=auto'
    #alias vdir='vdir --color=auto'

    #alias grep='grep --color=auto'
    #alias fgrep='fgrep --color=auto'
    #alias egrep='egrep --color=auto'
fi

# colored GCC warnings and errors
#export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

# some more ls aliases
#alias ll='ls -l'
#alias la='ls -A'
#alias l='ls -CF'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

# Save and reload under one lock so terminals cannot overwrite each other's history.
# The helper removes saved duplicates while preserving multiline entries/timestamps.
_bash_history_sync() {
    local previous_status=$? history_lock_fd
    [[ ${HISTFILE-} && $HISTFILE != /dev/null ]] || return "$previous_status"
    exec {history_lock_fd}>"${HISTFILE}.lock" || return "$previous_status"
    if flock -x "$history_lock_fd"; then
        if history -a && history -n &&
           /usr/bin/python3 "$HOME/.local/share/bash/deduplicate-history.py" "$HISTFILE"; then
            history -c
            history -r
        fi
    fi
    exec {history_lock_fd}>&-
    return "$previous_status"
}

if [[ ${BLE_VERSION-} ]]; then
    bleopt history_limit_length=0 history_erasedups_limit=0 history_share=
    # Save before execution too, including long-running commands and exec.
    blehook PREEXEC!=_bash_history_sync
    blehook PRECMD!=_bash_history_sync
    # Replace ble.sh's unlocked exit writer with the same synchronized save.
    blehook unload-=ble/history:bash/unload.hook
    blehook unload!=_bash_history_sync
else
    # Plain Bash fallback (for terminals where ble.sh cannot attach).
    if [[ $(declare -p PROMPT_COMMAND 2>/dev/null) == 'declare -a '* ]]; then
        [[ " ${PROMPT_COMMAND[*]} " == *' _bash_history_sync '* ]] ||
            PROMPT_COMMAND=(_bash_history_sync "${PROMPT_COMMAND[@]}")
    elif [[ ${PROMPT_COMMAND-} != *'_bash_history_sync'* ]]; then
        PROMPT_COMMAND="_bash_history_sync${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
    fi
    trap _bash_history_sync EXIT
fi

if [[ ${TERM:-dumb} != dumb && ! ${_BASH_STARSHIP_INITIALIZED-} ]] &&
   command -v starship >/dev/null 2>&1; then
    eval "$(starship init bash)"
    _BASH_STARSHIP_INITIALIZED=1
fi

# Show fetch once per interactive terminal shell, before the first prompt.
# Interactive command runners (bash -ic) and redirected streams skip it.
if [[ -t 0 && -t 1 && -t 2 && ${TERM:-dumb} != dumb &&
      ! ${BASH_EXECUTION_STRING+x} && ! ${_BASH_FETCH_SHOWN-} ]] &&
   command -v fetch >/dev/null 2>&1; then
    _BASH_FETCH_SHOWN=1
    fetch --infinite
fi

# Activate Homebrew and Mise tool paths.
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"
eval "$(/home/miubomz/.local/bin/mise activate bash)"

# Default terminal editor for applications that honor EDITOR or VISUAL.
export EDITOR=/usr/bin/mcedit
export VISUAL=/usr/bin/mcedit
export FCEDIT=/usr/bin/mcedit

# Explicit versioned commands use Debian's Python, regardless of Mise/venvs.
# Functions also apply to calls inside existing shell functions and hooks.
unalias python3 pip3 2>/dev/null || :
python3() { /usr/bin/python3 "$@"; }
pip3() { /usr/bin/python3 -m pip "$@"; }

# Attach the line editor after all startup configuration is complete.
[[ ! ${BLE_VERSION-} ]] || ble-attach
BASHRC_EOF
```

Fetch runs only for an interactive shell with a real terminal. Scripts, redirected streams, `TERM=dumb`, and command runners using `bash -ic` skip it. Sourcing the configuration again does not restart fetch or initialize Starship twice.

History synchronizes under `${HISTFILE}.lock` before commands, before prompts, and on exit when ble.sh is active. Plain Bash has prompt and exit fallbacks. Exact repeats move to the newest position; whitespace or text differences make distinct commands. Commands typed into interactive shells are recorded; commands inside a script are not separate history entries.

The `python3` and `pip3` functions apply to interactive Bash, including when Mise or a virtual environment has changed `PATH`. Scripts requiring system Python should use `/usr/bin/python3` or `/usr/bin/python3 -m pip` explicitly.

## 5. Set the terminal and editor defaults

Console is first in both user terminal preference lists, with Ptyxis kept as a fallback. The GNOME-specific list takes precedence over the generic list. These desktop preferences apply to this user; the system terminal command is set separately with `update-alternatives`. Console's empty custom-shell setting uses your account's default shell, which is Bash on this machine.

```bash
printf '%s\n' org.gnome.Console.desktop org.gnome.Ptyxis.desktop:new-window   > "$HOME/.config/gnome-xdg-terminals.list"
printf '%s\n' org.gnome.Console.desktop org.gnome.Ptyxis.desktop:new-window   > "$HOME/.config/xdg-terminals.list"
gsettings set org.gnome.Console shell '[]'
sudo update-alternatives --set x-terminal-emulator /usr/bin/kgx
sudo update-alternatives --set editor /usr/bin/mcedit
```

The `.bashrc` also sets `EDITOR`, `VISUAL`, and `FCEDIT` to `/usr/bin/mcedit`. No change to the deprecated GNOME terminal-selection GSettings keys is required; desktop selection uses `xdg-terminal-exec` and the preference lists above.

## 6. Install the Nautilus helper

The helper receives selected items as URI arguments, decodes paths itself, and launches applications with argument lists. This preserves spaces, quotes, line breaks, carriage returns, and shell symbols in filenames. Only the command deliberately entered into the Execute dialog is evaluated as Bash code.

**Open in Terminal** launches Console normally in the selected folder. It uses the default Bash shell, including fetch, Starship, and ble.sh; exiting Bash closes that window.

**Execute command here** asks for a command, then uses the native `/usr/bin/blackbox-terminal` installation. Fetch is skipped for this command runner. The command is saved to history, runs once, and shows its exit status. Any single key, including Enter, closes that terminal afterward. Commands containing `exit` or `exec` still reach the final key prompt because execution happens in a subshell. Cancelling the dialog does nothing. Fast launch failures produce an error dialog.

Black Box's command is passed as `--command=VALUE`, which avoids the command-option parsing bug in the installed Debian 0.15.2 package.

```bash
cat > "$HOME/.local/share/actions-for-nautilus/actions.py" <<'NAUTILUS_HELPER_EOF'
#!/usr/bin/python3
"""Local context-menu helpers; filenames arrive as URI arguments, never shell code."""
import argparse
import html
import os
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import unquote_to_bytes, urlsplit

COMMAND_RUNNER = r'''
builtin history -s "$1"
if declare -F _bash_history_sync >/dev/null; then
    _bash_history_sync
else
    builtin history -a
fi
( builtin eval -- "$1" )
_action_status=$?
printf '\nExit status: %s.\nPress any key to close this terminal...' "$_action_status"
IFS= builtin read -r -s -n 1
printf '\n'
exit "$_action_status"
'''


def local_path(uri):
    parsed = urlsplit(uri)
    if parsed.scheme != "file" or parsed.hostname not in (None, "", "localhost"):
        raise ValueError("This action requires a local file or folder.")
    path = os.fsdecode(unquote_to_bytes(parsed.path))
    if not os.path.isabs(path) or "\0" in path:
        raise ValueError("Invalid local file URI.")
    return path


def copy_values(kind, uris):
    if kind == "copy-uri":
        return "\n".join(uris)
    paths = [local_path(uri) for uri in uris]
    if kind == "copy-name":
        return "\n".join(os.path.basename(path.rstrip(os.sep)) or os.sep for path in paths)
    return "\n".join(paths)


def copy_to_clipboards(text):
    data = os.fsencode(text)
    if os.environ.get("WAYLAND_DISPLAY"):
        commands = [
            ["/usr/bin/wl-copy", "--type", "text/plain;charset=utf-8"],
            ["/usr/bin/wl-copy", "--primary", "--type", "text/plain;charset=utf-8"],
        ]
    elif os.environ.get("DISPLAY"):
        commands = [
            ["/usr/bin/xclip", "-selection", "clipboard", "-in"],
            ["/usr/bin/xclip", "-selection", "primary", "-in"],
        ]
    else:
        raise RuntimeError("No graphical clipboard is available in this session.")
    for index, command in enumerate(commands):
        subprocess.run(command, input=data, check=(index == 0),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def selected_directory(uris):
    if len(uris) != 1:
        raise ValueError("Select one folder for this action.")
    directory = local_path(uris[0])
    if not os.path.isdir(directory):
        raise ValueError("The selected item is not a folder.")
    return directory


def terminal_command(directory):
    # org.gnome.Console.desktop uses kgx; its default shell is Bash.
    return ["/usr/bin/kgx", "--working-directory=" + directory]


def blackbox_command(directory, command):
    # Black Box expects shell code for --command; encode each Bash argument.
    shell_command = "exec " + shlex.join(["/bin/bash", "-ic", COMMAND_RUNNER, "nautilus-command", command])
    # Debian's -c/-e alias entries duplicate --command; attach its value
    # so GLib does not try to consume a separate argument twice.
    return ["/usr/bin/blackbox-terminal", "--working-directory=" + directory,
            "--command=" + shell_command]


def launch_blackbox(directory, command):
    # Report fast CLI failures while allowing the GUI to run independently.
    with tempfile.TemporaryFile() as diagnostics:
        process = subprocess.Popen(blackbox_command(directory, command), cwd=directory,
                                   stdout=subprocess.DEVNULL, stderr=diagnostics)
        try:
            status = process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            return
        if status != 0:
            diagnostics.seek(0)
            detail = diagnostics.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError("Black Box could not start (exit %s).\n%s" % (status, detail[-2000:]))


def ask_command(directory):
    result = subprocess.run(
        ["/usr/bin/zenity", "--entry", "--title=Execute command here", "--width=800",
         "--text=" + html.escape(directory) + "\nEnter a Bash command. After it finishes, press any key to close Black Box."],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    command = result.stdout.removesuffix("\n")
    return command if command.strip() else None


def perform(action, uris):
    if action.startswith("copy-"):
        copy_to_clipboards(copy_values(action, uris))
        return
    directory = selected_directory(uris)
    if action == "terminal":
        subprocess.Popen(terminal_command(directory), cwd=directory)
    elif action == "execute":
        command = ask_command(directory)
        if command is not None:
            launch_blackbox(directory, command)
    elif action == "code":
        subprocess.Popen(["/usr/bin/code", "--new-window", directory], cwd=directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("copy-name", "copy-path", "copy-uri", "terminal", "execute", "code"))
    parser.add_argument("uris", nargs="+")
    args = parser.parse_args()
    try:
        perform(args.action, args.uris)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        message = str(exc)
        print("Nautilus action failed: " + message, file=sys.stderr)
        subprocess.run(["/usr/bin/zenity", "--error", "--title=Nautilus action",
                        "--text=" + html.escape(message)], check=False)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
NAUTILUS_HELPER_EOF
```

```bash
chmod 755 "$HOME/.local/share/actions-for-nautilus/actions.py"
```

## 7. Install the Nautilus menu

This configuration uses the extension's native argument handling (`use_shell=false`, `use_v1_interpolation=false`). `%U` supplies file URIs; the Python helper performs path decoding. The absolute helper paths below are for this account.

```bash
cat > "$HOME/.local/share/actions-for-nautilus/config.json" <<'NAUTILUS_CONFIG_EOF'
{
    "actions": [
        {
            "type": "menu",
            "label": "Copy details",
            "sort": "manual",
            "actions": [
                {
                    "type": "command",
                    "label": "Copy name",
                    "command_line": "/usr/bin/python3 /home/miubomz/.local/share/actions-for-nautilus/actions.py copy-name %U",
                    "use_shell": false,
                    "use_v1_interpolation": false
                },
                {
                    "type": "command",
                    "label": "Copy path",
                    "command_line": "/usr/bin/python3 /home/miubomz/.local/share/actions-for-nautilus/actions.py copy-path %U",
                    "use_shell": false,
                    "use_v1_interpolation": false
                },
                {
                    "type": "command",
                    "label": "Copy URI",
                    "command_line": "/usr/bin/python3 /home/miubomz/.local/share/actions-for-nautilus/actions.py copy-uri %U",
                    "use_shell": false,
                    "use_v1_interpolation": false
                }
            ]
        },
        {
            "type": "command",
            "label": "Open in Terminal",
            "command_line": "/usr/bin/python3 /home/miubomz/.local/share/actions-for-nautilus/actions.py terminal %U",
            "use_shell": false,
            "use_v1_interpolation": false,
            "max_items": 1,
            "filetypes": [
                "directory"
            ]
        },
        {
            "type": "command",
            "label": "Execute command here",
            "command_line": "/usr/bin/python3 /home/miubomz/.local/share/actions-for-nautilus/actions.py execute %U",
            "use_shell": false,
            "use_v1_interpolation": false,
            "max_items": 1,
            "filetypes": [
                "directory"
            ]
        },
        {
            "type": "command",
            "label": "Open in Code",
            "command_line": "/usr/bin/python3 /home/miubomz/.local/share/actions-for-nautilus/actions.py code %U",
            "use_shell": false,
            "use_v1_interpolation": false,
            "max_items": 1,
            "filetypes": [
                "directory"
            ]
        }
    ],
    "sort": "manual",
    "debug": false
}
NAUTILUS_CONFIG_EOF
```

**Copy details** copies names, paths, or URIs for one or several selected items. Multiple values use newline separators with no extra trailing newline. `wl-copy` supplies the Wayland clipboard; `xclip` supplies X11. The helper also updates the primary/middle-click selection where supported.

The three folder actions are available for one selected local directory and on a local folder's empty background. Copy details is also available on the folder background and on multiple selected files. **Open in Code** opens a new VS Code window for the selected folder.

## 8. Check and activate

Check syntax and confirm default applications before opening a new terminal:

```bash
bash -n "$HOME/.bashrc"
/usr/bin/python3 - <<'SYNTAX_CHECK_EOF'
from pathlib import Path
import ast
import json

home = Path.home()
for relative in (
    '.local/share/bash/deduplicate-history.py',
    '.local/share/actions-for-nautilus/actions.py',
):
    path = home / relative
    ast.parse(path.read_text(), filename=str(path))
json.loads((home / '.local/share/actions-for-nautilus/config.json').read_text())
print('Python and JSON syntax OK')
SYNTAX_CHECK_EOF
xdg-terminal-exec --print-id
readlink -f /usr/bin/x-terminal-emulator
readlink /etc/alternatives/editor
```

Expected defaults are `org.gnome.Console.desktop`, `/usr/bin/kgx`, and `/usr/bin/mcedit`.

Restart Files after first creating the configuration or installing the extension. Finish any active file operations first. Existing configuration edits usually reload in about 30 seconds; helper-only changes apply on the next menu activation.

```bash
nautilus -q
nautilus "$HOME"
```

Replace the retained Bash process with one using the new configuration:

```bash
HISTSIZE=-1 HISTFILESIZE=-1
history -a
exec bash
```

Dismiss fetch, then check the shell settings:

```bash
printf 'ble.sh: %s\nStarship initialized: %s\n' "${BLE_VERSION:-not loaded}" "${_BASH_STARSHIP_INITIALIZED:-no}"
declare -p HISTSIZE HISTFILESIZE HISTCONTROL
printf 'Editor: %s\nVisual: %s\nFC editor: %s\n' "$EDITOR" "$VISUAL" "$FCEDIT"
python3 -c 'import sys; print(sys.executable)'
pip3 --version
```

Both history sizes should be `-1`, history control should be `erasedups`, and all editor variables should be `/usr/bin/mcedit`. Python should report `/usr/bin/python3`; pip should come from Debian's system Python. The system Python at the time of setup is 3.14.7.

Check newest-only history interactively:

```bash
printf '%s\n' history-demo-first
printf '%s\n' history-demo-second
printf '%s\n' history-demo-first
history 8
```

The first demo command should appear once, after the second. Open a second terminal to confirm shared history.

In Files, test the menu on a folder containing spaces or quotes in its name. **Open in Terminal** should show Console in that folder with fetch followed by the normal Bash prompt. **Execute command here** with `ls` should show output in Black Box, remain open at the key prompt, and close after one key.

The live setup was verified with an actual Console launch and an actual Black Box command launch, using isolated test history. Menu parsing, unusual filenames, newest-only history, command exit statuses, and single-key closing were also checked.

## 9. Maintenance and rollback

Edit the shell and menu with `mcedit` using the paths shown above. The history helper is required for newest-only history across terminals; keep it with the shell configuration. Keep the Nautilus helper and JSON together.

To disable the custom menu, rename its configuration and restart Files:

```bash
mv "$HOME/.local/share/actions-for-nautilus/config.json"   "$HOME/.local/share/actions-for-nautilus/config.json.disabled"
nautilus -q
nautilus "$HOME"
```

To return to the original shell behavior, repeat section 2's history flush and close other Bash terminals first. Use its private backup and substitute the printed timestamp below. Leave the current history file in place instead of replacing it with an older backup. The restored original limits can trim history again, so the commands also save a separate copy of the complete current history before rollback.

```bash
terminal_setup_backup="$HOME/.local/share/terminal-setup-backup-YYYYMMDD-HHMMSS"
HISTSIZE=-1 HISTFILESIZE=-1
history -a
cp -p -- "${HISTFILE:-$HOME/.bash_history}" "$terminal_setup_backup/.bash_history.before-rollback"
cp -p -- "$terminal_setup_backup/.bashrc" "$HOME/.bashrc"
sudo update-alternatives --set editor /bin/nano
printf '%s\n' org.gnome.Ptyxis.desktop:new-window > "$HOME/.config/gnome-xdg-terminals.list"
printf '%s\n' org.gnome.Ptyxis.desktop:new-window > "$HOME/.config/xdg-terminals.list"
sudo update-alternatives --set x-terminal-emulator /usr/bin/ptyxis
exec bash
```

Restoring the original `.bashrc` also restores its old history limits and its original Starship/ble.sh initialization. To restore a previous menu or custom terminal preference instead, copy that specific file from the same backup if it exists.
```
```

I also installed org.gnome.Epiphany package from software not flatpak.

also installed io.mpv.Mpv package from software not flatpak.

also installed copyq package from software not flatpak. configure from defaults, toggle on autostart,

installed some flatpak stuff:
`flatpak install flathub org.gnome.meld it.mijorus.gearlever io.github.flattool.Warehouse com.raggesilver.BlackBox org.gnome.Boxes org.gnome.Snapshot it.mijorus.smile com.mattjakeman.ExtensionManager org.libreoffice.LibreOffice org.gnome.seahorse.Application org.remmina.Remmina org.gnome.SoundRecorder org.nickvision.tubeconverter org.qbittorrent.qBittorrent org.gnome.Evince org.nomacs.ImageLounge io.github.Qalculate -y`

then I configure gnome text editor from defaults, toggle on display line number, toggle on highlight current line, toggle display overview map, toggle off check spelling, toggle on show right margin, toggle off restore session.

then I install the following:
```
sudo apt install fonts-* --no-install-recommends --no-install-suggests -y
```

then I install pgAdmin4 flatpak

then install qview appimage from https://github.com/jurplel/qView/releases/latest with gearlever move to menu and fuse with
```
sudo add-apt-repository universe
sudo apt install libfuse3-dev libfuse3-4
```
but qview needs fuse2 at the time of installing this, so had to do some fixing like the following:
"""
# Fix qView AppImage FUSE errors on Debian Forky

Applies to Debian Forky on **amd64/x86_64**, with qView added to the application menu through Gear Lever.

## Cause

qView's AppImage requires **FUSE 2** (`libfuse.so.2`). Installing `libfuse3-4` or `libfuse3-dev` does not provide it. Forky's repositories currently lack `libfuse2t64`, so `apt install libfuse2t64` cannot find it. `universe` is an Ubuntu repository and does not apply to Debian.

## Fix

Install Debian Trixie's official FUSE 2 compatibility library. The commands below download it, verify Debian's SHA256 checksum, and install only that package. No additional repository is needed; FUSE 3 can remain installed.

Run in Bash:

```bash
(
  set -e
  qview_fuse_dir=$(mktemp -d)
  qview_fuse_deb="$qview_fuse_dir/libfuse2t64_2.9.9-9_amd64.deb"
  curl -fL -o "$qview_fuse_deb" \
    https://deb.debian.org/debian/pool/main/f/fuse/libfuse2t64_2.9.9-9_amd64.deb
  printf '%s  %s\n' \
    e60474070e983693ac461af291b876c2304340f75a6b8379a3ba017e4848341e \
    "$qview_fuse_deb" | sha256sum --check -
  sudo apt install "$qview_fuse_deb"
)
```

## Verify and launch

```bash
"$HOME/AppImages/qview.appimage" --version
gio launch "$HOME/.local/share/applications/qview.desktop"
```

The version command should print `qView 7.1` for the current release. The second command uses Gear Lever's existing menu entry. No reboot or reimport is required.

**Verified on 4 October 2026:** `libfuse2t64` version `2.9.9-9` installed successfully, qView reported `7.1`, and the menu launcher started its process without a FUSE error.

## Fallback without installing FUSE 2

```bash
"$HOME/AppImages/qview.appimage" --appimage-extract-and-run
```

This extracts the application on each launch, so startup can take longer.
"""

then I install mpv with uosc with the following command:
```
sudo apt install mpv -y
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/tomasklaen/uosc/HEAD/installers/unix.sh)"
mkdir -p ~/.config/mpv && tee ~/.config/mpv/mpv.conf <<EOF
keep-open=always
idle=yes
force-window=yes
EOF
```

then I encountered some issue with mpv not opening, so I had to fix it like the following:
"""
# mpv + uosc: immediate-close fix

Verified on Debian GNOME/Wayland, 4 October 2026: mpv 0.41.0 and uosc 5.13.0.

## Cause

This VM uses Mesa's **llvmpipe software renderer**. mpv rejects it by default, then crashes while trying another graphics backend:

```text
Found no suitable device, giving up.
Failed initializing vulkan device
vo_x11_init: Assertion `!vo->x11' failed.
```

The original `idle`, `force-window`, and `keep-open` settings were valid. uosc was installed correctly. **Adding `gpu-sw=yes` fixes the crash** by allowing software rendering.

## Install and configure

mpv and uosc are already installed on this machine. For a fresh installation or uosc update:

```bash
sudo apt install -y mpv curl unzip
MPV_CONFIG_DIR="$HOME/.config/mpv" /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/tomasklaen/uosc/HEAD/installers/unix.sh)"
```

Use this complete configuration. This replaces `mpv.conf`; the original configuration on this machine was backed up as `~/.config/mpv/mpv.conf.before-uosc-fix`.

```bash
mkdir -p ~/.config/mpv
cat > ~/.config/mpv/mpv.conf <<'EOF'
keep-open=always
idle=yes
force-window=yes

# Allow the VM's software renderer.
gpu-sw=yes

# Use uosc controls and seek/volume indicators.
osc=no
osd-bar=no
EOF
```

`idle=yes` keeps mpv running without a file; `force-window=yes` shows its window. `keep-open=always` pauses at the end of every playlist item; use `keep-open=yes` if playlists should advance normally. Software rendering uses CPU resources and can struggle with high-resolution video.

## Verify

```bash
mpv
```

The window should stay open. Drop a video into it; move the pointer near the bottom for uosc controls, or right-click for its menu.

Verified: terminal and desktop launch modes, uosc bindings, 640×360 video playback, and staying open at EOF. No startup or playback errors occurred.

If another issue appears, launch from a terminal to see the error:

```bash
mpv --log-file=/tmp/mpv.log
```

## Undo

Restore the original configuration with this self-contained command. It removes the fix, so the crash can return on this VM:

```bash
cat > ~/.config/mpv/mpv.conf <<'EOF'
keep-open=always
idle=yes
force-window=yes
EOF
```
"""

then I did
`sudo apt install timeshift git -y`

then configure timeshift snapshot to do 7 weekly, 8 daily, and 2 boot, and not include @home subvolume in backups, plus the following steps for storing from grub:
"""
# GRUB snapshots with Timeshift on Debian

Configured on 4 October 2026, Debian forky/sid. **Manual and scheduled Timeshift snapshots now appear automatically under “Timeshift snapshots” in GRUB.** The daemon is enabled at boot; the GRUB menu stays visible for five seconds.

## Why improve the original commands?

Installing from source is appropriate here because the configured Debian repository has no `grub-btrfs` package. The original commands omit dependency checks and leave the daemon watching `/.snapshots`. Timeshift needs `--timeshift-auto`. This setup also pins release `v4.14`, uses a systemd override, refreshes GRUB when the service starts, and protects snapshot previews with Debian’s `overlayroot` package.

## Requirements and Timeshift settings

This machine already has the required layout:

- `/` is Btrfs subvolume `@`; `/home` is separate subvolume `@home`.
- Both use `/dev/vda2`, UUID `603a47d0-6f26-4fbd-be0c-4ef0f7cfee6c`; Btrfs default subvolume is `5`.
- `/boot` is inside `@`; the EFI partition is `/dev/vda1`, mounted at `/boot/efi`.
- Timeshift uses **BTRFS** mode. Home snapshots/restoration are excluded.
- Existing schedules are preserved: daily (keep 8), weekly (keep 7), boot (keep 2).

To configure another installation, open Timeshift → Settings, select BTRFS, select its root Btrfs device, choose those schedules, and exclude home. These instructions require `@`/`@home`, GRUB, systemd, and Debian’s `initramfs-tools`; do not reformat an incompatible installation to follow them.

```bash
findmnt -no SOURCE,FSTYPE /
findmnt -no SOURCE,FSTYPE /home
sudo btrfs subvolume get-default /
sudo timeshift --list
```

## Installation

Already completed here. For a fresh compatible installation, run each block in order and stop if a command fails. This installation’s originals are in `/var/backups/grub-btrfs-20261004`. On another installation, back up its boot files and settings first:

```bash
task_backup_dir="/var/backups/grub-btrfs-$(date +%Y%m%d-%H%M%S)"
sudo mkdir -m 0700 "$task_backup_dir"
sudo cp -a --parents --reflink=auto /boot/grub /boot/initrd.img-* \
    /etc/default/grub /etc/timeshift/timeshift.json "$task_backup_dir/"
```

```bash
sudo apt update
sudo apt install -y timeshift git make btrfs-progs inotify-tools overlayroot
mkdir -p ~/Documents/Git
cd ~/Documents/Git
if [ ! -d grub-btrfs ]; then
    git clone --depth 1 --branch v4.14 https://github.com/Antynea/grub-btrfs.git
fi
cd grub-btrfs
git fetch --depth 1 origin tag v4.14
git checkout --detach v4.14
test "$(git rev-parse HEAD)" = 2fcfbe967637166b88dadd49c834807243a941bf
git diff --quiet HEAD -- Makefile 41_snapshots-btrfs grub-btrfsd \
    grub-btrfsd.service config manpages initramfs README.md LICENSE
```

After both the commit and unchanged-source checks succeed:

```bash
sudo make GRUB_UPDATE_EXCLUDE=true install
sudo tee -a /etc/default/grub-btrfs/config >/dev/null <<'CONFIG'
GRUB_BTRFS_SUBMENUNAME="Timeshift snapshots"
GRUB_BTRFS_SNAPSHOT_KERNEL_PARAMETERS="overlayroot=tmpfs:recurse=0"
GRUB_BTRFS_MKCONFIG=/usr/sbin/grub-mkconfig
CONFIG
```

Keep `overlayroot=""` in `/etc/overlayroot.conf` and do not enable it in `/etc/overlayroot.local.conf`. The kernel parameter above enables the overlay only for snapshot entries. Rebuild all installed kernels’ initramfs **before creating snapshots**:

```bash
sudo update-initramfs -u -k all
sudo tee /etc/default/grub.d/99-timeshift-snapshots.cfg >/dev/null <<'GRUB'
GRUB_TIMEOUT_STYLE=menu
GRUB_TIMEOUT=5
GRUB
```

## Automatically add manual and scheduled snapshots

The following override makes `grub-btrfsd` detect Timeshift’s changing `/run/timeshift/<PID>/backup` path. It watches snapshot creation/deletion for both the GUI and CLI, including scheduled runs. `ExecStartPre` refreshes the menu at service startup; `Restart` recovers from daemon failures.

```bash
sudo mkdir -p /etc/systemd/system/grub-btrfsd.service.d
sudo tee /etc/systemd/system/grub-btrfsd.service.d/override.conf >/dev/null <<'UNIT'
[Service]
ExecStartPre=/usr/sbin/update-grub
ExecStart=
ExecStart=/usr/bin/grub-btrfsd --syslog --timeshift-auto
Restart=on-failure
RestartSec=5
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now grub-btrfsd.service
sudo systemctl enable --now cron.service
```

Timeshift creates the snapshots; the daemon adds them to GRUB. Timeshift’s existing cron jobs run `timeshift --check --scripted` hourly and create a boot snapshot ten minutes after boot. The hourly check creates snapshots only when an enabled schedule is due, so hourly snapshots remain disabled. No extra snapshot cron job is needed.

## Verify and use

Create a manual snapshot, then allow a few seconds for automatic menu generation:

```bash
sudo timeshift --create --comments 'grub-btrfs recovery setup' --tags O --scripted
sudo timeshift --check --scripted
systemctl is-enabled grub-btrfsd.service
systemctl is-active grub-btrfsd.service
sudo timeshift --list
sudo grub-script-check /boot/grub/grub.cfg
sudo grub-script-check /boot/grub/grub-btrfs.cfg
sudo grep -E '^submenu|overlayroot=' /boot/grub/grub-btrfs.cfg
```

Expect `enabled`, `active`, snapshot entries with `overlayroot=tmpfs:recurse=0`, and no syntax errors. A scheduled check can reuse/tag a recent snapshot instead of creating another; that is normal.

Verified here without manually updating GRUB after snapshot creation:

- `2026-10-04_21-16-20`: manual recovery snapshot; the scheduled check added boot/daily/weekly tags.
- `2026-10-04_21-17-18`: separate snapshot created using the boot job’s `--create --scripted --tags B` command; automatically added to GRUB.
- Both installed kernels contain the overlay hook/module; both GRUB configuration files pass syntax checks. Actual reboot/snapshot boot has not been tested.

At your next reboot, choose **Timeshift snapshots → snapshot → kernel**; prefer `7.2.8+deb14-amd64` for these snapshots. A snapshot boot is a preview, not a permanent restoration: root filesystem writes go to RAM and disappear on reboot. **`/home`, EFI, and other separately mounted filesystems remain writable, and their changes persist.** Normal boot uses the usual writable root. Snapshots made before the overlay initramfs was installed do not gain this protection automatically.

For a permanent rollback, open Timeshift from a normal boot, select a snapshot, and choose Restore. If normal boot fails, boot a Debian live USB in UEFI mode, install/open Timeshift, choose BTRFS and `/dev/vda2`, and restore the snapshot. Keep home restoration excluded; use `/dev/vda1` for `/boot/efi` when prompted, then reboot. Use normal/live media for Timeshift restoration rather than the overlay preview. These snapshots share the system disk and do not replace an external backup.

## Troubleshooting and maintenance

If entries are missing, check the service log and regenerate the menu:

```bash
sudo journalctl -u grub-btrfsd.service -n 40 --no-pager
sudo systemctl restart grub-btrfsd.service
sudo update-grub
```

Ensure Timeshift still uses BTRFS and `grub-btrfsd` is active. Debian package updates maintain `overlayroot`; the source installation of `grub-btrfs` requires manual updates. When installing a reviewed newer release, save `/etc/default/grub-btrfs/config`, repeat the source installation, restore that configuration, then run `systemctl daemon-reload` and restart the service. Keep the Timeshift override.

## Remove this integration

From a normal boot, remove the integration and rebuild the boot files. Timeshift snapshots and schedules remain available.

```bash
sudo systemctl disable --now grub-btrfsd.service
sudo rm -f /etc/systemd/system/grub-btrfsd.service.d/override.conf \
    /etc/default/grub.d/99-timeshift-snapshots.cfg \
    /etc/grub.d/41_snapshots-btrfs /etc/default/grub-btrfs/config \
    /usr/bin/grub-btrfsd /usr/lib/systemd/system/grub-btrfsd.service \
    /boot/grub/grub-btrfs.cfg /boot/grub/grub-btrfs.cfg.bkp \
    /usr/share/man/man8/grub-btrfs.8 /usr/share/man/man8/grub-btrfsd.8
sudo rm -r /usr/share/doc/grub-btrfs /usr/share/licenses/grub-btrfs
sudo systemctl daemon-reload
sudo apt purge overlayroot
sudo update-initramfs -u -k all
sudo update-grub
```
"""

then I install easyvenv with `curl -fsSL https://raw.githubusercontent.com/RisPNG/easyvenv/main/install.sh | sh`

then I open font manager, configure preferences from defaults, toggle on use adwaita stylesheet, and change default view to manage from browse.

in console, I run `mc`, then configure from options>appearance, and change skin to yadt256-defbg. I do the same for `sudo mc` as well

then I go to settings again to configure keyboard shortcuts, from default:

in launchers
I disabled Launch help browser
I enable launch web browser with Super+B

then I set up some custom shortcut with
"""
# GNOME keyboard shortcuts

Configured for `miubomz` on Debian Forky/Sid, GNOME 50 / Wayland, 4 October 2026. All helper code and setup commands are included below.

| Shortcut | Result | Custom shortcut command on this account |
|---|---|---|
| Super+E | Append a Home tab to Nautilus; create a window if none exists | `/home/miubomz/.local/bin/gnome-shortcut-helper files` |
| Super+T | New tab in the default terminal; create a window if none exists | `/home/miubomz/.local/bin/gnome-shortcut-helper terminal` |
| Super+. | Open Smile | `/usr/bin/flatpak run it.mijorus.smile` |
| Super+- | All detected DDC/CI monitors: minimum brightness | `/home/miubomz/.local/bin/gnome-shortcut-helper brightness 0` |
| Super+= | All detected DDC/CI monitors: maximum brightness | `/home/miubomz/.local/bin/gnome-shortcut-helper brightness 100` |
| Ctrl+Shift+Esc | Open GNOME System Monitor | `/usr/bin/gnome-system-monitor` |

Use **Settings → Keyboard → View and Customize Shortcuts → Custom Shortcuts**. The built-in **Launchers → Home folder** binding cannot request a new tab, so Super+E is released there. IBus also used Super+.; setup releases that binding while preserving Super+; for its emoji picker. The equals shortcut does not require Shift.

The terminal helper resolves the current default with `xdg-terminal-exec` and invokes its **New Tab** action. Your default is GNOME Console: it uses its most recently active window and inherits the current tab's directory. A future default must offer that action. Nautilus uses its newest created window if several are open; its exported window actions are private and may need adjustment after an upgrade.

Brightness changes only VCP `0x10`. The sample's other registers change contrast and RGB calibration. Each invocation redetects monitors, uses each reported maximum, processes up to four monitors concurrently, verifies writes, and queues overlapping invocations. **0% is the monitor's minimum and may remain visible; 100% is maximum brightness.**

**Current limitation:** this machine is a KVM guest exposing a QEMU virtual display. `ddcutil detect --brief` finds no DDC/CI monitors. Both brightness shortcuts are installed, but physical brightness cannot work or be tested until the commands run on a physical host with accessible monitors or real display hardware is exposed to the guest. Errors produce a desktop notification.

## Setup

Everything required is already installed here. When rebuilding this setup, install the dependencies and Smile if missing:

```bash
sudo apt install python3 python3-gi gir1.2-glib-2.0 gir1.2-gtk-4.0 nautilus gnome-console xdg-terminal-exec ddcutil gnome-system-monitor flatpak
flatpak remote-add --system --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak info it.mijorus.smile >/dev/null 2>&1 || flatpak install --system flathub it.mijorus.smile
mkdir -p "$HOME/.local/bin" "$HOME/.local/share"
```

Save this complete helper:

```bash
cat > "$HOME/.local/bin/gnome-shortcut-helper" <<'SHORTCUT_HELPER_EOF'
#!/usr/bin/python3
"""GNOME: Home/terminal tabs and DDC/CI brightness endpoints."""
import concurrent.futures
import contextlib
import fcntl
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import gi
gi.require_version("GioUnix", "2.0")
from gi.repository import Gio, GioUnix, GLib


def call(destination, path, interface, method, parameters=None):
    return Gio.bus_get_sync(Gio.BusType.SESSION, None).call_sync(
        destination, path, interface, method, parameters, None,
        Gio.DBusCallFlags.NONE, 5000, None)


@contextlib.contextmanager
def locked(name):
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    with (runtime / f"gnome-shortcut-{name}.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def windows():
    return call("org.gnome.Nautilus", "/org/freedesktop/FileManager1",
                "org.freedesktop.DBus.Properties", "Get",
                GLib.Variant("(ss)", ("org.freedesktop.FileManager1",
                                      "OpenWindowsWithLocations"))).unpack()[0]


def files():
    with locked("files"):
        opened = windows()
        if not opened:
            subprocess.Popen(["/usr/bin/nautilus", str(Path.home())])
            deadline = time.monotonic() + 5
            while not windows() and time.monotonic() < deadline:
                time.sleep(0.1)
            if not windows():
                raise RuntimeError("Nautilus did not open a window.")
            return
        window = next(iter(opened))
        count = len(opened[window])
        platform = {key: GLib.Variant("s", os.environ[env]) for key, env in (
            ("activation-token", "XDG_ACTIVATION_TOKEN"),
            ("desktop-startup-id", "DESKTOP_STARTUP_ID")) if env in os.environ}

        def activate(action):
            call("org.gnome.Nautilus", window, "org.gtk.Actions", "Activate",
                 GLib.Variant("(sava{sv})", (action, [], platform)))

        activate("new-tab")
        deadline = time.monotonic() + 3
        while len(windows().get(window, [])) <= count:
            if time.monotonic() >= deadline:
                raise RuntimeError("Nautilus did not create a tab; retry after loading.")
            time.sleep(0.1)
        activate("go-home")
        for _ in range(count):
            activate("tab-move-right")


def terminal():
    desktop = subprocess.check_output(
        ["/usr/bin/xdg-terminal-exec", "--print-id"], text=True, timeout=10
    ).strip().split(":", 1)[0]
    app = GioUnix.DesktopAppInfo.new(desktop)
    if not app or "new-tab" not in app.list_actions():
        raise RuntimeError(f"Default terminal {desktop} has no New Tab action.")
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gtk, Gdk
    Gtk.init()
    context = Gdk.Display.get_default().get_app_launch_context()
    if app.get_boolean("DBusActivatable"):
        platform = {key: GLib.Variant("s", os.environ[env]) for key, env in (
            ("activation-token", "XDG_ACTIVATION_TOKEN"),
            ("desktop-startup-id", "DESKTOP_STARTUP_ID")) if env in os.environ}
        if not platform and app.get_boolean("StartupNotify"):
            token = context.get_startup_notify_id(app, [])
            if token:
                platform = {key: GLib.Variant("s", token) for key in
                            ("activation-token", "desktop-startup-id")}
        name = Path(app.get_filename()).name.removesuffix(".desktop")
        path = "/" + name.replace(".", "/").replace("-", "_")
        call(name, path, "org.freedesktop.Application", "ActivateAction",
             GLib.Variant("(sava{sv})", ("new-tab", [], platform)))
    else:
        app.launch_action("new-tab", context)


def ddc(*args):
    result = subprocess.run(["/usr/bin/ddcutil", *args], text=True,
                            capture_output=True, timeout=30,
                            env={**os.environ, "LC_ALL": "C"})
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip()[-600:])
    return result.stdout


def brightness(percent):
    with locked("brightness"):
        report = ddc("detect", "--brief")
        displays = re.findall(r"^Display\s+(\d+)\s*\n(.*?)(?=^\S|\Z)",
                              report, re.M | re.S)
        selectors = []
        for number, details in displays:
            bus = re.search(r"I2C bus:\s*/dev/i2c-(\d+)", details)
            selector = ("--bus", bus[1]) if bus else ("--display", number)
            if selector not in selectors:
                selectors.append(selector)
        if not selectors:
            raise RuntimeError("No DDC/CI displays found. Enable DDC/CI on physical monitors.")

        def adjust(selector):
            try:
                value = ddc(*selector, "getvcp", "10", "--terse")
                match = re.search(r"^VCP 10 C (\d+) (\d+)\s*$", value, re.M)
                if not match or not 0 < int(match[2]) <= 65535:
                    raise RuntimeError("Monitor did not report a valid brightness range.")
                raw = (int(match[2]) * percent + 50) // 100
                ddc(*selector, "setvcp", "10", str(raw), "--verify")
                return None
            except Exception as error:
                return f"{' '.join(selector)}: {error}"

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            failures = [error for error in pool.map(adjust, selectors) if error]
        if failures:
            raise RuntimeError("\n".join(failures))


def main():
    action = sys.argv[1:]
    if action == ["files"]:
        files()
    elif action == ["terminal"]:
        terminal()
    elif action in (["brightness", "0"], ["brightness", "100"]):
        brightness(int(action[1]))
    else:
        raise RuntimeError("Usage: gnome-shortcut-helper files|terminal|brightness 0|brightness 100")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        message = str(error)
        print(message, file=sys.stderr)
        try:
            call("org.freedesktop.Notifications", "/org/freedesktop/Notifications",
                 "org.freedesktop.Notifications", "Notify",
                 GLib.Variant("(susssasa{sv}i)",
                              ("GNOME shortcuts", 0, "dialog-warning",
                               "Shortcut failed", message[:1800], [], {}, -1)))
        except Exception:
            pass
        sys.exit(1)
SHORTCUT_HELPER_EOF
chmod 755 "$HOME/.local/bin/gnome-shortcut-helper"
```

Run this block as your normal desktop user. It backs up the affected settings, preserves other custom shortcuts, and installs or updates these six entries. It takes effect immediately:

```bash
/usr/bin/python3 - <<'SHORTCUT_SETUP_EOF'
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import shlex
from gi.repository import Gio

media_id = "org.gnome.settings-daemon.plugins.media-keys"
custom_id = media_id + ".custom-keybinding"
base = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/"
helper = shlex.quote(str(Path.home() / ".local/bin/gnome-shortcut-helper"))
rows = [
    ("home-tab", "Home folder — new tab", helper + " files", "<Super>e"),
    ("terminal-tab", "Default terminal — new tab", helper + " terminal", "<Super>t"),
    ("smile", "Smile", "/usr/bin/flatpak run it.mijorus.smile", "<Super>period"),
    ("brightness-min", "All monitors — brightness 0%", helper + " brightness 0", "<Super>minus"),
    ("brightness-max", "All monitors — brightness 100%", helper + " brightness 100", "<Super>equal"),
    ("system-monitor", "System Monitor", "/usr/bin/gnome-system-monitor", "<Control><Shift>Escape"),
]
media = Gio.Settings.new(media_id)
emoji = Gio.Settings.new("org.freedesktop.ibus.panel.emoji")
changes = [(media, "home", [s for s in media.get_strv("home") if s != "<Super>e"]),
           (emoji, "hotkey", [s for s in emoji.get_strv("hotkey") if s != "<Super>period"])]
paths = list(media.get_strv("custom-keybindings"))
for suffix, name, command, binding in rows:
    path = base + "desktop-" + suffix + "/"
    setting = Gio.Settings.new_with_path(custom_id, path)
    changes += [(setting, "name", name), (setting, "command", command), (setting, "binding", binding)]
    if path not in paths:
        paths.append(path)
changes.append((media, "custom-keybindings", paths))
saved = []
for setting, key, value in changes:
    old = setting.get_user_value(key)
    saved.append([setting.props.schema_id, setting.props.path, key,
                  old.print_(True) if old is not None else None])
backup = Path.home() / ".local/share" / ("gnome-shortcuts-backup-" +
    datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).strftime("%Y%m%d-%H%M%S") + ".json")
backup.write_text(json.dumps(saved, indent=2) + "\n")
backup.chmod(0o600)
for setting, key, value in changes:
    success = setting.set_strv(key, value) if isinstance(value, list) else setting.set_string(key, value)
    if not success:
        raise RuntimeError(f"Cannot write {setting.props.schema_id} {key}")
Gio.Settings.sync()
print("Configured all six shortcuts. Settings backup:", backup)
SHORTCUT_SETUP_EOF
```

For manual setup, run the helper-saving block, disable the built-in Home folder binding, and create the six custom shortcuts using the table's commands. Release the conflicting IBus binding with:

```bash
gsettings set org.freedesktop.ibus.panel.emoji hotkey "['<Super>semicolon']"
```

## Check and undo

Press Super+E and Super+T twice: each application should have one window with two tabs if initially closed. Appending a Nautilus tab from an earlier selected tab was verified at the right end; Console's cold launch and repeated new tabs were verified. Smile and System Monitor were launch-tested. Monitor handling passed simulated 100/255 maximum ranges, invalid/duplicate buses, and partial failures; physical brightness remains unverified for the reason above.

For physical monitors, enable **DDC/CI** in their on-screen menus and check:

```bash
ddcutil detect --brief
ddcutil --display 1 getvcp 10 --terse
```

If real video I2C adapters exist but access is denied, the Debian package normally grants desktop access through udev. A fallback is `sudo usermod -aG i2c "$USER"`, then log out and back in. This does not make a virtual display support DDC/CI.

To undo this session's settings, run the complete restore block below. Substitute the backup path printed by setup when using another run's backup. The helper can remain unused:

```bash
/usr/bin/python3 - "$HOME/.local/share/gnome-shortcuts-backup-20261004-215657.json" <<'SHORTCUT_RESTORE_EOF'
import json
from pathlib import Path
import sys
from gi.repository import Gio, GLib
for schema, path, key, original in json.loads(Path(sys.argv[1]).read_text()):
    settings = Gio.Settings.new_with_path(schema, path)
    if original is None:
        settings.reset(key)
    else:
        settings.set_value(key, GLib.Variant.parse(None, original, None, None))
Gio.Settings.sync()
SHORTCUT_RESTORE_EOF
```
"""

then I restart, once I logged into the desktop, I created the final snapshot.

so basically all the packages, flatpak apps, and appimages that are on that final "Desired Results" snapshot, along with all the settings for apps and gnome, etc. are all intended. the only thing I don't want there for the liveos install is chatgpt, because I have it there just for my own to make it my desired results.

vm is still running.
