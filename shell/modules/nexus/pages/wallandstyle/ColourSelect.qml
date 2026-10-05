pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Quickshell.Io
import Caelestia.Config
import Caelestia.I18n
import qs.components
import qs.services
import qs.modules.nexus.common
import qs.modules.launcher.services

PageBase {
    id: root

    property string applyError

    title: Tr.tr("Colours")
    isSubPage: true

    function displayName(value: string): string {
        return value.slice(0, 1).toUpperCase() + value.slice(1);
    }

    function applyScheme(scheme: var): void {
        if (applyProcess.running)
            return;
        applyError = "";
        applyProcess.command = ["caelestia", "scheme", "set", "--notify", "-n", scheme.name, "-f", scheme.flavour];
        applyProcess.running = true;
    }

    property Process applyProcess: Process {
        onExited: (exitCode, exitStatus) => {
            if (exitCode !== 0)
                root.applyError = Tr.tr("Could not apply the colour scheme. Please try again.");
            Schemes.reload();
        }
    }

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: Tokens.spacing.extraSmall / 2

        StyledText {
            Layout.fillWidth: true
            Layout.bottomMargin: Tokens.spacing.medium
            text: Tr.tr("Choose a colour scheme to apply it.")
            color: Colours.palette.m3onSurfaceVariant
            font: Tokens.font.body.medium
            wrapMode: Text.WordWrap
        }

        StyledText {
            Layout.fillWidth: true
            Layout.bottomMargin: visible ? Tokens.spacing.medium : 0
            visible: root.applyError !== ""
            text: root.applyError
            color: Colours.palette.m3error
            font: Tokens.font.body.medium
            wrapMode: Text.WordWrap
        }

        StyledText {
            Layout.fillWidth: true
            visible: schemeRepeater.count === 0
            text: Tr.tr("Loading colour schemes…")
            color: Colours.palette.m3onSurfaceVariant
            font: Tokens.font.body.medium
        }

        Repeater {
            id: schemeRepeater

            model: Schemes.list

            ConnectedRect {
                id: schemeCard

                required property var modelData
                required property int index
                readonly property bool selected: Colours.scheme === modelData.name && Colours.flavour === modelData.flavour

                Layout.fillWidth: true
                implicitHeight: cardContents.implicitHeight + Tokens.padding.medium * 2
                first: index === 0
                last: index === schemeRepeater.count - 1
                color: selected ? Colours.tPalette.m3secondaryContainer : Colours.tPalette.m3surfaceContainer

                StateLayer {
                    topLeftRadius: schemeCard.topLeftRadius
                    topRightRadius: schemeCard.topRightRadius
                    bottomLeftRadius: schemeCard.bottomLeftRadius
                    bottomRightRadius: schemeCard.bottomRightRadius
                    disabled: applyProcess.running
                    onClicked: root.applyScheme(schemeCard.modelData)
                }

                RowLayout {
                    id: cardContents

                    anchors.fill: parent
                    anchors.leftMargin: Tokens.padding.largeIncreased
                    anchors.rightMargin: Tokens.padding.largeIncreased
                    anchors.topMargin: Tokens.padding.medium
                    anchors.bottomMargin: Tokens.padding.medium
                    spacing: Tokens.spacing.medium

                    StyledRect {
                        implicitWidth: 48
                        implicitHeight: 48
                        radius: Tokens.rounding.large
                        color: "#" + schemeCard.modelData.colours.surface
                        border.width: 1
                        border.color: "#" + schemeCard.modelData.colours.outline

                        Row {
                            anchors.centerIn: parent
                            spacing: 3

                            Repeater {
                                model: [schemeCard.modelData.colours.primary, schemeCard.modelData.colours.secondary, schemeCard.modelData.colours.tertiary]

                                StyledRect {
                                    required property string modelData

                                    implicitWidth: 10
                                    implicitHeight: 22
                                    radius: Tokens.rounding.full
                                    color: "#" + modelData
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0

                        StyledText {
                            Layout.fillWidth: true
                            text: root.displayName(schemeCard.modelData.name)
                            font: Tokens.font.body.medium
                            elide: Text.ElideRight
                        }

                        StyledText {
                            Layout.fillWidth: true
                            text: root.displayName(schemeCard.modelData.flavour)
                            color: Colours.palette.m3onSurfaceVariant
                            font: Tokens.font.body.small
                            elide: Text.ElideRight
                        }
                    }

                    MaterialIcon {
                        text: schemeCard.selected ? "check_circle" : ""
                        color: Colours.palette.m3primary
                        fontStyle: Tokens.font.icon.large
                    }
                }
            }
        }
    }
}
