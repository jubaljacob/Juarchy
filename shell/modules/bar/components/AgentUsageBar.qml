pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Caelestia.Config
import qs.components
import qs.components.widgets
import qs.services

// Claude and Codex in the bar: each agent's mark and how much of its
// busiest limit window is spent. Hover for the full panel.
StyledRect {
    id: root

    readonly property var shown: AgentUsage.ready
    readonly property int padding: Tokens.padding.small

    implicitWidth: layout.implicitWidth + padding * 2
    implicitHeight: Tokens.sizes.bar.innerWidth
    color: "transparent"
    radius: Tokens.rounding.full

    RowLayout {
        id: layout

        anchors.centerIn: parent
        spacing: Tokens.spacing.medium

        Repeater {
            model: root.shown

            RowLayout {
                id: entry

                required property var modelData
                readonly property real percent: AgentUsage.primaryPercent(modelData)
                readonly property color tone: percent < 0 ? Colours.palette.m3onSurfaceVariant : AgentUsage.tone(percent)

                spacing: Tokens.spacing.extraSmall

                AgentMark {
                    agent: entry.modelData.id
                    size: 16
                    tint: entry.tone
                    opacity: entry.modelData.limitsStale ? 0.6 : 1
                }

                StyledText {
                    visible: entry.percent >= 0
                    text: `${Math.round(entry.percent * 100)}%`
                    color: entry.tone
                    font: Tokens.font.label.medium
                }
            }
        }

        // Nothing set up yet: the widget is still the way into the panel.
        MaterialIcon {
            visible: root.shown.length === 0
            text: "smart_toy"
            color: Colours.palette.m3onSurfaceVariant
        }
    }
}
