pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Caelestia.Config
import Caelestia.I18n
import qs.components
import qs.components.controls
import qs.services
import qs.modules.nexus.common

ColumnLayout {
    id: root

    readonly property var backgrounds: OmarchyThemes.currentTheme?.backgrounds ?? []

    spacing: Tokens.spacing.medium

    RowLayout {
        Layout.fillWidth: true

        StyledText {
            Layout.fillWidth: true
            text: Tr.tr("Omarchy themes")
            font: Tokens.font.title.small
        }

        IconTextButton {
            icon: "skip_next"
            text: Tr.tr("Next background")
            type: IconTextButton.Tonal
            disabled: OmarchyThemes.busy || !OmarchyThemes.active
            onClicked: OmarchyThemes.nextBackground()
        }
    }

    StyledText {
        Layout.fillWidth: true
        text: {
            if (!OmarchyThemes.loaded)
                return "";
            if (OmarchyThemes.themes.length === 0)
                return Tr.tr("No Omarchy themes are installed. Run scripts/install-omarchy-themes.py from the Juarchy checkout.");
            if (OmarchyThemes.active)
                return Tr.tr("%1 is active. Its colours style the whole desktop; changing the background keeps them.").arg(OmarchyThemes.currentTheme?.title ?? "");
            return Tr.tr("Choose a theme to set its wallpaper and restyle the shell, apps and terminals together.");
        }
        font: Tokens.font.body.small
        color: Colours.palette.m3onSurfaceVariant
        wrapMode: Text.WordWrap
        visible: text !== ""
    }

    GridLayout {
        Layout.fillWidth: true
        visible: OmarchyThemes.themes.length > 0

        columns: Config.nexus.wallpapersPerRow
        rowSpacing: Tokens.spacing.medium
        columnSpacing: Tokens.spacing.large

        Repeater {
            model: OmarchyThemes.themes

            Item {
                id: card

                required property var modelData

                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                implicitHeight: item.implicitHeight

                WallItem {
                    id: item

                    anchors.fill: parent
                    imgHeight: Math.round(width * 0.56)
                    radius: Tokens.rounding.large
                    source: card.modelData.preview
                    text: card.modelData.title
                    enabled: !OmarchyThemes.busy
                    onClicked: OmarchyThemes.apply(card.modelData.id)
                }

                // Ring around the theme in use.
                Rectangle {
                    width: parent.width
                    height: item.imgHeight
                    radius: item.radius
                    color: "transparent"
                    border.width: card.modelData.active ? 3 : 0
                    border.color: Colours.palette.m3primary
                    visible: card.modelData.active
                }

                // The theme's own colours, so the card reads without its picture.
                Row {
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Tokens.padding.small
                    spacing: 3

                    Repeater {
                        model: card.modelData.swatches

                        Rectangle {
                            required property string modelData

                            width: 9
                            height: 9
                            radius: 5
                            color: modelData
                            border.width: 1
                            border.color: Qt.rgba(0, 0, 0, 0.35)
                        }
                    }
                }
            }
        }
    }

    StyledText {
        Layout.topMargin: Tokens.spacing.small
        visible: OmarchyThemes.active && root.backgrounds.length > 0
        text: Tr.tr("%1 backgrounds").arg(OmarchyThemes.currentTheme?.title ?? "")
        font: Tokens.font.title.small
    }

    GridLayout {
        Layout.fillWidth: true
        visible: OmarchyThemes.active && root.backgrounds.length > 0

        columns: Config.nexus.wallpapersPerRow
        rowSpacing: Tokens.spacing.medium
        columnSpacing: Tokens.spacing.large

        Repeater {
            model: OmarchyThemes.active ? root.backgrounds : []

            Item {
                id: background

                required property var modelData

                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                implicitHeight: shot.implicitHeight

                WallItem {
                    id: shot

                    anchors.fill: parent
                    imgHeight: Math.round(width * 0.56)
                    radius: Tokens.rounding.large
                    source: background.modelData.path
                    text: background.modelData.name.replace(/\.[^.]+$/, "")
                    enabled: !OmarchyThemes.busy
                    onClicked: OmarchyThemes.setBackground(background.modelData.path)
                }

                Rectangle {
                    width: parent.width
                    height: shot.imgHeight
                    radius: shot.radius
                    color: "transparent"
                    border.width: 3
                    border.color: Colours.palette.m3primary
                    visible: background.modelData.current
                }
            }
        }
    }
}
