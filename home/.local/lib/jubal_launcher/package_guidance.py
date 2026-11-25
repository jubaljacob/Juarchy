"""Curated package families and conservative stable-release recommendations.

Arch choices are checked against the configured repository index. AUR choices
must exist in the index and have current RPC metadata before being recommended.
Name suffixes describe variants; they never establish vendor authenticity.
"""

import json
from functools import lru_cache
import os
from pathlib import Path
import re
import tarfile
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OFFICIAL_REPOS = ("core", "extra", "multilib")
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "jubal-launcher/aur-guidance.json"
MAX_AGE = 86400

# Exact primary packages plus known variant suffixes, rather than broad prefix
# matches which could incorrectly label plugins, themes, or extensions.
FAMILIES = (
    {"app": "Visual Studio Code", "aliases": "vscode vs code visual studio code", "arch": "code",
     "aur": "visual-studio-code-bin", "roots": ("code", "visual-studio-code"),
     "arch_note": "Open-source VS Code build; differs from Microsoft's branded release.",
     "aur_note": "Microsoft's stable binary release, packaged by the AUR community.",
     "arch_label": "Code - OSS", "aur_label": "Microsoft Visual Studio Code",
     "url": "https://code.visualstudio.com/"},
    {"app": "Firefox", "aliases": "firefox mozilla browser", "arch": "firefox", "roots": ("firefox",)},
    {"app": "Chromium", "aliases": "chromium browser", "arch": "chromium", "roots": ("chromium",)},
    {"app": "VLC", "aliases": "vlc videolan media player", "arch": "vlc", "roots": ("vlc",)},
    {"app": "mpv", "aliases": "mpv media player", "arch": "mpv", "roots": ("mpv",)},
    {"app": "OBS Studio", "aliases": "obs obs studio recording streaming", "arch": "obs-studio", "roots": ("obs-studio",)},
    {"app": "Thunderbird", "aliases": "thunderbird mozilla email", "arch": "thunderbird", "roots": ("thunderbird",)},
    {"app": "KeePassXC", "aliases": "keepass keepassxc password manager", "arch": "keepassxc", "roots": ("keepassxc",)},
    {"app": "GIMP", "aliases": "gimp image editor", "arch": "gimp", "roots": ("gimp",)},
    {"app": "Inkscape", "aliases": "inkscape vector graphics", "arch": "inkscape", "roots": ("inkscape",)},
    {"app": "Blender", "aliases": "blender 3d modelling", "arch": "blender", "roots": ("blender",)},
    {"app": "Krita", "aliases": "krita painting drawing", "arch": "krita", "roots": ("krita",)},
    {"app": "Discord", "aliases": "discord chat", "arch": "discord", "roots": ("discord",)},
    {"app": "Telegram", "aliases": "telegram telegram desktop messaging", "arch": "telegram-desktop", "roots": ("telegram-desktop",)},
    {"app": "Google Chrome", "aliases": "chrome google chrome browser", "arch": "google-chrome",
     "aur": "google-chrome", "roots": ("google-chrome",),
     "aur_note": "Google's stable Chrome release, packaged by the AUR community.", "url": "https://www.google.com/chrome/"},
    {"app": "Spotify", "aliases": "spotify music", "arch": "spotify", "aur": "spotify", "roots": ("spotify",),
     "aur_note": "The standard stable Spotify desktop package.", "url": "https://www.spotify.com/"},
    {"app": "Zen Browser", "aliases": "zen zen browser", "aur": "zen-browser-bin", "roots": ("zen-browser",),
     "aur_note": "Repackages the stable release published by the Zen project on GitHub; "
                 "Twilight, git and source builds are separate packages.", "url": "https://zen-browser.app/"},
    # Each entry below was checked against its PKGBUILD: the stable package
    # downloads the vendor's own release (or tagged source), not a third-party fork.
    {"app": "Brave", "aliases": "brave browser", "aur": "brave-bin", "roots": ("brave",),
     "aur_note": "Stable release downloaded from Brave's GitHub releases.", "url": "https://brave.com/"},
    {"app": "Microsoft Edge", "aliases": "edge microsoft edge browser", "aur": "microsoft-edge-stable-bin",
     "roots": ("microsoft-edge", "microsoft-edge-stable"),
     "aur_note": "Stable channel package downloaded from packages.microsoft.com.", "url": "https://www.microsoft.com/edge"},
    {"app": "Floorp", "aliases": "floorp browser", "aur": "floorp-bin", "roots": ("floorp",),
     "aur_note": "Stable release downloaded from the Floorp project's GitHub releases.", "url": "https://floorp.app/"},
    {"app": "Tor Browser", "aliases": "tor browser onion privacy", "aur": "tor-browser-bin", "roots": ("tor-browser",),
     "aur_note": "Stable release downloaded from the Tor Project archive.", "url": "https://www.torproject.org/"},
    {"app": "Mullvad Browser", "aliases": "mullvad browser privacy", "aur": "mullvad-browser-bin", "roots": ("mullvad-browser",),
     "aur_note": "Stable release downloaded from dist.torproject.org.", "url": "https://mullvad.net/en/browser"},
    {"app": "Slack", "aliases": "slack chat team", "aur": "slack-desktop", "roots": ("slack-desktop",),
     "aur_note": "Stable release downloaded from Slack's download servers.", "url": "https://slack.com/downloads"},
    {"app": "Zoom", "aliases": "zoom meetings video conferencing", "aur": "zoom", "roots": ("zoom",),
     "aur_note": "Stable client downloaded from zoom.us.", "url": "https://zoom.us/"},
    {"app": "ONLYOFFICE", "aliases": "onlyoffice desktop editors office suite", "aur": "onlyoffice-bin", "roots": ("onlyoffice",),
     "aur_note": "Stable release downloaded from ONLYOFFICE's GitHub releases.", "url": "https://www.onlyoffice.com/"},
    {"app": "1Password", "aliases": "1password password manager", "aur": "1password", "roots": ("1password",),
     "aur_note": "Stable release downloaded from downloads.1password.com.", "url": "https://1password.com/"},
    {"app": "Dropbox", "aliases": "dropbox sync cloud storage", "aur": "dropbox", "roots": ("dropbox",),
     "aur_note": "Stable client downloaded from Dropbox's servers.", "url": "https://www.dropbox.com/"},
    {"app": "Postman", "aliases": "postman api client", "aur": "postman-bin", "roots": ("postman",),
     "aur_note": "Stable release downloaded from Postman's download server.", "url": "https://www.postman.com/"},
    {"app": "Insomnia", "aliases": "insomnia api client rest", "aur": "insomnia-bin", "roots": ("insomnia",),
     "aur_note": "Stable release downloaded from Kong's Insomnia GitHub releases.", "url": "https://insomnia.rest/"},
    {"app": "Android Studio", "aliases": "android studio ide", "aur": "android-studio", "roots": ("android-studio",),
     "aur_note": "Stable release downloaded from dl.google.com.", "url": "https://developer.android.com/studio"},
    {"app": "JetBrains Toolbox", "aliases": "jetbrains toolbox ide manager", "aur": "jetbrains-toolbox",
     "roots": ("jetbrains-toolbox",),
     "aur_note": "Stable release downloaded from download.jetbrains.com.", "url": "https://www.jetbrains.com/toolbox-app/"},
    {"app": "Cursor", "aliases": "cursor ai code editor", "aur": "cursor-bin", "roots": ("cursor-bin",),
     "aur_note": "Stable release downloaded from downloads.cursor.com.", "url": "https://www.cursor.com/"},
    {"app": "Sublime Text", "aliases": "sublime text editor", "aur": "sublime-text-4", "roots": ("sublime-text-4", "sublime-text"),
     "aur_note": "Stable build downloaded from download.sublimetext.com.", "url": "https://www.sublimetext.com/"},
    {"app": "Mullvad VPN", "aliases": "mullvad vpn", "aur": "mullvad-vpn-bin", "roots": ("mullvad-vpn",),
     "aur_note": "Stable release downloaded from Mullvad's GitHub releases.", "url": "https://mullvad.net/"},
    {"app": "NordVPN", "aliases": "nordvpn vpn", "aur": "nordvpn-bin", "roots": ("nordvpn",),
     "aur_note": "Stable release downloaded from repo.nordvpn.com.", "url": "https://nordvpn.com/download/linux/"},
    {"app": "Minecraft Launcher", "aliases": "minecraft launcher mojang game", "aur": "minecraft-launcher",
     "roots": ("minecraft-launcher",),
     "aur_note": "Official launcher downloaded from Mojang.", "url": "https://www.minecraft.net/"},
    {"app": "TeamViewer", "aliases": "teamviewer remote desktop", "aur": "teamviewer", "roots": ("teamviewer",),
     "aur_note": "Stable release downloaded from dl.teamviewer.com.", "url": "https://www.teamviewer.com/"},
    {"app": "AnyDesk", "aliases": "anydesk remote desktop", "aur": "anydesk-bin", "roots": ("anydesk",),
     "aur_note": "Stable release downloaded from download.anydesk.com.", "url": "https://anydesk.com/"},
    {"app": "Ventoy", "aliases": "ventoy bootable usb", "aur": "ventoy-bin", "roots": ("ventoy",),
     "aur_note": "Stable release downloaded from Ventoy's GitHub releases.", "url": "https://www.ventoy.net/"},
    {"app": "Heroic Games Launcher", "aliases": "heroic games launcher epic gog", "aur": "heroic-games-launcher-bin",
     "roots": ("heroic-games-launcher",),
     "aur_note": "Stable release downloaded from the Heroic project's GitHub releases.", "url": "https://heroicgameslauncher.com/"},
    {"app": "balenaEtcher", "aliases": "balena etcher flash usb images", "aur": "balena-etcher", "roots": ("balena-etcher",),
     "aur_note": "Built from the tagged stable source of balena-io/etcher on GitHub.", "url": "https://etcher.balena.io/"},
)
VARIANT_SUFFIX = re.compile(r"(?:-(?:bin|git|svn|hg|bzr|cvs|darcs|beta|alpha|nightly|dev|canary|insiders|rc|stable|oss|esr))+")
VARIANT_TAIL = re.compile(VARIANT_SUFFIX.pattern + r"\Z")


@lru_cache(maxsize=131072)
def base_name(name):
    """Package name without trailing build-variant suffixes: htop-git -> htop."""
    match = VARIANT_TAIL.search(name)
    return name[:match.start()] if match and match.start() else name


def contested_bases(names):
    """Names that AUR packages offer build variants of, e.g. {'htop'} for htop-git."""
    return frozenset(base for name in names if (base := base_name(name)) != name)


def implicit_family(name, choices, contested):
    """An Arch repository app that the AUR also offers variants of needs no curated entry.

    The stable repository build is then the recommended one, and the AUR
    variants point to it. Apps nobody builds variants of are left untagged.
    """
    base = base_name(name)
    if base in contested and base in choices:
        return {"app": base, "arch": base}
    return None


def clean(value):
    """Keep metadata on one line and strip terminal control characters."""
    return " ".join(re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", str(value or "")).split())


@lru_cache(maxsize=131072)
def family_for(name):
    for family in FAMILIES:
        for root in family["roots"]:
            if name == root or (name.startswith(root) and VARIANT_SUFFIX.fullmatch(name[len(root):])):
                return family
    return None


def variant(name, repo):
    tokens = name.split("-")
    if any(t in tokens for t in ("beta", "alpha", "rc", "canary", "insiders")):
        return "Preview"
    if any(t in tokens for t in ("git", "svn", "hg", "bzr", "cvs", "darcs", "nightly", "dev")):
        return "Development"
    if "testing" in repo or "staging" in repo:
        return "Testing repository"
    if repo in OFFICIAL_REPOS or (family_for(name) and name in (family_for(name).get("arch"), family_for(name).get("aur"))):
        return "Stable"
    return "Release"  # Unverified release channel; absence of -git is not proof.


def repo_choices(rows):
    choices = {}
    for repo in OFFICIAL_REPOS:
        for row in rows:
            target = row.split()[0]
            source, name = target.split("/", 1)
            if source == repo and variant(name, source) == "Stable":
                choices.setdefault(name, target)
    return choices


def repo_descriptions(database_dir=Path("/var/lib/pacman/sync")):
    """Read local sync databases without a network request per package."""
    result = {}
    for path in sorted(database_dir.glob("*.db")):
        try:
            with tarfile.open(path, "r:*") as archive:
                for member in archive:
                    if not member.isfile() or not member.name.endswith("/desc"):
                        continue
                    file = archive.extractfile(member)
                    if file is None:
                        continue
                    fields = {}
                    for block in file.read().decode("utf-8", errors="replace").split("\n\n"):
                        lines = block.splitlines()
                        if lines and lines[0].startswith("%"):
                            fields[lines[0].strip("%")] = lines[1:]
                    if fields.get("NAME"):
                        result[f"{path.stem}/{fields['NAME'][0]}"] = clean(" ".join(fields.get("DESC", [])))
        except (OSError, tarfile.TarError):
            continue
    return result


def aur_metadata(names, refresh=False):
    """Check only curated candidates; cache successful checks for one day."""
    names = sorted(set(names))
    if not names:
        return {}, False
    try:
        cached = json.loads(CACHE.read_text())
        records = cached["records"]
        requested = set(cached["requested"])
        if not isinstance(records, dict):
            raise ValueError("Invalid cache")
        current = 0 <= time.time() - cached["checked_at"] < MAX_AGE
        if current and not refresh and set(names).issubset(requested):
            return {n: records[n] for n in names if n in records}, True
    except (OSError, ValueError, KeyError, TypeError):
        records, current, requested = {}, False, set()
    try:
        url = "https://aur.archlinux.org/rpc/v5/info?" + urlencode([("arg[]", n) for n in names])
        request = Request(url, headers={"User-Agent": "jubal-package-browser/1.0"})
        with urlopen(request, timeout=6) as response:
            payload = json.load(response)
        if payload.get("type") != "multiinfo" or not isinstance(payload.get("results"), list):
            raise ValueError("Invalid AUR response")
        new_records = {p["Name"]: p for p in payload["results"] if p.get("Name") in names}
        if current and not refresh:
            # Preserve other preview results without extending their lifetime.
            checked_at = cached["checked_at"]
            records = {**records, **new_records}
            requested.update(names)
        else:
            checked_at = time.time()
            records = new_records
            requested = set(names)
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        temporary = CACHE.with_name(f"aur-guidance.{os.getpid()}.tmp")
        try:
            temporary.write_text(json.dumps({"checked_at": checked_at, "requested": sorted(requested), "records": records}))
            temporary.replace(CACHE)
        finally:
            temporary.unlink(missing_ok=True)
        return {n: records[n] for n in names if n in records}, True
    except (OSError, ValueError, KeyError, TypeError):
        # Expired metadata can describe a package but cannot earn a badge.
        return {n: records[n] for n in names if n in records}, current


def guidance(target, choices, metadata=None, metadata_current=False, contested=frozenset()):
    repo, name = target.split("/", 1)
    family = family_for(name) or implicit_family(name, choices, contested)
    channel = variant(name, repo)
    tags = [channel]
    reason = ""
    recommended = False
    record = (metadata or {}).get(name, {}) if repo == "aur" else {}
    if repo in OFFICIAL_REPOS:
        tags.append("Arch repository")
    elif repo == "aur":
        tags.append("AUR community")
    else:
        tags.append("Configured repository")
    preferred = choices.get(family.get("arch")) if family else None
    if family and channel == "Stable":
        if preferred == target:
            recommended = True
            reason = "Stable Arch repository package; your preferred source. " + family.get("arch_note", "")
        elif repo == "aur" and preferred:
            tags.append("Arch alternative: " + preferred)
            reason = "Prefer " + preferred + " for the stable Arch package. " + family.get("aur_note", "")
        elif repo == "aur" and name == family.get("aur"):
            if metadata_current and record.get("Maintainer") and not record.get("OutOfDate"):
                recommended = True
                reason = "Stable curated AUR choice; no stable Arch package for this app is in your configured repositories. " + family.get("aur_note", "")
            else:
                reason = "Curated stable candidate; maintenance status is unavailable or needs attention. " + family.get("aur_note", "")
    elif family and preferred:
        reason = "Use " + preferred + " for the stable Arch version."
    if name.endswith("-bin"):
        tags.append("Prebuilt binary")
    if record:
        if not record.get("Maintainer"):
            tags.append("Orphaned" if metadata_current else "Previously orphaned")
        if record.get("OutOfDate"):
            tags.append("Out of date" if metadata_current else "Previously out of date")
    if recommended:
        tags.insert(0, "Recommended")
    return tags, clean(reason), recommended


def build_label(target):
    repo, name = target.split("/", 1)
    family = family_for(name)
    if not family:
        return ""
    if repo != "aur" and name == family.get("arch"):
        return family.get("arch_label", family["app"])
    if repo == "aur" and name == family.get("aur"):
        return family.get("aur_label", family["app"])
    return family["app"]


def decorate(rows, choices, descriptions=None, metadata=None, metadata_current=False):
    decorated = []
    targets = [row.split()[0] for row in rows]
    contested = contested_bases(t.split("/", 1)[1] for t in targets if t.startswith("aur/"))
    for row, target in zip(rows, targets):
        repo, name = target.split("/", 1)
        curated = family_for(name)
        family = curated or implicit_family(name, choices, contested)
        tags, reason, recommended = guidance(target, choices, metadata, metadata_current, contested)
        if "[installed]" in row:
            tags.append("Installed")
        detail = (descriptions or {}).get(target, "")
        if repo == "aur":
            detail = clean((metadata or {}).get(name, {}).get("Description", "")) or detail
        # The searchable text includes human names and aliases, but not badges.
        search = clean(" ".join(filter(None, [build_label(target), (family or {}).get("aliases", ""), detail])))
        if not search:
            search = name
        label = build_label(target)
        display = target + "\t" + (label + " · " if label else "") + " ".join(f"[{t}]" for t in tags) + "\t" + search
        channel = variant(name, repo)
        if recommended:
            rank = 0 if curated else 1  # Curated picks lead; derived Arch picks follow.
        elif channel in ("Development", "Preview", "Testing repository"):
            rank = 4
        elif family and channel == "Stable":
            rank = 2  # Main stable app before plugins and unrelated matches.
        else:
            rank = 3
        decorated.append(((rank, target), display))
    return [row for _, row in sorted(decorated)]


def suggested_arch_rows(choices, aur_names):
    """Offer each app's Arch choice inside AUR searches without hiding variants."""
    available = {arch for name in aur_names if (family := family_for(name)) and (arch := family.get("arch"))}
    return [choices[f["arch"]] for f in FAMILIES
            if f.get("arch") in choices and f["arch"] in available]
