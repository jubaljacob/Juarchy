pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Caelestia.Config
import qs.components
import qs.services
import qs.modules.nexus.common

PageBase {
    id: root
    title: "Updates"
    property string helperPath: Quickshell.env("HOME") + "/.local/bin/jubal-arch-updates"
    property var packages: []
    property double checkedAt: 0
    property string errorMessage: ""
    readonly property bool busy: checker.running
    readonly property string statusText: busy ? "Checking Arch repositories…" : errorMessage ? "Could not check for updates" : !checkedAt ? "Not checked yet" : packages.length ? packages.length + (packages.length === 1 ? " update available" : " updates available") : "Your Arch packages are up to date"

    function checkUpdates(force: bool): void {
        if (busy) return;
        errorMessage = "";
        checker.command = force ? [helperPath, "--refresh"] : [helperPath];
        checker.running = true;
    }
    function acceptResult(text: string, code: int): void {
        try {
            const result = JSON.parse(text);
            if (code !== 0 || !result.success) {
                errorMessage = result.message || "Update check failed. Try again.";
                return;
            }
            packages = result.packages;
            checkedAt = result.checkedAt;
        } catch (error) {
            errorMessage = "Could not read the update result. Try again.";
        }
    }
    Component.onCompleted: checkUpdates(false)

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: Tokens.spacing.extraSmall / 2

        Process {
            id: checker
            stdout: StdioCollector { id: output }
            onExited: code => Qt.callLater(() => root.acceptResult(output.text, code))
        }
        SectionHeader { first: true; text: "Arch Linux" }
        InfoRow {
            first: true
            last: true
            icon: root.busy ? "sync" : root.errorMessage ? "error" : root.packages.length ? "system_update" : "check_circle"
            label: root.statusText
            subtext: root.checkedAt ? "Last successful check: " + new Date(root.checkedAt * 1000).toLocaleString(Qt.locale(), Locale.ShortFormat) : "Official repositories · rolling release"
        }
        StyledText {
            visible: !!root.errorMessage
            Layout.fillWidth: true
            Layout.margins: Tokens.padding.small
            text: root.errorMessage
            color: Colours.palette.m3error
            wrapMode: Text.Wrap
            font: Tokens.font.body.small
        }
        RowButton {
            first: true
            last: true
            text: root.busy ? "Checking…" : "Check for updates"
            icon: "refresh"
            disabled: root.busy
            onClicked: root.checkUpdates(true)
        }
        StyledText {
            Layout.fillWidth: true
            Layout.margins: Tokens.padding.small
            text: "Checks Arch repository packages without installing anything. AUR, Flatpak and other software sources are not included."
            color: Colours.palette.m3outline
            font: Tokens.font.body.small
            wrapMode: Text.Wrap
        }
        SectionHeader {
            visible: root.packages.length > 0
            text: root.errorMessage ? "Previous check · may be out of date" : "Available package updates"
        }
        Repeater {
            model: root.packages
            delegate: InfoRow {
                required property var modelData
                required property int index
                first: index === 0
                last: index === root.packages.length - 1
                label: modelData.name
                subtext: "Installed: " + modelData.installed
                value: modelData.available
            }
        }
    }
}
