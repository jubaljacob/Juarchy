pragma ComponentBehavior: Bound

import QtQuick
import Quickshell

Item {
    id: root
    required property ShellScreen screen
    required property bool fullscreen

    implicitWidth: content.implicitHeight
    implicitHeight: content.implicitWidth

    Workspaces {
        id: content
        screen: root.screen
        fullscreen: root.fullscreen
        width: implicitWidth
        height: implicitHeight
        x: (root.width - width) / 2
        y: (root.height - height) / 2
        rotation: -90
    }
}
