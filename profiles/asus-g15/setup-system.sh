#!/usr/bin/env bash
# System-side setup for the ASUS ROG Zephyrus G15 (GA503RM) profile.
#
#   profiles/asus-g15/setup-system.sh           preview: print every command
#   profiles/asus-g15/setup-system.sh --apply   run them (asks for sudo)
#
# Installs drivers and ASUS/Logitech packages, copies the /etc configs in
# system/etc (backing up any existing file), and enables the services.
# Run it after `python scripts/install.py --profile asus-g15 --apply`, which
# installs the per-user files (including the asus-profile-sync user unit).

set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
apply=0
[[ ${1:-} == --apply ]] && apply=1
stamp=$(date +%Y%m%d-%H%M%S)

run() {
    printf '+ %s\n' "$*"
    (( apply )) && "$@"
    return 0
}

list() { grep -v -e '^#' -e '^[[:space:]]*$' "$1"; }

(( apply )) || echo "Preview only. Re-run with --apply to make these changes."
echo

echo "== Official packages"
mapfile -t pkgs < <(list "$here/packages.txt")
run sudo pacman -S --needed "${pkgs[@]}"

echo "== AUR packages"
mapfile -t aur < <(list "$here/aur.txt")
if command -v yay >/dev/null; then
    run yay -S --needed "${aur[@]}"
else
    echo "yay not found: install these AUR packages yourself: ${aur[*]}"
fi

echo "== /etc configuration"
while IFS= read -r -d '' src; do
    dest=/${src#"$here/system/"}
    if [[ -e $dest ]] && ! cmp -s "$src" "$dest"; then
        run sudo cp -p "$dest" "$dest.bak-$stamp"
    fi
    run sudo install -D -m 644 "$src" "$dest"
done < <(find "$here/system" -type f -print0 | sort -z)

echo "== System services"
run sudo systemctl enable --now power-profiles-daemon.service bluetooth.service logid.service
run sudo systemctl enable nvidia-suspend.service nvidia-resume.service nvidia-hibernate.service
# asusd is started by udev/D-Bus; restart it so it reads the copied config.
run sudo systemctl restart asusd.service
run sudo udevadm control --reload-rules
run sudo udevadm trigger

echo "== User services"
run systemctl --user daemon-reload
run systemctl --user enable --now asus-profile-sync.service
run systemctl --user enable hypridle.service openlogi-agent.service

echo
(( apply )) && echo "Done. Reboot so the NVIDIA modules and new kernel images load." || true
