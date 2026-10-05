pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Caelestia.Config
import Caelestia.I18n
import qs.components
import qs.services

StyledRect {
    id: root

    readonly property color colour: Colours.palette.m3secondary
    readonly property int padding: Config.bar.clock.background ? Tokens.padding.medium : Tokens.padding.extraSmall

    implicitWidth: layout.implicitWidth + padding * 2
    implicitHeight: Tokens.sizes.bar.innerWidth
    color: Qt.alpha(Colours.tPalette.m3surfaceContainer, Config.bar.clock.background ? Colours.tPalette.m3surfaceContainer.a : 0)
    radius: Tokens.rounding.full

    RowLayout {
        id: layout
        anchors.centerIn: parent
        spacing: Tokens.spacing.small

        Loader {
            asynchronous: true
            active: Config.bar.clock.showIcon
            visible: active
            sourceComponent: MaterialIcon {
                text: "calendar_month"
                color: root.colour
            }
        }

        StyledText {
            visible: Config.bar.clock.showDate
            text: Time.format("ddd d")
            color: root.colour
        }

        StyledText {
            text: Time.hourStr + ":" + Time.minuteStr
                + (root.Config.bar.clock.showSeconds ? ":" + Time.format("ss") : "")
                + (Units.twelveHourClock ? " " + Time.amPmStr.toLowerCase() : "")
            color: root.colour
        }
    }
}
