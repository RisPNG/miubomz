# Calamares

The installer uses Debian Calamares `3.4.2-1.1+miubomz1`, built with Debian's
native source-package workflow. The single quilt patch restricts the legacy
BIOS root or `/boot` flag to non-GPT tables. On GPT, KPMcore interprets that
flag as an EFI partition type; the stock automatic hybrid layout otherwise
marks the Linux root as a second EFI partition. The existing partition flow
and dedicated EFI/BIOS boot partitions remain intact.

`build.sh OUTPUT_DIRECTORY` runs inside the Debian builder. It verifies the
three upstream Debian source files against `sources.sha256`, installs native
build dependencies there, and builds the binary and patched Debian source.
The cache retains the source, recipe identity, binary and its SHA256; unchanged
recipes reuse that verified binary. No host packages are installed.

Upstream sources come from
[`deb.debian.org/debian/pool/main/c/calamares/`](https://deb.debian.org/debian/pool/main/c/calamares/).
