pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Quickshell.Io
import Caelestia.Config
import Caelestia.I18n
import qs.components
import qs.components.controls
import qs.components.images
import qs.services
import qs.utils
import qs.modules.nexus.common

ColumnLayout {
    id: root

    property var presets: []
    property string error
    property string output
    property string stderrText
    property string action
    property var restoringPreset: null
    readonly property string helper: `${Paths.home}/.local/bin/juarchy-theme`

    spacing: Tokens.spacing.medium
    Component.onCompleted: run("list")

    function run(operation, name = "", preset = null) {
        if (worker.running)
            return;
        action = operation;
        restoringPreset = preset;
        error = "";
        output = "";
        stderrText = "";
        if (operation === "dynamic") {
            worker.command = ["caelestia", "scheme", "set", "-n", "dynamic", "-f", "default"];
        } else {
            const command = ["python3", helper, operation];
            if (name)
                command.push(name);
            if (operation === "save" && !GlobalConfig.services.smartScheme)
                command.push("--no-smart");
            worker.command = command;
        }
        worker.running = true;
    }

    Process {
        id: worker
        stdout: StdioCollector {
            onStreamFinished: root.output = text
        }
        stderr: StdioCollector {
            onStreamFinished: root.stderrText = text
        }
        onExited: (exitCode, exitStatus) => {
            if (exitCode !== 0) {
                root.error = root.stderrText.trim() || Tr.tr("Could not update the theme. Please try again.");
                return;
            }
            if (root.action !== "dynamic") {
                try {
                    root.presets = JSON.parse(root.output);
                } catch (error) {
                    root.error = Tr.tr("Could not read saved themes.");
                    return;
                }
            }
            if (root.action === "save")
                presetName.text = "";
            if (root.action === "apply" && root.restoringPreset)
                GlobalConfig.services.smartScheme = root.restoringPreset.smart;
        }
    }

    StyledText {
        text: Tr.tr("Wallpaper themes")
        font: Tokens.font.title.small
    }

    StyledText {
        Layout.fillWidth: true
        text: Colours.scheme === "dynamic"
            ? Tr.tr("Wallpaper colours are active. Choosing a wallpaper updates your desktop palette.")
            : Tr.tr("A fixed palette is active. Use wallpaper colours, or choose a fixed palette in Colours.")
        font: Tokens.font.body.small
        color: Colours.palette.m3onSurfaceVariant
        wrapMode: Text.WordWrap
    }

    IconTextButton {
        icon: "auto_awesome"
        text: Tr.tr("Use wallpaper colours")
        disabled: worker.running || Colours.scheme === "dynamic"
        onClicked: root.run("dynamic")
    }

    ToggleRow {
        first: true
        last: true
        text: Tr.tr("Match wallpaper brightness")
        subtext: Tr.tr("Automatically choose light/dark mode and colour intensity for new wallpapers")
        checked: GlobalConfig.services.smartScheme
        disabled: worker.running || Colours.scheme !== "dynamic"
        onToggled: GlobalConfig.services.smartScheme = checked
    }

    StyledText {
        Layout.fillWidth: true
        text: Tr.tr("Save your current wallpaper and palette together. Turn off brightness matching to keep your chosen light/dark mode.")
        font: Tokens.font.body.small
        color: Colours.palette.m3onSurfaceVariant
        wrapMode: Text.WordWrap
    }

    RowLayout {
        Layout.fillWidth: true
        StyledTextField {
            id: presetName
            Layout.fillWidth: true
            placeholderText: Tr.tr("Theme name")
            enabled: !worker.running
            onAccepted: {
                if (text.trim())
                    root.run("save", text.trim());
            }
        }
        IconTextButton {
            icon: "save"
            text: Tr.tr("Save")
            disabled: worker.running || !presetName.text.trim()
            onClicked: root.run("save", presetName.text.trim())
        }
    }

    StyledText {
        Layout.fillWidth: true
        visible: root.error !== ""
        text: root.error
        color: Colours.palette.m3error
        wrapMode: Text.WordWrap
    }

    Repeater {
        model: root.presets
        RowLayout {
            id: presetRow
            required property var modelData
            Layout.fillWidth: true
            spacing: Tokens.spacing.medium

            StyledClippingRect {
                implicitWidth: 88
                implicitHeight: 56
                radius: Tokens.rounding.small
                color: Colours.tPalette.m3surfaceContainer
                FadeImage {
                    anchors.fill: parent
                    source: presetRow.modelData.wallpaper
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                StyledText {
                    Layout.fillWidth: true
                    text: presetRow.modelData.name
                    elide: Text.ElideRight
                }
                StyledText {
                    Layout.fillWidth: true
                    text: presetRow.modelData.scheme.name === "dynamic"
                        ? Tr.tr("Wallpaper colours")
                        : `${presetRow.modelData.scheme.name} · ${presetRow.modelData.scheme.flavour}`
                    color: Colours.palette.m3onSurfaceVariant
                    font: Tokens.font.body.small
                    elide: Text.ElideRight
                }
            }

            IconTextButton {
                icon: "check"
                text: Tr.tr("Apply")
                disabled: worker.running
                onClicked: root.run("apply", presetRow.modelData.name, presetRow.modelData)
            }
            IconButton {
                icon: "delete"
                disabled: worker.running
                onClicked: root.run("delete", presetRow.modelData.name)
            }
        }
    }
}
