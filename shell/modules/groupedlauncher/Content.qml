pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Widgets
import Caelestia.Config
import qs.components
import qs.components.controls
import qs.services
import qs.modules.launcher.services
import "MenuModel.js" as MenuModel

Item {
    id: root

    required property ScreenState screenState
    required property var panels
    required property real maxHeight
    property real maxWidth: 380
    property var menu: ({title: "Menu", items: []})
    property string loadError: ""
    property string activePath: ""
    property var history: []
    property alias query: search.text
    readonly property int padding: Tokens.padding.large
    readonly property int rowHeight: 44
    readonly property var tree: MenuModel.build(menu, Apps.search(""))
    readonly property var activeMenu: MenuModel.find(tree, activePath) || tree
    readonly property var rows: MenuModel.visible(tree, activePath, search.text)
    readonly property int desiredRows: Math.min(Math.max(rows.length, 1), 9)

    implicitWidth: Math.min(380, maxWidth)
    implicitHeight: Math.min(maxHeight, header.height + search.implicitHeight + padding * 3 + Tokens.spacing.small
                             + desiredRows * (rowHeight + list.spacing) - list.spacing)

    function readMenu(text) {
        try {
            const data = JSON.parse(text);
            if (!Array.isArray(data.items) || data.items.length === 0)
                throw new Error("No menu groups found");
            root.menu = data;
            root.loadError = "";
            root.activePath = "";
            root.history = [];
            applyRequest();
        } catch (error) {
            root.loadError = "Cannot load menu.json";
            console.warn("Grouped launcher:", error);
        }
    }

    function applyRequest() {
        if (!menu.items.length || !MenuRequest.pending || MenuRequest.targetState !== screenState) return;
        const selected = MenuModel.section(tree, MenuRequest.section);
        MenuRequest.pending = false;
        if (!selected || selected.kind !== "group") return;
        activePath = selected.path;
        history = selected.path ? [{path: "", query: "", index: 0}] : [];
        search.clear();
        search.forceActiveFocus();
    }

    function removeSelected() {
        const row = rows[list.currentIndex];
        if (!row || row.kind !== "app") return false;
        root.screenState.launcher = false;
        Quickshell.execDetached([Quickshell.env("HOME") + "/.local/bin/jubal-desktop-tools", "uninstall", row.app.id]);
        return true;
    }

    function moveSelection(amount) {
        if (!rows.length) return;
        list.currentIndex = (list.currentIndex + amount + rows.length) % rows.length;
        list.positionViewAtIndex(list.currentIndex, ListView.Contain);
    }

    function back() {
        if (!history.length) return;
        const previous = history[history.length - 1];
        history = history.slice(0, -1);
        activePath = previous.path;
        search.text = previous.query;
        Qt.callLater(() => {
            list.currentIndex = Math.min(previous.index, rows.length - 1);
            list.positionViewAtIndex(list.currentIndex, ListView.Contain);
            search.forceActiveFocus();
        });
    }

    function activate(index) {
        const row = rows[index];
        if (!row) return;
        if (row.kind === "group") {
            history = history.concat([{path: activePath, query: search.text, index: index}]);
            activePath = row.path;
            search.text = "";
            search.forceActiveFocus();
        } else {
            root.screenState.launcher = false;
            if (row.kind === "app") {
                Apps.launch(row.app);
            } else {
                Quickshell.execDetached([
                    Quickshell.env("HOME") + "/.local/bin/jubal-launcher",
                    "--run-action", row.path, "--expected-action", JSON.stringify(row.entry)
                ]);
            }
        }
    }

    onRowsChanged: {
        list.currentIndex = rows.length ? 0 : -1;
        list.positionViewAtBeginning();
    }

    FileView {
        id: menuFile
        path: (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/jubal-launcher/menu.json"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: root.readMenu(text())
        onLoadFailed: root.loadError = "Cannot read menu.json"
    }

    Item {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: root.padding
        height: 28

        IconButton {
            id: backButton
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            icon: "arrow_back"
            type: IconButton.Text
            visible: root.history.length > 0
            onClicked: root.back()
        }

        StyledText {
            anchors.left: parent.left
            anchors.leftMargin: backButton.visible ? backButton.width + Tokens.spacing.small : 4
            anchors.right: closeButton.left
            anchors.verticalCenter: parent.verticalCenter
            text: root.activeMenu.label
            font: Tokens.font.body.medium
            color: Colours.palette.m3primary
            elide: Text.ElideRight
        }

        IconButton {
            id: closeButton
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            icon: "close"
            type: IconButton.Text
            onClicked: root.screenState.launcher = false
        }
    }

    ListView {
        id: list
        objectName: "groupedMenuList"
        anchors.top: header.bottom
        anchors.bottom: search.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: root.padding
        anchors.rightMargin: root.padding
        anchors.topMargin: Tokens.spacing.small
        anchors.bottomMargin: root.padding
        spacing: 3
        clip: true
        model: root.rows
        boundsBehavior: Flickable.StopAtBounds
        highlightMoveDuration: 100
        highlight: Rectangle {
            radius: Tokens.rounding.large
            color: Qt.alpha(Colours.palette.m3primary, 0.14)
        }

        delegate: Item {
            id: row
            required property var modelData
            required property int index
            readonly property bool hasAppIcon: modelData.kind === "app" && Quickshell.hasThemeIcon(modelData.icon)
            width: list.width
            height: root.rowHeight

            MaterialIcon {
                id: rowIcon
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                width: 24
                horizontalAlignment: Text.AlignHCenter
                visible: !row.hasAppIcon
                text: row.modelData.kind === "app" ? "apps" : MenuModel.icon(row.modelData)
                color: row.ListView.isCurrentItem ? Colours.palette.m3primary : Colours.palette.m3onSurfaceVariant
            }

            IconImage {
                anchors.centerIn: rowIcon
                implicitSize: 24
                visible: row.hasAppIcon
                source: visible ? Quickshell.iconPath(row.modelData.icon, "application-x-executable") : ""
                asynchronous: true
            }

            Column {
                anchors.left: rowIcon.right
                anchors.right: arrow.left
                anchors.leftMargin: 12
                anchors.rightMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                spacing: 1

                StyledText {
                    width: parent.width
                    text: row.modelData.label
                    font: Tokens.font.body.medium
                    elide: Text.ElideRight
                }

                StyledText {
                    width: parent.width
                    visible: root.query.length > 0 || !!row.modelData.entry?.shortcut
                    text: row.modelData.entry?.shortcut || row.modelData.detail
                    font: Tokens.font.body.small
                    color: Colours.palette.m3outline
                    elide: Text.ElideRight
                }
            }

            MaterialIcon {
                id: arrow
                anchors.right: parent.right
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                width: 20
                text: row.modelData.kind === "group" ? "chevron_right" : ""
                color: Colours.palette.m3outline
            }

            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onPositionChanged: list.currentIndex = row.index
                onClicked: root.activate(row.index)
            }

            IconButton {
                anchors.right: parent.right
                anchors.rightMargin: 4
                anchors.verticalCenter: parent.verticalCenter
                icon: "delete"
                type: IconButton.Text
                visible: row.modelData.kind === "app" && row.ListView.isCurrentItem
                Accessible.name: "Uninstall " + row.modelData.label
                onClicked: {
                    list.currentIndex = row.index;
                    root.removeSelected();
                }
            }
        }

        StyledScrollBar.vertical: StyledScrollBar { flickable: list }
    }

    StyledText {
        anchors.centerIn: list
        visible: root.rows.length === 0 || root.loadError.length > 0
        text: root.loadError || (root.query ? "No matches" : "Loading menu…")
        color: Colours.palette.m3outline
    }

    SearchBar {
        id: search
        objectName: "launcherSearch"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: root.padding
        anchors.bottomMargin: Math.max(0, root.padding - Config.border.thickness)
        topPadding: Tokens.padding.medium
        bottomPadding: Tokens.padding.medium
        placeholderText: list.currentItem?.modelData.kind === "app" ? "Search apps · Delete to uninstall" : (root.activePath ? "Search " + root.activeMenu.label.toLowerCase() : "Search apps and actions")
        onAccepted: root.activate(list.currentIndex)
        Keys.onUpPressed: root.moveSelection(-1)
        Keys.onDownPressed: root.moveSelection(1)
        Keys.onEscapePressed: {
            if (text) clear();
            else if (root.history.length) root.back();
            else root.screenState.launcher = false;
        }
        Keys.onPressed: event => {
            if (event.key === Qt.Key_Delete && event.modifiers === Qt.NoModifier && !event.isAutoRepeat) {
                event.accepted = root.removeSelected();
            } else if ((event.key === Qt.Key_Backspace || event.key === Qt.Key_Left) && !text) {
                root.back();
                event.accepted = true;
            } else if (event.key === Qt.Key_Right && !text) {
                root.activate(list.currentIndex);
                event.accepted = true;
            } else if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
                root.moveSelection(event.key === Qt.Key_Backtab || (event.modifiers & Qt.ShiftModifier) ? -1 : 1);
                event.accepted = true;
            } else if (event.modifiers & Qt.ControlModifier) {
                if (event.key === Qt.Key_J || event.key === Qt.Key_N) {
                    root.moveSelection(1);
                    event.accepted = true;
                } else if (event.key === Qt.Key_K || event.key === Qt.Key_P) {
                    root.moveSelection(-1);
                    event.accepted = true;
                }
            }
        }
        Component.onCompleted: forceActiveFocus()
    }

    Connections {
        target: root.screenState
        function onLauncherChanged() {
            if (root.screenState.launcher) {
                root.activePath = "";
                root.history = [];
                search.clear();
                search.forceActiveFocus();
                root.applyRequest();
            }
        }
    }

    Connections {
        target: MenuRequest
        function onRevisionChanged() {
            if (root.screenState.launcher) root.applyRequest();
        }
    }
}
