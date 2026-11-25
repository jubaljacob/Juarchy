import QtQuick
import QtQuick.Effects
import Quickshell
import qs.services

// An AI agent's logo. Claude's keeps its own colour; Codex's is a plain white
// shape, so it takes the colour it is given and follows the theme.
Item {
    id: root

    required property string agent
    property int size: 16
    property color tint: Colours.palette.m3onSurface
    readonly property bool tinted: agent === "codex"

    implicitWidth: size
    implicitHeight: size

    Image {
        id: mark

        anchors.fill: parent
        source: Quickshell.shellPath(`assets/agents/${root.agent}.svg`)
        sourceSize: Qt.size(root.size * 2, root.size * 2)
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        visible: !root.tinted
    }

    MultiEffect {
        anchors.fill: parent
        source: mark
        visible: root.tinted
        colorization: 1
        colorizationColor: root.tint
    }
}
