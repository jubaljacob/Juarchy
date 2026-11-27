pragma ComponentBehavior: Bound

// Floating screenshot preview in the top-left corner.
//   qs -c juarchy ipc call screenshotPreview open /path/to/shot.png
//   qs -c juarchy ipc call screenshotPreview dismiss    (instant, used before capturing)
// Click the preview to open the file, hover for share/close, share -> LocalSend.

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Caelestia.Config
import qs.components
import qs.components.containers
import qs.components.controls
import qs.components.effects
import qs.services

Scope {
    id: root

    property string path
    property string screenName
    property int serial

    readonly property int timeout: 6000

    function show(file: string): void {
        path = file;
        screenName = Hypr.focusedMonitor?.name ?? "";
        serial++;
        loader.active = true;
    }

    LazyLoader {
        id: loader

        StyledWindow {
            id: win

            readonly property real pad: Tokens.padding.extraLarge

            name: "screenshot-preview"
            screen: Quickshell.screens.find(s => s.name === root.screenName) ?? Quickshell.screens[0]

            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.exclusionMode: ExclusionMode.Normal
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
            exclusiveZone: 0

            anchors.top: true
            anchors.left: true

            implicitWidth: card.width + pad * 2
            implicitHeight: card.height + pad * 2

            mask: Region {
                item: content.closing ? null : card
            }

            Item {
                id: content

                property real progress
                property bool entered
                property bool closing
                property bool menuOpen
                readonly property bool hovered: hover.hovered

                function enter(): void {
                    if (entered)
                        return;
                    entered = true;
                    exitAnim.stop();
                    enterAnim.restart();
                }

                function close(): void {
                    if (closing)
                        return;
                    closing = true;
                    enterAnim.stop();
                    exitAnim.restart();
                }

                function openFile(): void {
                    Quickshell.execDetached(["xdg-open", root.path]);
                    close();
                }

                function sendLocalSend(): void {
                    Quickshell.execDetached(["localsend", root.path]);
                    close();
                }

                anchors.fill: parent

                Connections {
                    target: root

                    function onSerialChanged(): void {
                        // A new screenshot arrived while the preview was up.
                        content.menuOpen = false;
                        if (content.closing) {
                            content.closing = false;
                            content.entered = false;
                        } else if (content.entered) {
                            bump.restart();
                        }
                        dismissTimer.restart();
                    }
                }

                Anim {
                    id: enterAnim

                    target: content
                    property: "progress"
                    to: 1
                    type: Anim.SlowSpatial
                }

                Anim {
                    id: exitAnim

                    target: content
                    property: "progress"
                    to: 0
                    type: Anim.Emphasized
                    onFinished: if (content.closing) loader.active = false
                }

                Timer {
                    id: dismissTimer

                    interval: root.timeout
                    running: content.entered && !content.closing && !content.hovered && !content.menuOpen
                    onTriggered: content.close()
                }

                // Don't wait forever if the image never decodes.
                Timer {
                    interval: 800
                    running: !content.entered
                    onTriggered: content.enter()
                }

                Elevation {
                    x: card.x
                    y: card.y
                    width: card.width
                    height: card.height
                    radius: card.radius
                    level: content.hovered ? 4 : 3
                    opacity: card.opacity
                    scale: card.scale
                    transformOrigin: Item.TopLeft
                }

                StyledClippingRect {
                    id: card

                    readonly property real maxW: 320
                    readonly property real maxH: 220
                    readonly property real minW: 200
                    readonly property real minH: 130
                    readonly property real ratio: img.status === Image.Ready && img.implicitWidth > 0 ? img.implicitHeight / img.implicitWidth : 9 / 16
                    readonly property real fitW: ratio > maxH / maxW ? maxH / ratio : maxW

                    x: win.pad - (1 - content.progress) * (width + win.pad * 2)
                    y: win.pad
                    width: Math.round(Math.max(minW, fitW))
                    height: Math.round(Math.min(maxH, Math.max(minH, fitW * ratio)))
                    opacity: Math.min(1, content.progress * 1.5)
                    scale: (0.88 + 0.12 * content.progress) * (bumpScale.value)
                    transformOrigin: Item.TopLeft
                    radius: Tokens.rounding.large
                    color: Colours.palette.m3surfaceContainer
                    border.width: 1
                    border.color: Qt.alpha(Colours.palette.m3outlineVariant, 0.6)

                    QtObject {
                        id: bumpScale

                        property real value: 1
                    }

                    SequentialAnimation {
                        id: bump

                        Anim {
                            target: bumpScale
                            property: "value"
                            to: 0.94
                            type: Anim.FastEffects
                        }
                        Anim {
                            target: bumpScale
                            property: "value"
                            to: 1
                            type: Anim.DefaultSpatial
                        }
                    }

                    Image {
                        id: img

                        anchors.fill: parent
                        source: root.path ? "file://" + encodeURI(root.path) : ""
                        sourceSize.width: card.maxW * 2
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        cache: false
                        smooth: true
                        mipmap: true
                        onStatusChanged: if (status === Image.Ready || status === Image.Error) content.enter()
                    }

                    HoverHandler {
                        id: hover
                    }

                    // Click anywhere on the image: open it (or dismiss the share sheet).
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: content.menuOpen ? content.menuOpen = false : content.openFile()
                    }

                    // Hover scrim
                    Rectangle {
                        anchors.fill: parent
                        opacity: content.hovered || content.menuOpen ? 1 : 0
                        gradient: Gradient {
                            GradientStop {
                                position: 0
                                color: Qt.rgba(0, 0, 0, 0.45)
                            }
                            GradientStop {
                                position: 0.45
                                color: Qt.rgba(0, 0, 0, 0.12)
                            }
                            GradientStop {
                                position: 1
                                color: Qt.rgba(0, 0, 0, 0.6)
                            }
                        }

                        Behavior on opacity {
                            Anim {
                                type: Anim.DefaultEffects
                            }
                        }
                    }

                    // "Click to open" hint
                    Row {
                        anchors.left: parent.left
                        anchors.bottom: parent.bottom
                        anchors.margins: Tokens.padding.medium
                        spacing: Tokens.spacing.extraSmall
                        opacity: content.hovered && !content.menuOpen ? 1 : 0

                        Behavior on opacity {
                            Anim {
                                type: Anim.DefaultEffects
                            }
                        }

                        MaterialIcon {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "open_in_new"
                            color: "white"
                        }

                        StyledText {
                            anchors.verticalCenter: parent.verticalCenter
                            text: qsTr("Click to open")
                            color: "white"
                            font: Tokens.font.label.medium
                        }
                    }

                    IconButton {
                        id: closeButton

                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.margins: Tokens.padding.small
                        type: IconButton.Tonal
                        isRound: true
                        icon: "close"
                        font: Tokens.font.icon.small
                        opacity: content.hovered && !content.menuOpen ? 1 : 0
                        scale: opacity ? 1 : 0.6
                        visible: opacity > 0
                        onClicked: content.close()

                        Behavior on opacity {
                            Anim {
                                type: Anim.DefaultEffects
                            }
                        }
                        Behavior on scale {
                            Anim {
                                type: Anim.FastSpatial
                            }
                        }
                    }

                    IconButton {
                        id: shareButton

                        anchors.top: parent.top
                        anchors.right: parent.right
                        anchors.margins: Tokens.padding.small
                        isRound: true
                        shapeMorph: true
                        icon: "share"
                        font: Tokens.font.icon.small
                        opacity: content.hovered || content.menuOpen ? 1 : 0
                        scale: opacity ? 1 : 0.6
                        visible: opacity > 0
                        onClicked: content.menuOpen = !content.menuOpen

                        Behavior on opacity {
                            Anim {
                                type: Anim.DefaultEffects
                            }
                        }
                        Behavior on scale {
                            Anim {
                                type: Anim.FastSpatial
                            }
                        }
                    }

                    // Share sheet: slides up from the bottom of the card.
                    StyledRect {
                        id: sheet

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.margins: Tokens.padding.small
                        y: content.menuOpen ? parent.height - height - Tokens.padding.small : parent.height + 4
                        height: sheetColumn.implicitHeight + Tokens.padding.small * 2
                        radius: Tokens.rounding.medium
                        color: Colours.palette.m3surfaceContainerHigh
                        opacity: content.menuOpen ? 1 : 0
                        visible: opacity > 0

                        Behavior on y {
                            Anim {
                                type: Anim.DefaultSpatial
                            }
                        }
                        Behavior on opacity {
                            Anim {
                                type: Anim.DefaultEffects
                            }
                        }

                        // Swallow clicks so they don't reach the "open" area underneath.
                        MouseArea {
                            anchors.fill: parent
                        }

                        Column {
                            id: sheetColumn

                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: Tokens.padding.small
                            spacing: Tokens.spacing.extraSmall

                            StyledText {
                                leftPadding: Tokens.padding.small
                                text: qsTr("Share via")
                                color: Colours.palette.m3onSurfaceVariant
                                font: Tokens.font.label.small
                            }

                            StyledRect {
                                width: parent.width
                                implicitHeight: localSendRow.implicitHeight + Tokens.padding.small * 2
                                radius: Tokens.rounding.small
                                color: Colours.palette.m3secondaryContainer

                                StateLayer {
                                    color: Colours.palette.m3onSecondaryContainer
                                    onClicked: content.sendLocalSend()
                                }

                                Row {
                                    id: localSendRow

                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.left: parent.left
                                    anchors.leftMargin: Tokens.padding.medium
                                    spacing: Tokens.spacing.small

                                    MaterialIcon {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "send_to_mobile"
                                        color: Colours.palette.m3onSecondaryContainer
                                        fontStyle: Tokens.font.icon.medium
                                    }

                                    StyledText {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: qsTr("LocalSend")
                                        color: Colours.palette.m3onSecondaryContainer
                                        font: Tokens.font.body.medium
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    IpcHandler {
        target: "screenshotPreview"

        function open(path: string): void {
            root.show(path);
        }

        // Returns whether a preview was on screen, so callers can wait out the fade.
        function dismiss(): bool {
            const wasShown = loader.active;
            loader.active = false;
            return wasShown;
        }
    }
}
