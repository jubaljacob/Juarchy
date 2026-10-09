import QtQuick
import QtTest
import "../../shell/modules/spotlight/SearchPolicy.js" as Policy

TestCase {
    name: "SpotlightSearchPolicy"

    function test_settings_opens_main_panel_before_display_app() {
        const apps = Policy.appRows([{id: "nwg-displays", name: "Displays Settings"}], "settings");
        const rows = Policy.rows("all", "settings", apps, []);
        compare(rows[0].title, "Settings");
        compare(rows[0].kind, "settings");
        compare(rows[0].page, "");
        compare(rows[1].title, "Displays Settings");
        compare(rows.length, 2);
        compare(Policy.rows("all", "preferences", [], [])[0].title, "Settings");
        compare(Policy.rows("all", "display settings", Policy.appRows([{id: "nwg-displays", name: "Displays Settings"}], "display settings"), [])[0].kind, "app");
    }

    function test_app_names_win_and_descriptions_do_not_match() {
        const apps = Policy.appRows([
            {id: "firefox", name: "Firefox", comment: "Web browser"},
            {id: "other", name: "Other", comment: "Firefox helper"},
            {id: "helper", name: "Firefox Helper"}
        ], "firefox");
        compare(apps.length, 2);
        const rows = Policy.rows("all", "firefox", apps, [{kind: "file", title: "Firefox.pdf", value: "/Firefox.pdf", score: 950}]);
        compare(rows[0].title, "Firefox");
        compare(rows[0].kind, "app");
        compare(Policy.appRows([{id: "f", name: "Firefox"}], "fox").length, 0);
        compare(Policy.appRows([{id: "f", name: "Firefox"}], "fire")[0].title, "Firefox");
    }

    function test_settings_page_destinations() {
        compare(Policy.settingsRows("audio settings")[0].page, "audio");
        compare(Policy.settingsRows("wallpaper")[0].page, "appearance");
        const notifications = Policy.settingsRows("notification history")[0];
        compare(notifications.page, "services");
        compare(notifications.subPage, 1);
    }

    function test_compact_results_and_files_mode() {
        const extras = [];
        for (let i = 0; i < 12; i++) extras.push({kind: "file", title: "Report " + i, value: "/" + i, score: 900});
        extras.push({kind: "mode", value: "web"});
        compare(Policy.rows("all", "report", [], extras).length, 5);
        compare(Policy.rows("files", "report", [], extras).length, 13);
        const apps = Policy.appRows([{name: "Report", id: "report"}], "report");
        compare(Policy.rows("all", "report", apps, extras).length, 1);
        for (let i = 0; i < 12; i++) extras[i].score = 950;
        compare(Policy.rows("all", "report", apps, extras).length, 3);
    }

    function test_calculation_and_explicit_currency_stay_accessible() {
        const answers = Policy.rows("all", "2+2", [], [
            {kind: "copy", title: "4", value: "4"},
            {kind: "file", title: "2.jpg", value: "/2.jpg", score: 900}
        ]);
        compare(answers[0].title, "4");
        compare(answers.length, 1);
        compare(Policy.rows("all", "10 GBP to INR", [], [{kind: "mode", value: "currency"}])[0].value, "currency");
    }

    function test_unified_context_keeps_apps_first_and_avoids_web_clutter() {
        const apps = Policy.appRows([{id: "chromium", name: "Chromium", icon: "chromium"}], "chro");
        const fallback = {kind: "url", title: "Search web", value: "https://example.com"};
        const rows = Policy.rows("search", "chro", apps, [fallback], "search");
        compare(rows.length, 1);
        compare(rows[0].title, "Chromium");
        compare(rows[0].appIcon, "chromium");
        compare(Policy.rows("search", "settings", [], [fallback], "search")[0].title, "Settings");
        compare(Policy.rows("search", "unmatched", [], [fallback], "search")[0].kind, "url");
        compare(Policy.rows("search", "report", [], [{kind: "file", score: 900}, fallback], "search").length, 1);
    }

    function test_unified_answers_errors_and_explicit_web() {
        const app = {kind: "app", title: "Converter", score: 1000};
        const answer = {kind: "copy", value: "10"};
        const error = {kind: "info", title: "Incompatible units"};
        compare(Policy.rows("search", "10 km to mi", [app], [answer], "answer")[0].kind, "copy");
        compare(Policy.rows("search", "1 kg to km", [app], [error], "conversion")[0].kind, "info");
        compare(Policy.rows("search", "web settings", [], [{kind: "url"}], "web")[0].kind, "url");
        compare(Policy.rows("search", "web settings", [], [], "search").length, 0);
        const files = [];
        for (let i = 0; i < 10; i++) files.push({kind: "file", score: 400});
        compare(Policy.rows("search", "files: port", [], files, "files").length, 10);
        compare(Policy.rows("search", "port", [], files, "search").length, 5);
    }

    function test_highlighting_escapes_file_names() {
        compare(Policy.highlightTitle("Project_Report.pdf", "project report"), "<b>Project</b>_<b>Report</b>.pdf");
        compare(Policy.highlightTitle("<img src=x>.pdf", "unrelated"), "&lt;img src=x&gt;.pdf");
    }

    function test_compact_web_card_and_context_detection() {
        const preview = {kind: "web", title: "Rainbow", value: "https://example.com/article"};
        const links = [preview];
        for (let i = 0; i < 5; i++) links.push({kind: "url", role: "web-link"});
        compare(Policy.rows("search", "what is a rainbow", [], links, "web").length, 3);
        compare(Policy.rowHeight(links[1]), 48);
        compare(Policy.rowHeight({kind: "app"}), 62);
        for (const q of ["what is a rainbow", "how do rainbows form", "define entropy", "tell me about Mars", "rainbows?", "web rainbow"])
            verify(Policy.isWebQuery(q), q);
        for (const q of ["settings", "chro", "project report", "600gbp to aed", "2+2"])
            verify(!Policy.isWebQuery(q), q);
    }

    function webData(title, state) {
        return {mode: "search", query: title, intent: "web", status: "Preview",
            results: [{kind: state === "ready" ? "web" : "url", title: title, previewState: state}]};
    }

    function test_web_cache_expiry_does_not_extend_on_read_and_fallbacks_expire_sooner() {
        const cache = {entries: []};
        Policy.rememberWeb(cache, "rainbow", webData("rainbow", "ready"), 1000);
        Policy.rememberWeb(cache, "missing", webData("missing", "empty"), 1000);
        Policy.rememberWeb(cache, "offline", webData("offline", "unavailable"), 1000);
        compare(Policy.cachedWeb(cache, "rainbow", 300999).results[0].title, "rainbow");
        compare(Policy.cachedWeb(cache, "rainbow", 301000), null);
        compare(Policy.cachedWeb(cache, "missing", 301000), null);
        compare(Policy.cachedWeb(cache, "offline", 301000), null);
        Policy.rememberWeb(cache, "offline", webData("offline", "unavailable"), 400000);
        verify(Policy.cachedWeb(cache, "offline", 429999) !== null);
        compare(Policy.cachedWeb(cache, "offline", 430000), null);
    }

    function test_web_cache_is_bounded_and_evicts_least_recently_used() {
        const cache = {entries: []};
        for (let i = 0; i < 32; i++) Policy.rememberWeb(cache, "query " + i, webData("query " + i, "ready"), 1000);
        verify(Policy.cachedWeb(cache, "query 0", 1100) !== null);
        Policy.rememberWeb(cache, "query 32", webData("query 32", "ready"), 1200);
        compare(cache.entries.length, 32);
        compare(Policy.cachedWeb(cache, "query 1", 1300), null);
        verify(Policy.cachedWeb(cache, "query 0", 1300) !== null);
        verify(Policy.cachedWeb(cache, "query 32", 1300) !== null);
        Policy.rememberWeb(cache, "query 0", webData("new result", "ready"), 1400);
        compare(cache.entries.length, 32);
        compare(Policy.cachedWeb(cache, "query 0", 1500).results[0].title, "new result");
    }

    function test_web_cache_excludes_loading_local_answers_and_direct_urls() {
        const cache = {entries: []};
        Policy.rememberWeb(cache, "loading", {intent: "web", results: [{kind: "web", loading: true}]}, 1000);
        Policy.rememberWeb(cache, "2+2", {intent: "answer", results: [{kind: "copy", value: "4"}]}, 1000);
        Policy.rememberWeb(cache, "example.com", {intent: "web", results: [{kind: "url", value: "https://example.com"}]}, 1000);
        compare(cache.entries.length, 0);
    }

    function test_app_and_file_queries_do_not_wait_for_web_debounce() {
        compare(Policy.typingDelay("who app", true), 90);
        compare(Policy.typingDelay("who app", false), 400);
        compare(Policy.typingDelay("web settings", true), 400);
        compare(Policy.typingDelay("files: why?", false), 220);
        compare(Policy.typingDelay("600gbp to aed", false), 90);
    }
}
