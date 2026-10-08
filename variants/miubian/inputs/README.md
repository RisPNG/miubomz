# Miubian inputs

The native `live-build/config/package-lists/` files select Debian packages by role. `05-exported-inputs.list.chroot` explicitly selects the preserved vendor and unavailable package archives supplied with this release. `locks/apt.json` records the reviewed resolved package closure, including the separate offline installer-media closure. Native integration and patched Calamares packages are rebuilt from source and recorded separately in each image's inputs manifest.

`software.json` selects the upstream software assets, Flatpak applications and runtimes, GNOME extensions, development toolchains and Homebrew payload. Its bundle field declares an immutable local archive with an exact SHA-256 and size. `locks/software.json` records exact Flatpak commits, including locale dependencies, and verifies the complete supplied software tree's content, paths and permission modes. Preparation checks native software inventories against the selections and locks, then stages only the declared asset paths. The package-owned Mise and Rustup configuration files and root's Midnight Commander tree are excluded; their maintained sources live in `integration/defaults/`.

The [setup specification](../documentation/setup.md) describes the intended Miubian setup. Its accompanying [package inventory](../documentation/specifications/desired-packages.json) and [software inventory](../documentation/specifications/software-lock.json) record the original Desired Results workstation. The native package lists and files in this directory provide current build selection and locks. Cached manifests and completion markers are not authorities: each preparation verifies cached input bytes against the tracked locks.

## Building from an empty cache

Provide the bundle named in `software.json` alongside the source, then run `mise run build`. `MIUBOMZ_INPUT_BUNDLE` may point to the same verified archive at another location. The bundle contains `software/`, `apt/` and its canonical inventory in `manifest.json`; preparation extracts and verifies it before staging native live-build inputs. The first release's exported upstream payload is supplied as an archived input, rather than reconstructed from unpinned downloads. A reference VM is not required. Debian bootstrap and the native builder's dependency installation still use the official network archive; offline support applies to the resulting desktop and installer.

## Resolving changed Debian selections

Normal builds reject native recipe changes until their lock has been resolved and reviewed. To obtain a candidate, edit the native package lists and run:

```sh
MIUBOMZ_RESOLVE_INPUTS=1 mise run build
```

This runs the same native build pipeline with unversioned Debian selections. It stages only the explicitly selected exported archives and newly built local packages; it does not reinstall or pin the historical dependency closure. The software lock remains enforced. Native APT and live-build resolve the remaining packages and installer-media dependencies. The export step emits `.apt-lock.candidate.json` and `.inputs.candidate.json` without publishing the ISO as a release.

Review the candidate's package additions, removals, versions, hashes and media closure. Replace `locks/apt.json` with the reviewed candidate, then export the verified canonical cache:

```sh
mise run export-inputs .cache/miubian artifacts/miubian/inputs
```

The exporter verifies the reviewed locks, produces a content-addressed archive and checksum, and registers its path, SHA-256 and size in `software.json`. Run an ordinary `mise run build` afterward to enforce the reviewed closure and validate the release. Resolution candidates are diagnostic artifacts, not automatically accepted source locks.

Changing exported software requires a separately prepared and reviewed upstream payload and software lock before exporting a replacement bundle. The APT resolution mode does not resolve Flatpak, toolchain or artwork changes and cannot bypass their lock. Keep the source, declared bundle and released source-package artifacts together when distributing build inputs.
