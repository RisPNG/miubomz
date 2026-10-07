# Development environment

The supplied shell combines Bash, ble.sh, Starship, the selected aliases and file-management utilities. Git receives the clean configuration from the setup reference. New accounts receive these seeds without importing personal shell history or Git identity.

Mise manages the supplied language toolchains. Python environments use easyvenv through its `venv` command; Rust also retains its native rustup environment. Homebrew and Pacstall remain available through their ordinary tools. The installed toolchains and supporting binaries must work without downloading replacements during installation or first login.

The software lock records the exact toolchains shipped in an image. User configuration can continue to select `latest` for future development work; that selection does not change the frozen image inputs. A requested Python version may require Mise's upstream refresh. A supplied version can be selected offline with its native offline mode, for example `MISE_OFFLINE=1 venv create project 3.11 --yes`.

Miubian owns shell and development configuration under `variants/miubian/integration/defaults/` and account initialization under `integration/helpers/`. Toolchain binaries and caches needed for offline use are explicit software inputs. Account initialization assigns paths and ownership for the account chosen during installation rather than preserving the reference username.
