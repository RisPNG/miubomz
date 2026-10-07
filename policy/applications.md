# Applications and sources

Miubomz provides an immediately usable desktop for browsing, documents, media, downloads, communication, file management and development. The selected Debian applications, Vivaldi and Visual Studio Code, Flathub applications, qView AppImage and supporting tools follow the clean setup reference. ChatGPT and personal reference-machine data are excluded.

Applications come from the distribution or their official vendor and project channels. Debian packages use Debian's archive; vendor applications retain their vendor repositories; Flatpaks use Flathub. A supplied application must remain manageable through its normal package manager after installation.

Vivaldi is the initial browser. Firefox has its clean themed profile. qView integrates with Gear Lever, while mpv receives its selected scripts, fonts and preferences. Supplied application profiles must contain clean defaults without browsing history, credentials or machine-specific paths.

Miubian's native live-build package lists express Debian application selection. `variants/miubian/inputs/software.json` selects non-APT assets, Flatpak references and extensions. The locks resolve these selections to exact shipped bytes and versions. `integration/defaults/applications/` owns maintained application preferences. The historical reference inventory documents provenance and parity; it does not decide future application selection.
