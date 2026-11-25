"""Regression checks for recommendations and exact package installation targets."""

import importlib.machinery
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from jubal_launcher import package_guidance as guidance

SCRIPT = Path(__file__).resolve().parents[2] / "bin/jubal-packages"
loader = importlib.machinery.SourceFileLoader("package_browser", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
browser = importlib.util.module_from_spec(spec)
loader.exec_module(browser)


class GuidanceTests(unittest.TestCase):
    def test_arch_beats_aur_and_testing(self):
        choices = guidance.repo_choices(["extra-testing/code 2.0", "extra/code 1.0"])
        self.assertEqual(choices["code"], "extra/code")
        metadata = {"visual-studio-code-bin": {"Maintainer": "tester", "OutOfDate": None}}
        self.assertTrue(guidance.guidance("extra/code", choices)[2])
        tags, reason, recommended = guidance.guidance("aur/visual-studio-code-bin", choices, metadata, True)
        self.assertFalse(recommended)
        self.assertIn("Arch alternative: extra/code", tags)
        self.assertIn("Microsoft", reason)
        self.assertFalse(guidance.guidance("extra-testing/code", choices)[2])

    def test_aur_needs_current_maintained_metadata(self):
        target = "aur/visual-studio-code-bin"
        for record, current, expected in [
            ({"Maintainer": "tester", "OutOfDate": None}, True, True),
            ({"Maintainer": "tester", "OutOfDate": None}, False, False),
            ({"Maintainer": None, "OutOfDate": None}, True, False),
            ({"Maintainer": "tester", "OutOfDate": 123}, True, False),
            ({}, True, False),
        ]:
            with self.subTest(record=record, current=current):
                self.assertEqual(guidance.guidance(target, {}, {"visual-studio-code-bin": record}, current)[2], expected)

    def test_preview_and_development_never_recommended(self):
        for name in ("code-git", "firefox-beta", "visual-studio-code-insiders-bin", "firefox-nightly"):
            with self.subTest(name=name):
                self.assertIn(guidance.variant(name, "aur"), ("Development", "Preview"))
                self.assertFalse(guidance.guidance("aur/" + name, {"code": "extra/code"})[2])

    def test_plugins_and_alternatives_are_not_the_main_app(self):
        for name in ("code-marketplace", "firefox-extension-ublock-origin", "vlc-plugin-ffmpeg", "vscodium-bin"):
            self.assertIsNone(guidance.family_for(name))
            self.assertFalse(guidance.guidance("aur/" + name, {})[2])
        self.assertEqual(guidance.variant("unverified-app-bin", "aur"), "Release")

    def test_zen_only_the_stable_binary_is_recommended(self):
        metadata = {n: {"Maintainer": "tester", "OutOfDate": None}
                    for n in ("zen-browser-bin", "zen-browser", "zen-browser-git", "zen-browser-twilight-bin")}
        self.assertTrue(guidance.guidance("aur/zen-browser-bin", {}, metadata, True)[2])
        self.assertFalse(guidance.guidance("aur/zen-browser-bin", {}, metadata, False)[2])
        for name in ("zen-browser", "zen-browser-git", "zen-browser-twilight-bin", "zen-browser-ublock-origin"):
            with self.subTest(name=name):
                self.assertFalse(guidance.guidance("aur/" + name, {}, metadata, True)[2])
        self.assertEqual(guidance.suggested_arch_rows({"code": "extra/code"}, ["zen-browser-bin"]), [])
        rows = guidance.decorate(["aur/zen-browser-git", "aur/zen-browser-twilight-bin", "aur/zen-browser-bin"], {}, None, metadata, True)
        self.assertEqual(rows[0].split()[0], "aur/zen-browser-bin")
        self.assertIn("[Recommended]", rows[0])
        self.assertTrue(all("[Recommended]" not in row for row in rows[1:]))

    def test_every_curated_aur_choice_resolves_to_itself_as_stable(self):
        names = [f["aur"] for f in guidance.FAMILIES if f.get("aur")]
        self.assertEqual(len(names), len(set(names)))
        for family in guidance.FAMILIES:
            if family.get("aur"):
                with self.subTest(app=family["app"]):
                    self.assertIs(guidance.family_for(family["aur"]), family)
                    self.assertEqual(guidance.variant(family["aur"], "aur"), "Stable")
                    record = {family["aur"]: {"Maintainer": "tester", "OutOfDate": None}}
                    self.assertTrue(guidance.guidance("aur/" + family["aur"], {}, record, True)[2])

    def test_curated_vendor_variants_are_never_recommended(self):
        metadata = {}
        for name in ("brave-beta-bin", "brave-nightly-bin", "brave-git", "microsoft-edge-beta-bin",
                     "microsoft-edge-dev-bin", "android-studio-canary", "1password-beta", "teamviewer-beta",
                     "tor-browser-alpha-bin", "mullvad-vpn-beta-bin", "sublime-text-dev", "zoom-git"):
            with self.subTest(name=name):
                self.assertIsNotNone(guidance.family_for(name))
                self.assertIn(guidance.variant(name, "aur"), ("Development", "Preview"))
                self.assertFalse(guidance.guidance("aur/" + name, {}, metadata, True)[2])
        for name in ("slack-desktop-wayland", "zoom-firejail", "cursor-theme", "dropbox-cli", "brave-nightly"):
            with self.subTest(name=name):
                self.assertFalse(guidance.guidance("aur/" + name, {}, {}, True)[2])

    def test_arch_build_is_recommended_when_the_aur_offers_variants_of_it(self):
        choices = guidance.repo_choices(["extra/htop 3.4", "extra/nano 8.0", "extra-testing/foo 2", "extra/foo 1"])
        rows = ["extra/htop 3.4", "extra/nano 8.0", "aur/htop-git", "aur/htop-bin", "aur/htop-vim", "extra/foo 1", "aur/foo-nightly"]
        decorated = guidance.decorate(rows, choices)
        by_target = {row.split()[0]: row for row in decorated}
        self.assertIn("[Recommended]", by_target["extra/htop"])
        self.assertIn("[Recommended]", by_target["extra/foo"])
        for target in ("extra/nano", "aur/htop-git", "aur/htop-bin", "aur/htop-vim", "aur/foo-nightly"):
            self.assertNotIn("[Recommended]", by_target[target])
        self.assertEqual({r.split()[0] for r in decorated[:2]}, {"extra/htop", "extra/foo"})
        for target in ("aur/htop-git", "aur/htop-bin"):
            self.assertEqual(guidance.guidance(target, choices, None, False, guidance.contested_bases(["htop-git"]))[1],
                             "Use extra/htop for the stable Arch version.")
        # Without AUR variants to confuse it with, an ordinary package carries no badge.
        self.assertFalse(guidance.guidance("extra/htop", choices)[2])
        self.assertTrue(guidance.guidance("extra/htop", choices, None, False, frozenset({"htop"}))[2])
        self.assertEqual(guidance.base_name("visual-studio-code-insiders-bin"), "visual-studio-code")
        self.assertEqual(guidance.base_name("bin"), "bin")

    def test_curated_picks_rank_ahead_of_derived_arch_picks(self):
        metadata = {"brave-bin": {"Maintainer": "tester", "OutOfDate": None}}
        rows = ["extra/htop 3.4", "aur/htop-git", "aur/brave-git", "aur/brave-bin"]
        decorated = guidance.decorate(rows, {"htop": "extra/htop"}, None, metadata, True)
        self.assertEqual([r.split()[0] for r in decorated],
                         ["aur/brave-bin", "extra/htop", "aur/brave-git", "aur/htop-git"])

    def test_alias_search_and_recommendation_order_with_real_fzf(self):
        rows = guidance.decorate(["aur/visual-studio-code-insiders-bin", "aur/visual-studio-code-bin", "extra/code 1.0"], {"code": "extra/code"})
        result = subprocess.run(["fzf", "--delimiter=\t", "--nth=1,3", "--exact", "--no-sort", "--filter=vscode"],
                                input="\n".join(rows), capture_output=True, text=True, check=True)
        matched = result.stdout.splitlines()
        self.assertEqual(matched[0].split()[0], "extra/code")
        self.assertEqual(matched[-1].split()[0], "aur/visual-studio-code-insiders-bin")
        self.assertEqual(len(matched), 3)

    def test_aur_search_includes_arch_suggestion(self):
        choices = {"code": "extra/code", "vlc": "extra/vlc"}
        self.assertEqual(guidance.suggested_arch_rows(choices, ["visual-studio-code-bin", "code-git"]), ["extra/code"])

    def test_preview_cache_keeps_other_apps_without_extending_age(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "guidance.json"
            stamp = time.time() - 100
            cache.write_text(json.dumps({"checked_at": stamp, "requested": ["spotify"],
                                         "records": {"spotify": {"Name": "spotify", "Maintainer": "test"}}}))
            payload = {"type": "multiinfo", "results": [{"Name": "google-chrome", "Maintainer": "test"}]}
            class Response:
                def __enter__(self):
                    import io
                    return io.StringIO(json.dumps(payload))
                def __exit__(self, *args):
                    pass
            with patch.object(guidance, "CACHE", cache), patch.object(guidance, "urlopen", return_value=Response()):
                records, current = guidance.aur_metadata(["google-chrome"])
                self.assertTrue(current)
                self.assertIn("google-chrome", records)
                saved = json.loads(cache.read_text())
                self.assertEqual(saved["checked_at"], stamp)
                self.assertIn("spotify", saved["records"])
            with patch.object(guidance, "CACHE", cache), patch.object(guidance, "urlopen") as request:
                self.assertTrue(guidance.aur_metadata(["spotify"])[1])
                request.assert_not_called()

    def test_stale_offline_metadata_cannot_recommend(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "guidance.json"
            cache.write_text(json.dumps({"checked_at": time.time() - 90000, "requested": ["spotify"],
                                         "records": {"spotify": {"Maintainer": "test", "OutOfDate": None}}}))
            with patch.object(guidance, "CACHE", cache), patch.object(guidance, "urlopen", side_effect=OSError("offline")):
                records, current = guidance.aur_metadata(["spotify"])
                self.assertFalse(current)
                self.assertFalse(guidance.guidance("aur/spotify", {}, records, current)[2])

    def test_install_commands_preserve_sources(self):
        self.assertEqual(browser.install_command("aur", ["extra/code"]),
                         ["sudo", "pacman", "-S", "--needed", "--confirm", "--", "extra/code"])
        self.assertEqual(browser.install_command("aur", ["aur/spotify"]),
                         ["yay", "-S", "--aur", "--needed", "--confirm", "--", "aur/spotify"])
        self.assertEqual(browser.install_command("aur", ["extra/code", "aur/spotify"]),
                         ["yay", "-S", "--needed", "--confirm", "--", "extra/code", "aur/spotify"])
        with self.assertRaises(ValueError):
            browser.install_command("arch", ["aur/spotify"])
        with self.assertRaises(ValueError):
            browser.install_command("aur", ["untrusted/code"])

    def test_selection_uses_exact_targets_and_rejects_injected_targets(self):
        rows = ["extra/code\t[Recommended] [Stable]\tvscode", "aur/spotify\t[Stable]\tspotify"]
        result = subprocess.CompletedProcess([], 0, "enter\n" + "\n".join(rows) + "\n")
        with patch.object(browser.subprocess, "run", return_value=result):
            self.assertEqual(browser.select_packages("aur", rows, "test"), ("install", ["extra/code", "aur/spotify"]))
        for output in ("enter\nextra/firefox\n", "enter\naur/spotify;touch /tmp/injected\n"):
            with patch.object(browser.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output)):
                with self.assertRaises(RuntimeError):
                    browser.select_packages("aur", rows, "test")

    def test_removal_picker_keeps_existing_behavior(self):
        rows = ["firefox 1.0"]
        result = subprocess.CompletedProcess([], 0, "enter\nfirefox 1.0\n")
        with patch.object(browser.subprocess, "run", return_value=result):
            self.assertEqual(browser.select_packages("remove", rows, "test"), ("remove", ["firefox"]))
        self.assertNotIn("--no-sort", browser.picker_command("remove", "test"))

    def test_terminal_metadata_is_sanitized(self):
        self.assertEqual(guidance.clean("hello\nworld\x1b\t!"), "hello world !")

    def test_combined_catalogue_filters_and_deduplication(self):
        repos = ["extra/code 1.0 [installed]", "core/bash 5.0", "extra/code 1.0 [installed]"]
        with patch.object(browser, "repository_rows", return_value=repos), \
             patch.object(browser, "cached_aur", return_value=(time.time(), ["visual-studio-code-bin", "spotify", "spotify"])), \
             patch.object(browser, "query", return_value="code\n"), \
             patch.object(browser, "aur_metadata", return_value=({}, False)), \
             patch.object(browser, "repo_descriptions", return_value={}):
            rows, _ = browser.load_packages("all")
            targets = [r.split()[0] for r in rows]
            self.assertEqual(len(targets), len(set(targets)))
            self.assertEqual(set(targets), {"extra/code", "core/bash", "aur/visual-studio-code-bin", "aur/spotify"})
            arch, _ = browser.load_packages("all", source_filter="arch")
            aur, _ = browser.load_packages("all", source_filter="aur")
            self.assertTrue(all(not row.startswith("aur/") for row in arch))
            self.assertTrue(all(row.startswith("aur/") for row in aur))
            self.assertEqual(targets[0], "extra/code")

    def test_combined_catalogue_works_when_aur_is_unavailable(self):
        with patch.object(browser, "repository_rows", return_value=["extra/code 1.0"]), \
             patch.object(browser, "cached_aur", return_value=(0, [])), \
             patch.object(browser, "query", side_effect=[RuntimeError("offline"), "code\n"]), \
             patch.object(browser, "aur_metadata", return_value=({}, False)), \
             patch.object(browser, "repo_descriptions", return_value={}):
            rows, notice = browser.load_packages("all")
            self.assertEqual([r.split()[0] for r in rows], ["extra/code"])
            self.assertIn("AUR unavailable", notice)

    def test_selection_after_source_filter_uses_full_allowed_set(self):
        rows = ["extra/code\t[Recommended]\tvscode", "aur/spotify\t[Stable]\tspotify"]
        result = subprocess.CompletedProcess([], 0, "enter\n" + rows[1] + "\n")
        with patch.object(browser.subprocess, "run", return_value=result):
            self.assertEqual(browser.select_packages("all", rows[:1], "test", "arch", allowed_rows=rows),
                             ("install", ["aur/spotify"]))
        self.assertEqual(browser.filter_rows(rows, "arch"), rows[:1])
        self.assertEqual(browser.filter_rows(rows, "aur"), rows[1:])

    def test_combined_install_routes_arch_aur_and_mixed_sources(self):
        for targets, prefix in [(["extra/code"], ["sudo", "pacman", "-S"]),
                                (["aur/spotify"], ["yay", "-S", "--aur"]),
                                (["extra/code", "aur/spotify"], ["yay", "-S"])]:
            command = browser.install_command("all", targets)
            self.assertEqual(command[:len(prefix)], prefix)
            self.assertEqual(command[-len(targets):], targets)
        with self.assertRaises(ValueError):
            browser.install_command("all", ["aur/spotify;touch"])

    def test_build_names_make_vscode_difference_visible(self):
        rows = guidance.decorate(["extra/code 1.0", "aur/visual-studio-code-bin"], {"code": "extra/code"})
        self.assertIn("Code - OSS", rows[0])
        self.assertIn("Microsoft Visual Studio Code", rows[1])
        for term, target in (("code oss", "extra/code"), ("microsoft visual studio code", "aur/visual-studio-code-bin")):
            result = subprocess.run(["fzf", "--delimiter=\t", "--nth=1,3", "--exact", "--filter=" + term],
                                    input="\n".join(rows), capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.split()[0], target)


if __name__ == "__main__":
    unittest.main()
