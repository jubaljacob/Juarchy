pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import Quickshell.Widgets
import Caelestia.Config
import qs.components
import qs.components.controls
import qs.services
import qs.modules.launcher.services
import qs.modules.nexus
import "SearchPolicy.js" as SearchPolicy

Rectangle {
    id: root
    signal close()
    property alias query: search.text
    readonly property string mode: "search"
    property string intent: "search"
    property var appRows: []
    property var extraRows: []
    property var webCache: ({entries: []})
    property string status: "Search apps, settings and files, ask a question, or convert"
    property bool previewing: false
    property bool pending: false
    property bool workerCancelled: false
    readonly property bool expanded: query.trim().length > 0
    readonly property var rows: SearchPolicy.rows(mode, query, appRows, extraRows, intent)
    readonly property var selected: rows[list.currentIndex] || null
    readonly property string webSearchUrl: rows.find(r => r.searchUrl)?.searchUrl || ""
    readonly property bool localMatch: appRows.length > 0 || SearchPolicy.settingsRows(query).length > 0
    property string selectedIdentity: ""
    property bool keepSelection: false
    readonly property string helper: Quickshell.env("HOME") + "/.local/bin/juarchy-spotlight"
    property string launchedQuery: ""
    property string launchedMode: ""
    readonly property int contentMargin: 20
    readonly property int sectionGap: 12
    readonly property int resultHeight: 62
    readonly property int resultSpacing: 5
    readonly property int visibleResultCount: Math.min(Math.max(rows.length, 1), 5)
    // Web cards size to their bounded text; include every related link in the viewport.
    readonly property real preferredResultsHeight: previewing ? 320
        : rows.some(r => r.kind === "web") ? Math.max(104, list.contentHeight)
        : rows.length ? rows.slice(0, visibleResultCount).reduce((total, r) => total + SearchPolicy.rowHeight(r), 0)
            + (visibleResultCount - 1) * resultSpacing : resultHeight

    color: Qt.alpha(Colours.palette.m3surfaceContainer, 0.72)
    radius: 24
    border.width: 1
    border.color: Qt.alpha(Colours.palette.m3outlineVariant, 0.6)
    implicitHeight: contentMargin * 2 + header.implicitHeight
        + (expanded ? sectionGap * 2 + preferredResultsHeight + footer.implicitHeight : 0)
    clip: true

    // Contain pointer events so clicking the card doesn't dismiss it.
    MouseArea { anchors.fill: parent }

    function refresh() {
        if (worker.running) {
            workerCancelled = true;
            pending = true;
            worker.signal(15);
        }
        previewing = false;
        intent = "search";
        extraRows = [];
        keepSelection = false;
        appRows = search.text.trim() && !SearchPolicy.explicitContext(search.text)
            ? SearchPolicy.appRows(Apps.list.map(a => a.entry), search.text) : [];
        const cached = !localMatch || SearchPolicy.explicitContext(query)
            ? SearchPolicy.cachedWeb(webCache, query, Date.now()) : null;
        if (cached) { applyResults(cached, true); debounce.stop(); return; }
        status = appRows.length ? "Apps • Enter opens the selected result" : "Searching…";
        debounce.restart();
    }

    function request() {
        if (!expanded) { status = "Search apps, settings and files, ask a question, or convert"; return; }
        if (worker.running) { pending = true; return; } // Wait only for the cancelled helper to exit.
        pending = false;
        workerCancelled = false;
        launchedQuery = search.text;
        launchedMode = mode;
        const cached = !localMatch || SearchPolicy.explicitContext(launchedQuery)
            ? SearchPolicy.cachedWeb(webCache, launchedQuery, Date.now()) : null;
        if (cached) { applyResults(cached, true); return; }
        worker.command = [helper, mode, "--stream"].concat(localMatch ? ["--local-only"] : []).concat(["--", launchedQuery]);
        worker.receivedResults = false;
        worker.running = true;
    }

    function applyResults(data, cached) {
        if ((!cached && workerCancelled) || data.query !== search.text || data.mode !== mode) return;
        selectedIdentity = SearchPolicy.identity(selected);
        keepSelection = true;
        intent = data.intent || "search";
        extraRows = data.results;
        status = rows.some(r => r.kind === "app" || r.kind === "settings")
            ? "Apps and Settings • Enter opens the selected result"
            : data.intent !== "web" && rows.length === 1 && rows[0].kind === "url"
                ? "Web search • Enter opens your browser" : data.status;
        if (!cached) SearchPolicy.rememberWeb(webCache, search.text, data, Date.now());
    }

    function move(amount) {
        if (!rows.length) return;
        list.currentIndex = (list.currentIndex + amount + rows.length) % rows.length;
        list.positionViewAtIndex(list.currentIndex, ListView.Contain);
    }

    function openWebSearch() {
        if (!webSearchUrl) return;
        Quickshell.execDetached(["xdg-open", webSearchUrl]);
        root.close();
    }

    function activate(reveal) {
        const r = selected;
        if (!r) return;
        if (reveal && webSearchUrl) { openWebSearch(); return; }
        if (r.kind === "info") return;
        if (r.kind === "lookup") { search.text = "web " + r.value; search.forceActiveFocus(); return; }
        if (r.kind === "copy") {
            clipboard.command = ["wl-copy", "--", r.value];
            clipboard.running = true;
            status = "Copied " + r.value;
            return;
        }
        if (r.kind === "app") Apps.launch(r.app);
        else if (r.kind === "settings") WindowFactory.openPage(r.page, r.subPage === undefined ? -1 : r.subPage);
        else if (reveal && r.kind === "file") Quickshell.execDetached(["xdg-open", r.value.slice(0, r.value.lastIndexOf("/"))]);
        else Quickshell.execDetached(["xdg-open", r.value]);
        root.close();
    }

    onRowsChanged: {
        const previous = keepSelection ? rows.findIndex(r => SearchPolicy.identity(r) === selectedIdentity) : -1;
        list.currentIndex = previous >= 0 ? previous : rows.length ? 0 : -1;
    }
    Component.onCompleted: { search.forceActiveFocus(); refresh(); indexer.running = true; }

    Timer { id: debounce; interval: SearchPolicy.typingDelay(root.query, root.localMatch); onTriggered: root.request() }
    Process {
        id: indexer
        property bool updated: false
        command: [root.helper, "index"]
        stdout: SplitParser {
            onRead: dataLine => {
                try { indexer.updated = JSON.parse(dataLine).indexUpdated === true; } catch (error) {}
            }
        }
        onExited: {
            if (updated) root.webCache.entries = [];
            if (updated && root.expanded && (!SearchPolicy.isWebQuery(root.query) || /^files?\s*:/i.test(root.query))
                && ["web", "answer", "conversion"].indexOf(root.intent) < 0) debounce.restart();
        }
    }
    Process {
        id: worker
        property bool receivedResults: false
        stdout: SplitParser {
            onRead: dataLine => {
                try {
                    if (root.workerCancelled || !dataLine.trim()) return;
                    const data = JSON.parse(dataLine);
                    if (data.query !== search.text || data.mode !== root.mode) return;
                    if (!Array.isArray(data.results)) throw new Error("Invalid search response");
                    worker.receivedResults = true;
                    root.applyResults(data, false);
                } catch (error) { if (!root.workerCancelled) root.status = "Search helper unavailable"; }
            }
        }
        onExited: {
            if (!root.workerCancelled && !receivedResults && root.expanded
                && root.launchedQuery === search.text) root.status = "Search helper unavailable";
            if ((root.pending || root.launchedQuery !== search.text || root.launchedMode !== root.mode) && !debounce.running) root.request();
        }
    }
    Process { id: clipboard }

    Column {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: root.contentMargin
        spacing: 12
        SearchBar {
            id: search
            objectName: "spotlightSearch"
            width: parent.width
            maximumLength: 300
            bg.color: Qt.alpha(Colours.palette.m3surfaceContainer, 0.38)
            placeholderText: "Search, ask a question, calculate or convert…"
            onTextChanged: root.refresh()
            onAccepted: root.activate(false)
            Keys.onEscapePressed: { if (root.previewing) root.previewing = false; else root.close(); }
            Keys.onDownPressed: root.move(1)
            Keys.onUpPressed: root.move(-1)
            Keys.onPressed: event => {
                if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_Return) {
                    root.activate(true); event.accepted = true;
                } else if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_W && root.query.trim()) {
                    if (!/^web\s/i.test(search.text)) search.text = "web " + search.text;
                    event.accepted = true;
                } else if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_Space && root.selected?.kind === "file") {
                    root.previewing = !root.previewing; event.accepted = true;
                }
            }
        }
    }

    ListView {
        id: list
        objectName: "spotlightResults"
        visible: root.expanded
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: footer.top
        anchors.margins: root.contentMargin
        anchors.topMargin: root.sectionGap
        anchors.bottomMargin: root.sectionGap
        spacing: root.resultSpacing
        clip: true
        model: root.rows
        delegate: Rectangle {
            id: item
            required property var modelData
            required property int index
            width: list.width
            height: modelData.kind === "web" ? Math.max(104, webCard.implicitHeight + 24) : SearchPolicy.rowHeight(modelData)
            radius: 12
            color: ListView.isCurrentItem ? Qt.alpha(Colours.palette.m3secondaryContainer, 0.48) : "transparent"
            Item {
                id: iconSlot
                visible: item.modelData.kind !== "web"
                anchors.left: parent.left; anchors.leftMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                width: 40
                height: 32

                MaterialIcon {
                    anchors.centerIn: parent
                    visible: appIconImage.status !== Image.Ready
                    text: item.modelData.icon || ({url: "travel_explore", copy: "calculate", lookup: "travel_explore", info: "info"})[item.modelData.kind] || "description"
                    color: Colours.palette.m3primary
                }

                IconImage {
                    id: appIconImage
                    objectName: "spotlightAppIcon"
                    anchors.centerIn: parent
                    implicitSize: 32
                    asynchronous: true
                    visible: status === Image.Ready
                    source: item.modelData.kind === "app" && item.modelData.appIcon
                        ? Quickshell.iconPath(item.modelData.appIcon, true) : ""
                }
            }
            Column {
                visible: item.modelData.kind !== "web"
                anchors.left: parent.left; anchors.leftMargin: 62
                anchors.right: parent.right; anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4
                StyledText {
                    width: parent.width
                    text: SearchPolicy.highlightTitle(item.modelData.title, root.query)
                    textFormat: Text.StyledText
                    elide: Text.ElideRight
                    font.pixelSize: item.modelData.role === "web-link" ? 14 : 16
                }
                StyledText { width: parent.width; text: item.modelData.detail; elide: Text.ElideRight; font.pixelSize: 12; color: Colours.palette.m3onSurfaceVariant }
            }
            Column {
                id: webCard
                objectName: "spotlightWebCard"
                visible: item.modelData.kind === "web"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                anchors.topMargin: 12
                spacing: 6
                Row {
                    width: parent.width
                    height: 20
                    spacing: 6
                    MaterialIcon { anchors.verticalCenter: parent.verticalCenter; text: "travel_explore"; font.pixelSize: 16; color: Colours.palette.m3onSurfaceVariant }
                    StyledText { anchors.verticalCenter: parent.verticalCenter; text: "Wikipedia · " + (item.modelData.loading ? "searching" : "article preview"); font.pixelSize: 11; color: Colours.palette.m3onSurfaceVariant }
                }
                StyledText {
                    objectName: "spotlightWebTitle"
                    width: parent.width
                    text: item.modelData.kind === "web" ? item.modelData.title : ""
                    font.pixelSize: 17
                    font.weight: Font.DemiBold
                    wrapMode: Text.Wrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                    textFormat: Text.PlainText
                }
                StyledText {
                    objectName: "spotlightWebSummary"
                    width: parent.width
                    text: item.modelData.summary || ""
                    font.pixelSize: 13
                    lineHeight: 1.15
                    wrapMode: Text.Wrap
                    maximumLineCount: 3
                    elide: Text.ElideRight
                    textFormat: Text.PlainText
                    color: Colours.palette.m3onSurfaceVariant
                }
            }
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                onEntered: list.currentIndex = item.index
                onClicked: { list.currentIndex = item.index; root.activate(false); }
            }
        }
        StyledText {
            anchors.centerIn: parent
            visible: !root.rows.length
            text: root.status === "Searching…" ? root.status : "No matching results"
            horizontalAlignment: Text.AlignHCenter
            color: Colours.palette.m3onSurfaceVariant
        }
    }

    Column {
        id: footer
        visible: root.expanded
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: root.contentMargin
        spacing: 6
        Row {
            width: parent.width
            spacing: 12
            StyledText {
                width: parent.width - (fullWebSearch.visible ? fullWebSearch.implicitWidth + parent.spacing : 0)
                text: root.status
                elide: Text.ElideRight
                font.pixelSize: 12
                color: Colours.palette.m3primary
            }
            StyledText {
                id: fullWebSearch
                visible: root.webSearchUrl.length > 0
                text: "Search web ↗"
                font.pixelSize: 12
                color: Colours.palette.m3primary
                MouseArea { anchors.fill: parent; onClicked: root.openWebSearch() }
            }
        }
        StyledText {
            text: root.webSearchUrl ? "↑↓ Select   Enter " + (root.selected?.loading ? "Search web" : "Open result") + "   Ctrl+Enter Search web   Esc Close"
                : "↑↓ Select   Enter Open / Copy   Ctrl+Enter Folder   Ctrl+Space Preview   Ctrl+W Web   Esc Close"
            font.pixelSize: 11
            color: Colours.palette.m3onSurfaceVariant
        }
    }

    Rectangle {
        anchors.fill: list
        visible: root.previewing && root.selected?.kind === "file"
        color: Qt.alpha(Colours.palette.m3surfaceContainer, 0.5)
        radius: 12
        Image {
            anchors.fill: parent
            anchors.margins: 24
            source: root.previewing && root.selected?.kind === "file" && /\.(png|jpe?g|webp|gif|bmp|svg)$/i.test(root.selected.value) ? "file://" + root.selected.value.split("/").map(p => encodeURIComponent(p)).join("/") : ""
            fillMode: Image.PreserveAspectFit
            asynchronous: true
        }
        StyledText {
            anchors.centerIn: parent
            width: parent.width - 40
            text: root.selected ? root.selected.title + "\n\n" + root.selected.value + "\n\nEnter opens this file • Ctrl+Space returns to results" : ""
            visible: !/\.(png|jpe?g|webp|gif|bmp|svg)$/i.test(root.selected?.value || "")
            wrapMode: Text.WrapAnywhere
            horizontalAlignment: Text.AlignHCenter
        }
    }
}
