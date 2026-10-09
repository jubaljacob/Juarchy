pragma ComponentBehavior: Bound

import QtQuick

Item {
    id: root

    required property real barHeight
    required property color handleColour
    property color activeColour: handleColour
    property color recordingColour: "#fb4934"
    property font iconFont: Qt.font({ family: "Material Symbols Rounded", pixelSize: 18 })
    property bool dndEnabled: false
    property bool recordingActive: false
    property bool nightLightEnabled: false
    property bool nightLightBusy: false
    property color nightLightColour: "#fabd2f"
    property bool microphoneMuted: false
    property bool microphoneAvailable: true
    property bool keepAwakeEnabled: false
    property bool screenshotBusy: false
    readonly property real controlScale: Math.min(1, width / 296)
    readonly property alias surface: surface
    property bool expanded: false
    property bool peekOnHover: true
    property bool dashboardHovered: false
    property real pixelsPerMillimeter: 96 / 25.4
    property bool pointerVisited: false
    readonly property bool hovered: hoverTracker.hovered
    readonly property bool revealed: expanded || (peekOnHover && hovered)
    signal toggled()
    signal dismissed()
    signal dndToggleRequested()
    signal recordingToggleRequested()
    signal nightLightToggleRequested()
    signal microphoneToggleRequested()
    signal keepAwakeToggleRequested()
    signal screenshotRequested()

    implicitWidth: Math.round(80 * pixelsPerMillimeter)
    implicitHeight: Math.max(0, barHeight)
    clip: true

    onExpandedChanged: pointerVisited = expanded && (hovered || dashboardHovered)
    onHoveredChanged: { if (expanded && hovered) pointerVisited = true; }
    onDashboardHoveredChanged: { if (expanded && dashboardHovered) pointerVisited = true; }

    Timer {
        interval: 160
        running: root.expanded && root.pointerVisited && !root.hovered && !root.dashboardHovered
        onTriggered: root.dismissed()
    }

    // Keep the hover target in the taskbar even while the surface is hidden.
    HoverTracker {
        id: hoverTracker
    }

    Item {
        id: surface
        objectName: "dashboardNotchSurface"

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.width
        height: root.revealed ? root.height / 2 : 0
        visible: height > 0
        clip: true

        Behavior on height { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }

        Rectangle {
            id: handle
            anchors.centerIn: parent
            width: 24 * root.controlScale
            height: 2
            radius: 1
            color: root.handleColour
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton
            cursorShape: Qt.PointingHandCursor
            onClicked: root.toggled()
        }

        NotchToggle {
            id: dndButton
            objectName: "dashboardNotchDnd"
            anchors.left: handle.right
            anchors.leftMargin: 16 * root.controlScale
            anchors.verticalCenter: parent.verticalCenter
            symbol: root.dndEnabled ? "notifications_off" : "notifications"
            checked: root.dndEnabled
            accent: root.activeColour
            label: checked ? "Disable Do not disturb" : "Enable Do not disturb"
            onTriggered: root.dndToggleRequested()
        }

        NotchToggle {
            id: nightLightButton
            objectName: "dashboardNotchNightLight"
            anchors.left: dndButton.right
            anchors.leftMargin: 8 * root.controlScale
            anchors.verticalCenter: parent.verticalCenter
            symbol: root.nightLightEnabled ? "nightlight" : "light_mode"
            checked: root.nightLightEnabled
            accent: root.nightLightColour
            label: checked ? "Night mode on: disable blue-light filter" : "Day mode: enable blue-light filter"
            actionEnabled: !root.nightLightBusy
            onTriggered: root.nightLightToggleRequested()
        }

        NotchToggle {
            objectName: "dashboardNotchMicrophone"
            anchors.right: screenshotButton.left
            anchors.rightMargin: 8 * root.controlScale
            anchors.verticalCenter: parent.verticalCenter
            symbol: root.microphoneMuted ? "mic_off" : "mic"
            checked: root.microphoneMuted && root.microphoneAvailable
            accent: root.recordingColour
            actionEnabled: root.microphoneAvailable
            label: !root.microphoneAvailable ? "No microphone available" : checked ? "Unmute microphone" : "Mute microphone"
            onTriggered: root.microphoneToggleRequested()
        }

        NotchToggle {
            id: recorderButton
            objectName: "dashboardNotchRecorder"
            anchors.right: handle.left
            anchors.rightMargin: 16 * root.controlScale
            anchors.verticalCenter: parent.verticalCenter
            symbol: root.recordingActive ? "stop_circle" : "screen_record"
            checked: root.recordingActive
            accent: root.recordingColour
            label: checked ? "Stop screen recording" : "Start screen recording"
            onTriggered: root.recordingToggleRequested()
        }

        NotchToggle {
            id: screenshotButton
            objectName: "dashboardNotchScreenshot"
            anchors.right: recorderButton.left
            anchors.rightMargin: 8 * root.controlScale
            anchors.verticalCenter: parent.verticalCenter
            symbol: "screenshot_region"
            checked: false
            isToggle: false
            accent: root.activeColour
            actionEnabled: !root.screenshotBusy
            label: "Screenshot a region"
            onTriggered: root.screenshotRequested()
        }

        NotchToggle {
            objectName: "dashboardNotchKeepAwake"
            anchors.left: nightLightButton.right
            anchors.leftMargin: 8 * root.controlScale
            anchors.verticalCenter: parent.verticalCenter
            symbol: "coffee"
            checked: root.keepAwakeEnabled
            accent: root.activeColour
            label: checked ? "Disable Keep awake" : "Enable Keep awake"
            onTriggered: root.keepAwakeToggleRequested()
        }
    }

    component NotchToggle: MouseArea {
        id: button

        required property string symbol
        required property string label
        required property bool checked
        required property color accent
        property bool actionEnabled: true
        property bool isToggle: true
        signal triggered()

        function activate(): void {
            if (actionEnabled) triggered();
        }

        width: 32 * root.controlScale
        height: surface.height
        opacity: actionEnabled ? 1 : 0.4
        Behavior on opacity { NumberAnimation { duration: 140 } }
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        cursorShape: Qt.PointingHandCursor
        activeFocusOnTab: true
        Accessible.role: Accessible.Button
        Accessible.name: label
        Accessible.checkable: isToggle
        Accessible.checked: checked
        Accessible.onPressAction: activate()
        onClicked: activate()
        Keys.onSpacePressed: activate()
        Keys.onReturnPressed: activate()

        Rectangle {
            anchors.fill: parent
            anchors.margins: 2
            radius: height / 2
            color: button.checked ? button.accent : root.handleColour
            opacity: button.pressed ? 0.28 : button.checked ? 0.2 : button.containsMouse ? 0.08 : 0
            Behavior on color { ColorAnimation { duration: 160 } }
            Behavior on opacity { NumberAnimation { duration: 140 } }
        }

        Text {
            id: glyph
            anchors.centerIn: parent
            text: button.symbol
            font: root.iconFont
            scale: root.controlScale * (button.pressed ? 0.9 : button.checked ? 1.04 : 1)
            color: button.checked ? button.accent : root.handleColour
            Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: 160 } }
            Behavior on text {
                SequentialAnimation {
                    NumberAnimation { target: glyph; property: "opacity"; to: 0; duration: 60 }
                    PropertyAction {}
                    NumberAnimation { target: glyph; property: "opacity"; to: 1; duration: 100 }
                }
            }
        }

    }
}
