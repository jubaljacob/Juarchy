.pragma library

// Spotlight uses deliberate names and aliases, independently of the menu's fuzzy filter.
var destinations = [
    {title: "Settings", detail: "Juarchy desktop settings", page: "", aliases: ["settings", "preferences", "settings panel", "desktop settings", "system settings", "juarchy settings"]},
    {title: "Audio settings", detail: "Settings → Audio", page: "audio", aliases: ["audio", "sound", "volume", "audio settings", "sound settings", "volume settings"]},
    {title: "Wallpaper & style", detail: "Settings → Wallpaper & style", page: "appearance", aliases: ["wallpaper", "wallpapers", "themes", "theme", "appearance", "colours", "colors", "fonts", "wallpaper settings", "appearance settings"]},
    {title: "Network settings", detail: "Settings → Network", page: "network", aliases: ["network", "wifi", "wi fi", "ethernet", "vpn", "network settings", "wifi settings"]},
    {title: "Bluetooth settings", detail: "Settings → Connected devices", page: "bluetooth", aliases: ["bluetooth", "connected devices", "bluetooth settings"]},
    {title: "Notification settings", detail: "Settings → Services → Notifications", page: "services", subPage: 1, aliases: ["notification", "notifications", "notification settings", "notification history", "notifications settings"]},
    {title: "Taskbar settings", detail: "Settings → Panels → Taskbar", page: "panels", subPage: 2, aliases: ["taskbar", "bar settings", "taskbar settings", "workspaces"]},
    {title: "Panel settings", detail: "Settings → Panels", page: "panels", aliases: ["panels", "panel settings", "desktop panels"]},
    {title: "App preferences", detail: "Settings → Apps", page: "apps", aliases: ["default apps", "app preferences", "app settings", "favourite apps", "favorite apps"]},
    {title: "Services & media privacy", detail: "Settings → Services", page: "services", aliases: ["services", "media privacy", "music artwork", "visualisers", "visualizers", "services settings"]},
    {title: "Language & region", detail: "Settings → Language & region", page: "region", aliases: ["language", "region", "weather location", "language settings", "region settings"]},
    {title: "System updates", detail: "Settings → Updates", page: "updates", aliases: ["updates", "system updates", "update settings"]}
];

function normalise(text) {
    return String(text || "").replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase()
        .replace(/[\s_.\-]+/g, " ").trim();
}

function nameScore(name, query) {
    const full = normalise(name), needle = normalise(query);
    if (!needle) return 0;
    if (full === needle) return 1000;
    const words = full.split(" "), terms = needle.split(" ");
    if (terms.every(term => words.indexOf(term) !== -1))
        return (" " + full + " ").indexOf(" " + needle + " ") !== -1 ? 900 : 850;
    if (needle.length < 2) return 0;
    if (terms.every(term => words.some(word => word.indexOf(term) === 0))) return 750;
    return 0;
}

function settingsRows(query) {
    const matches = destinations.map(destination => {
        const score = Math.max.apply(null, destination.aliases.map(alias => nameScore(alias, query)));
        return Object.assign({kind: "settings", value: destination.page, icon: "settings", score: score}, destination);
    }).filter(row => row.score > 0).sort(compareNavigation);
    // A request for the whole Settings panel does not need suggestions for every section.
    const main = matches.find(row => row.page === "" && row.score === 1000);
    return main ? [main] : matches;
}

function compareNavigation(a, b) {
    // Exact destination aliases win over partial names like "Displays Settings".
    return b.score - a.score || (a.kind === "app" ? 0 : 1) - (b.kind === "app" ? 0 : 1)
        || a.title.localeCompare(b.title);
}

function appRows(entries, query) {
    return entries.map(app => ({kind: "app", title: app.name, detail: "Application", app: app,
        value: app.id, icon: "apps", appIcon: app.icon || "", score: nameScore(app.name, query)}))
        .filter(row => row.score > 0).sort(compareNavigation);
}

function explicitContext(query) {
    return /^(web|search online|search the web|google|duckduckgo)\s*:?\s+|^files?\s*:/i.test(query);
}

function isWebQuery(query) {
    const q = String(query || "").trim();
    return /^(web|search online|search the web|google|duckduckgo)\s*:?\s+|^(what|who|where|when|why|how|which|is|are|can|does|do)\s+\S+|^(tell me about|define|definition of|search for|look up)\s+\S+/i.test(q) || /\?$/.test(q);
}

function rowHeight(row) {
    return row?.role === "web-link" ? 48 : 62;
}

function typingDelay(query, localMatch) {
    if (/^files?\s*:/i.test(String(query).trim())) return 220;
    if (localMatch && !explicitContext(query)) return 90;
    return isWebQuery(query) ? 400 : 90;
}

function cachedWeb(cache, query, now) {
    if (!cache || !cache.entries) return null;
    cache.entries = cache.entries.filter(entry => entry.expires > now);
    const key = String(query).trim();
    const index = cache.entries.findIndex(entry => entry.key === key);
    if (index < 0) return null;
    const entry = cache.entries.splice(index, 1)[0];
    cache.entries.push(entry);
    const data = Object.assign({}, entry.data, {query: query});
    if (data.results[0].previewState === "ready")
        data.status = "Wikipedia · cached preview • Enter opens the selected result";
    return data;
}

function rememberWeb(cache, query, data, now) {
    const state = data.results?.[0]?.previewState;
    if (!cache || data.intent !== "web" || ["ready", "empty", "unavailable"].indexOf(state) < 0) return;
    const key = String(query).trim();
    const entries = (cache.entries || []).filter(entry => entry.expires > now && entry.key !== key);
    entries.push({key: key, data: data, expires: now + (state === "ready" ? 300000 : 30000)});
    cache.entries = entries.slice(-32);
}

function rows(mode, query, apps, extras, intent) {
    if (mode === "search") {
        if (intent === "web") return extras.slice(0, 3);
        if (intent === "files") return extras.slice(0, 40);
        const answers = extras.filter(row => row.kind === "copy" || row.kind === "info");
        if (answers.length) return answers.slice(0, 5);
        const navigation = explicitContext(query) ? [] : settingsRows(query).concat(apps).sort(compareNavigation).slice(0, 3);
        const files = extras.filter(row => row.kind === "file")
            .filter(row => !navigation.length || row.score >= 950).slice(0, navigation.length ? 2 : 5);
        if (navigation.length || files.length) return navigation.concat(files).slice(0, 5);
        return extras.filter(row => row.kind === "url" || row.kind === "lookup").slice(0, 5);
    }
    if (mode === "apps") return settingsRows(query).concat(apps).sort(compareNavigation).slice(0, 30);
    if (mode !== "all") return extras;
    const answers = extras.filter(row => row.kind === "copy");
    if (answers.length) return answers.slice(0, 5);
    const navigation = settingsRows(query).concat(apps).sort(compareNavigation).slice(0, 3);
    const files = extras.filter(row => row.kind === "file").filter(row => !navigation.length || row.score >= 950).slice(0, navigation.length ? 2 : 5);
    const local = answers.concat(navigation, files).slice(0, 5);
    // Keep broad searches and external lookups accessible without filling the result list.
    const conversion = extras.filter(row => row.kind === "mode" && row.value === "currency");
    return conversion.concat(local).slice(0, 5);
}

function identity(row) {
    return row ? row.kind + ":" + String(row.value) : "";
}

function escapeHtml(text) {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function highlightTitle(title, query) {
    const terms = normalise(query).split(" ").filter(term => term.length > 0);
    return String(title).split(/([\s_.\-]+)/).map(part => {
        const escaped = escapeHtml(part);
        return terms.some(term => normalise(part).indexOf(term) >= 0) ? "<b>" + escaped + "</b>" : escaped;
    }).join("");
}
