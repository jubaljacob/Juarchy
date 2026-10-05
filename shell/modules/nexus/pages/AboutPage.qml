import QtQuick
import QtQuick.Layouts
import Quickshell.Io
import Caelestia
import Caelestia.Config
import Caelestia.I18n
import qs.components
import qs.services
import qs.utils
import qs.modules.nexus.common

PageBase {
    id: root

    // Plugin support is not wired up yet; always 0 for now
    readonly property int pluginCount: 0

    property string quickshellVersion
    property string archRelease: Tr.tr("Rolling release")

    title: Tr.tr("About")

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: Tokens.spacing.extraSmall / 2

        // e.g. "Quickshell 0.3.0 (revision ...)"
        Process {
            running: true
            command: ["quickshell", "--version"]
            stdout: StdioCollector {
                onStreamFinished: root.quickshellVersion = text.trim().split(" ")[1] ?? ""
            }
        }

        FileView {
            path: "/etc/os-release"
            onLoaded: {
                const fields = Object.fromEntries(text().split("\n")
                    .filter(line => /^[A-Z_]+=/.test(line))
                    .map(line => {
                        const separator = line.indexOf("=");
                        return [line.slice(0, separator), line.slice(separator + 1).replace(/^['"]|['"]$/g, "")];
                    }));
                root.archRelease = fields.VERSION_ID || fields.VERSION
                    || (fields.BUILD_ID === "rolling" ? Tr.tr("Rolling release") : fields.BUILD_ID)
                    || Tr.tr("Rolling release");
            }
        }

        // Hero
        ConnectedRect {
            Layout.fillWidth: true
            first: true
            last: true
            implicitHeight: hero.implicitHeight + Tokens.padding.extraLarge * 2

            ColumnLayout {
                id: hero

                anchors.centerIn: parent
                width: parent.width - Tokens.padding.largeIncreased * 2
                spacing: Tokens.spacing.small

                Image {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 128
                    Layout.preferredHeight: 128
                    source: "file:///usr/share/pixmaps/archlinux-logo.svg"
                    sourceSize.width: 256
                    sourceSize.height: 256
                    fillMode: Image.PreserveAspectFit
                }

                StyledText {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.topMargin: Tokens.spacing.small
                    text: "Arch Linux"
                    font: Tokens.font.headline.builders.large.width(110).build()
                }

                StyledText {
                    Layout.alignment: Qt.AlignHCenter
                    text: root.archRelease
                    color: Colours.palette.m3onSurfaceVariant
                    font: Tokens.font.body.medium
                }
            }
        }

        // System
        SectionHeader {
            text: Tr.tr("System")
        }

        InfoRow {
            first: true
            label: Tr.tr("Hostname")
            value: SysInfo.hostname
        }

        InfoRow {
            label: Tr.trCtx("Device", "system model name")
            value: SysInfo.device
        }

        InfoRow {
            label: Tr.tr("Distro")
            value: SysInfo.osPrettyName || SysInfo.osName
        }

        InfoRow {
            label: Tr.tr("Kernel")
            value: SysInfo.kernel
        }

        InfoRow {
            last: true
            // TRANSLATORS: BIOS or UEFI firmware version
            label: Tr.tr("Firmware")
            value: SysInfo.firmware
        }

        // Software
        SectionHeader {
            text: Tr.tr("Software")
        }

        InfoRow {
            first: true
            label: "Quickshell"
            value: root.quickshellVersion || "…"
        }

        InfoRow {
            last: true
            label: "Qt"
            value: CUtils.qtVersion || "…"
        }

        // Plugins
        SectionHeader {
            text: Tr.tr("Plugins")
        }

        InfoRow {
            first: true
            last: true
            label: Tr.tr("Loaded plugins")
            value: root.pluginCount.toString()
        }
    }
}
