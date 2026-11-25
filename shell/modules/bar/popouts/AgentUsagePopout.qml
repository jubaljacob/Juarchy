pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Caelestia.Config
import Caelestia.I18n
import qs.components
import qs.components.controls
import qs.components.widgets
import qs.services

ColumnLayout {
    id: root

    readonly property date now: Time.date

    spacing: Tokens.spacing.large
    implicitWidth: 340

    // Opening the panel asks for fresh local counts; limits are only re-checked when due.
    Component.onCompleted: AgentUsage.refresh(false)

    RowLayout {
        Layout.fillWidth: true

        StyledText {
            Layout.fillWidth: true
            text: Tr.tr("Agent usage")
            font: Tokens.font.title.small
        }

        StyledText {
            text: AgentUsage.busy ? Tr.tr("Updating…") : AgentUsage.formatAge(AgentUsage.updatedAt, root.now)
            color: Colours.palette.m3onSurfaceVariant
            font: Tokens.font.label.medium
        }

        IconButton {
            icon: "refresh"
            type: IconButton.Text
            disabled: AgentUsage.busy
            onClicked: AgentUsage.refresh(true)
        }
    }

    StyledText {
        Layout.fillWidth: true
        visible: AgentUsage.failed && AgentUsage.agents.length === 0
        text: Tr.tr("Could not read agent usage. Is juarchy-agent-usage installed?")
        color: Colours.palette.m3error
        wrapMode: Text.WordWrap
    }

    Repeater {
        model: AgentUsage.agents

        ColumnLayout {
            id: section

            required property var modelData
            required property int index
            readonly property var stats: modelData.stats
            readonly property bool urgent: modelData.usageStatusText !== "" && modelData.usageStatusText !== "Limits off"

            Layout.fillWidth: true
            spacing: Tokens.spacing.small

            StyledRect {
                Layout.fillWidth: true
                Layout.bottomMargin: Tokens.spacing.small
                visible: section.index > 0
                implicitHeight: 1
                color: Colours.palette.m3outlineVariant
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Tokens.spacing.medium

                AgentMark {
                    agent: section.modelData.id
                    size: 20
                    opacity: section.modelData.ready ? 1 : 0.5
                }

                StyledText {
                    text: section.modelData.name
                    font: Tokens.font.title.small
                    opacity: section.modelData.ready ? 1 : 0.6
                }

                StyledRect {
                    visible: section.modelData.tierLabel !== ""
                    implicitWidth: plan.implicitWidth + Tokens.padding.medium * 2
                    implicitHeight: plan.implicitHeight + Tokens.padding.extraSmall * 2
                    color: Colours.palette.m3secondaryContainer
                    radius: Tokens.rounding.full

                    StyledText {
                        id: plan

                        anchors.centerIn: parent
                        text: section.modelData.tierLabel
                        color: Colours.palette.m3onSecondaryContainer
                        font: Tokens.font.label.medium
                    }
                }

                Item {
                    Layout.fillWidth: true
                }
            }

            StyledText {
                Layout.fillWidth: true
                visible: !section.modelData.ready
                text: section.modelData.installed
                    ? Tr.tr("Not signed in. Run `%1` to see your usage.").arg(section.modelData.id === "codex" ? "codex login" : "claude auth login")
                    : Tr.tr("Not installed. Install the %1 CLI and sign in to see your usage.").arg(section.modelData.name)
                color: Colours.palette.m3onSurfaceVariant
                font: Tokens.font.body.small
                wrapMode: Text.WordWrap
            }

            // Anything wrong, in the same words for every agent.
            StyledText {
                Layout.fillWidth: true
                visible: section.modelData.ready && section.modelData.usageStatusText !== ""
                text: section.modelData.usageStatusText
                color: section.urgent ? Colours.palette.m3error : Colours.palette.m3onSurfaceVariant
                font: Tokens.font.label.medium
            }

            StyledText {
                Layout.fillWidth: true
                visible: section.modelData.ready && text !== ""
                text: section.modelData.authHelpText
                    || (section.modelData.limitsStale ? Tr.tr("Showing limits from %1.").arg(AgentUsage.formatAge(section.modelData.limitsFetchedAt, root.now)) : "")
                color: Colours.palette.m3onSurfaceVariant
                font: Tokens.font.body.small
                wrapMode: Text.WordWrap
            }

            Repeater {
                model: section.modelData.limits

                RowLayout {
                    id: limit

                    required property var modelData

                    Layout.fillWidth: true
                    spacing: Tokens.spacing.medium
                    opacity: section.modelData.limitsStale ? 0.6 : 1

                    StyledText {
                        Layout.preferredWidth: 96
                        text: limit.modelData.title || limit.modelData.label
                        color: Colours.palette.m3onSurfaceVariant
                        font: Tokens.font.label.medium
                        elide: Text.ElideRight
                    }

                    StyledRect {
                        Layout.fillWidth: true
                        implicitHeight: 6
                        radius: Tokens.rounding.full
                        color: Colours.palette.m3secondaryContainer

                        StyledRect {
                            width: parent.width * Math.max(0, Math.min(1, limit.modelData.percent))
                            height: parent.height
                            radius: parent.radius
                            color: AgentUsage.tone(limit.modelData.percent)
                        }
                    }

                    StyledText {
                        Layout.preferredWidth: 34
                        horizontalAlignment: Text.AlignRight
                        text: `${Math.round(limit.modelData.percent * 100)}%`
                        font: Tokens.font.label.medium
                    }

                    StyledText {
                        Layout.preferredWidth: 52
                        horizontalAlignment: Text.AlignRight
                        text: AgentUsage.formatReset(limit.modelData.resetsAt, root.now)
                        color: Colours.palette.m3outline
                        font: Tokens.font.label.medium
                    }
                }
            }

            StyledText {
                Layout.fillWidth: true
                visible: section.modelData.ready && section.modelData.limits.length === 0 && section.modelData.usageStatusText === ""
                text: Tr.tr("No usage limits on this plan.")
                color: Colours.palette.m3onSurfaceVariant
                font: Tokens.font.body.small
            }

            // What this machine spent, from the agent's own session files.
            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: Tokens.spacing.small
                visible: section.stats.hasLocal
                spacing: Tokens.spacing.large

                Row {
                    id: spark

                    readonly property real peak: Math.max(1, ...section.stats.recentDays.map(day => day.tokens))

                    Layout.alignment: Qt.AlignBottom
                    spacing: 3

                    Repeater {
                        model: section.stats.recentDays

                        Item {
                            id: day

                            required property var modelData
                            required property int index

                            width: 8
                            height: 26

                            StyledRect {
                                anchors.bottom: parent.bottom
                                width: parent.width
                                height: Math.max(2, parent.height * day.modelData.tokens / spark.peak)
                                radius: 2
                                color: day.index === section.stats.recentDays.length - 1 ? Colours.palette.m3primary : Colours.palette.m3secondary
                                opacity: day.modelData.tokens > 0 ? 1 : 0.25
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0

                    StyledText {
                        Layout.fillWidth: true
                        text: Tr.tr("Today %1 · %2 · %3")
                            .arg(AgentUsage.formatTokens(section.stats.todayTokens))
                            .arg(Tr.trN("%n prompt", "%n prompts", section.stats.todayPrompts))
                            .arg(Tr.trN("%n session", "%n sessions", section.stats.todaySessions))
                        font: Tokens.font.label.medium
                        elide: Text.ElideRight
                    }

                    StyledText {
                        Layout.fillWidth: true
                        text: section.stats.topModel
                            ? Tr.tr("7 days %1 · %2").arg(AgentUsage.formatTokens(section.stats.weekTokens)).arg(section.stats.topModel)
                            : Tr.tr("7 days %1").arg(AgentUsage.formatTokens(section.stats.weekTokens))
                        color: Colours.palette.m3onSurfaceVariant
                        font: Tokens.font.label.medium
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
}
