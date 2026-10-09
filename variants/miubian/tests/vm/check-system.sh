#!/bin/bash
set -euo pipefail

test "$(. /etc/os-release; printf '%s' "$ID")" = debian
for package in miubomz-defaults miubomz-recovery; do
    test "$(dpkg-query -W -f='${Version}' "$package")" = "$MIUBOMZ_QA_VERSION"
    test "$(dpkg-query -W -f='${Status}' "$package")" = 'install ok installed'
done
for package in miubomz-desktop miubomz-software chatgpt; do
    if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -qx 'install ok installed'; then
        printf 'Unexpected installed package: %s\n' "$package" >&2
        exit 1
    fi
done
test ! -e /usr/share/applications/chatgpt.desktop
test -x /usr/lib/miubomz/initialize-user
test -s /usr/share/miubomz/skel/.bashrc
test -s /usr/lib/x86_64-linux-gnu/nautilus/extensions-4/libmiubomz-nautilus-tabs.so
test -s /etc/xdg/miu/nautilus-tabs.conf
test "$(readlink -f /usr/bin/x-terminal-emulator)" = /usr/bin/xdg-terminal-exec
test "$(readlink /etc/alternatives/x-www-browser)" = /usr/bin/vivaldi-stable
test "$(readlink /etc/alternatives/gnome-www-browser)" = /usr/bin/vivaldi-stable
test "$(dpkg-query -S /etc/skel/.bashrc | cut -d: -f1)" = bash
test "$(dpkg-query -S /usr/share/miubomz/skel/.bashrc | cut -d: -f1)" = miubomz-defaults
test -z "$(dpkg-divert --list /etc/skel/.bashrc)"
test -x /usr/lib/miubomz/apt-pre-snapshot
test -s /etc/dconf/db/miubomz
test -s /etc/apt/apt.conf.d/80-miubomz-snapshots
test -s /etc/sudoers.d/99-miubomz-admin
test -s /etc/polkit-1/rules.d/00-miubomz-admin.rules
test -f /usr/lib/systemd/zram-generator.conf.d/50-miubomz.conf
swapon --noheadings --show=NAME | grep -q '^/dev/zram'

for configuration in \
    /etc/apt/preferences.d/locked-inputs.pref \
    /etc/dpkg/dpkg.cfg.d/calamares-force-unsafe-io; do
    test ! -e "$configuration"
    test ! -e "$configuration.orig"
done

account_home=$(getent passwd "$MIUBOMZ_QA_USERNAME" | cut -d: -f6)
test -n "$account_home"
cmp -s /usr/share/miubomz/skel/.bashrc "$account_home/.bashrc"
test -L "$account_home/.config/gtk-4.0/gtk.css"
test -d "$account_home/.local/share/mise/shims"
grep -qx 'org.gnome.Console.desktop:new-tab' "$account_home/.config/gnome-xdg-terminals.list"
grep -qx 'org.gnome.Console.desktop:new-tab' "$account_home/.config/xdg-terminals.list"
grep -qx 'Exec=/usr/bin/kgx --tab' "$account_home/.local/share/applications/org.gnome.Console.desktop"
test -s "$account_home/.config/mimeapps.list"
id -nG "$MIUBOMZ_QA_USERNAME" | tr ' ' '\n' | grep -qx i2c
test "$(runuser -u "$MIUBOMZ_QA_USERNAME" -- gsettings get org.gnome.desktop.interface color-scheme)" = "'prefer-dark'"
test "$(runuser -u "$MIUBOMZ_QA_USERNAME" -- gsettings get org.gnome.desktop.interface gtk-theme)" = "'Fluent-round-Dark-compact'"

case "$MIUBOMZ_QA_PHASE" in
    live)
        grep -qw boot=live /proc/cmdline
        test ! -e /var/lib/miubomz/installed
        for package in miubomz-installer miubomz-live-settings; do
            test "$(dpkg-query -W -f='${Version}' "$package")" = "$MIUBOMZ_QA_VERSION"
            test "$(dpkg-query -W -f='${Status}' "$package")" = 'install ok installed'
        done
        test -x /usr/bin/calamares
        test -x /usr/lib/live/config/0950-miubomz-software
        test -s /usr/share/applications/calamares-install-miubomz.desktop
        test "$(systemctl show -p ActiveState --value miubomz-recovery-start.service)" = inactive
        ;;
    installed)
        test "$(cat /var/lib/miubomz/installed)" = "Miubomz $MIUBOMZ_QA_VERSION"
        if grep -qw boot=live /proc/cmdline; then
            exit 1
        fi
        for package in miubomz-installer miubomz-live-settings live-boot live-config; do
            if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -qx 'install ok installed'; then
                printf 'Live-only package remains installed: %s\n' "$package" >&2
                exit 1
            fi
        done
        test ! -e /usr/lib/python3/dist-packages/miubomz_installer.py
        test ! -e /usr/lib/live/config/0950-miubomz-software
        test ! -e /usr/share/applications/calamares-install-miubomz.desktop
        test ! -e /etc/apt/sources.list.d/debian-live-media.list
        test "$(findmnt --noheadings --output FSTYPE --target /)" = btrfs
        python3 - <<'CHECK_TIMESHIFT'
import json
import subprocess

with open('/etc/timeshift/timeshift.json') as stream:
    settings = json.load(stream)
uuid = subprocess.check_output([
    'findmnt', '--noheadings', '--output', 'UUID', '--target', '/',
], text=True).strip()
assert settings['backup_device_uuid'] == uuid
assert settings['include_btrfs_home_for_restore'] == 'false'
CHECK_TIMESHIFT
        systemctl is-enabled cron.service miubomz-recovery-start.service grub-btrfsd.service
        test -s /boot/grub/grub.cfg
        ;;
esac
printf 'Passed %s system checks for %s\n' "$MIUBOMZ_QA_PHASE" "$MIUBOMZ_QA_VERSION"
