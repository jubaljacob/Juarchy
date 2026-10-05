// Pure model shared by the native drawer and its navigation/search tests.

function build(menu, applications) {
    function convert(entry, indices, parents) {
        var node = {
            label: entry.label,
            path: indices.join('.'),
            detail: parents.join(' › '),
            kind: entry.items ? 'group' : 'action',
            entry: entry,
            children: []
        };
        if (entry.items) {
            node.children = entry.items.map(function(child, index) {
                return convert(child, indices.concat(index), parents.concat(entry.label));
            });
            if (entry.applications) {
                var apps = applications.filter(function(app) {
                    return app.id !== 'jubal-launcher' && app.id !== 'jubal-launcher.desktop';
                }).map(function(app) {
                    return {
                        label: app.name,
                        detail: parents.concat(entry.label).join(' › '),
                        path: 'app:' + app.id,
                        kind: 'app',
                        app: app,
                        icon: app.icon || '',
                        keywords: [app.genericName || '', app.comment || '', app.id,
                                   (app.keywords || []).join(' ')].join(' '),
                        children: []
                    };
                });
                apps.sort(function(a, b) { return a.label.localeCompare(b.label); });
                node.children = node.children.concat(apps);
            }
        }
        return node;
    }
    return {
        label: menu.title || 'Menu', path: '', kind: 'group', detail: '',
        children: (menu.items || []).map(function(entry, index) { return convert(entry, [index], []); })
    };
}

function find(root, path) {
    if (root.path === path) return root;
    for (var i = 0; i < root.children.length; i++) {
        var match = find(root.children[i], path);
        if (match) return match;
    }
    return null;
}

function section(root, name) {
    if (!name) return root;
    return root.children.find(function(node) {
        return node.label.toLowerCase() === name.toLowerCase();
    }) || null;
}

function score(node, query) {
    var name = node.label.toLowerCase();
    var needle = query.toLowerCase().trim();
    if (name === needle) return 0;
    if (name.indexOf(needle) === 0) return 10;
    var words = name.split(/[\s._-]+/);
    if (words.some(function(word) { return word === needle; })) return 12;
    if (words.some(function(word) { return word.indexOf(needle) === 0; })) return 18;
    if (name.indexOf(needle) >= 0) return 25;
    var haystack = name + ' ' + (node.keywords || '').toLowerCase();
    var terms = needle.split(/\s+/);
    if (terms.every(function(term) { return haystack.indexOf(term) >= 0; })) return 40;
    // Skipped-letter matching is useful for quick app searches (e.g. "chrmi").
    var cursor = 0;
    for (var i = 0; i < needle.length; i++) {
        if (needle[i] === ' ') continue;
        cursor = name.indexOf(needle[i], cursor);
        if (cursor < 0) return -1;
        cursor++;
    }
    return 60 + cursor - needle.length;
}

function visible(root, path, query) {
    var active = find(root, path) || root;
    if (!query.trim()) return active.children;
    var matches = [];
    function descend(parent) {
        parent.children.forEach(function(node) {
            var rank = score(node, query);
            if (rank >= 0) matches.push({node: node, rank: rank - (node.kind === 'app' ? 1 : 0)});
            if (node.kind === 'group') descend(node);
        });
    }
    descend(active);
    matches.sort(function(a, b) { return a.rank - b.rank || a.node.label.localeCompare(b.node.label); });
    return matches.map(function(match) { return match.node; });
}

function icon(node) {
    var icons = {Apps: 'apps', Triggers: 'bolt', Style: 'palette', Setup: 'tune',
                 Install: 'download', Remove: 'delete', Update: 'system_update',
                 Snaps: 'history', About: 'info', System: 'computer', Files: 'folder'};
    if (icons[node.label]) return icons[node.label];
    if (node.kind === 'group' || (node.entry && node.entry.path)) return 'folder';
    return 'chevron_right';
}

if (typeof module !== 'undefined') module.exports = {build: build, find: find, section: section, visible: visible, score: score};
