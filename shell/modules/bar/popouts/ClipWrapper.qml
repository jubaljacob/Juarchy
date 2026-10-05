pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import qs.components
import qs.modules.bar.popouts

Item {
    id: root

    required property ShellScreen screen
    required property real borderThickness

    readonly property alias content: content
    property real offsetScale: 1
    readonly property real clippedOffset: Math.max(0, Math.min(1, offsetScale))

    function updateVisibility(restartOpening: bool): void {
        const shown = content.isDetached || content.hasCurrent;
        reveal.stop();
        if (shown && restartOpening && !content.isDetached)
            offsetScale = 1;
        reveal.to = shown ? 0 : 1;
        reveal.start();
    }

    Component.onCompleted: offsetScale = content.isDetached || content.hasCurrent ? 0 : 1

    visible: width > 0 && height > 0
    clip: true
    implicitWidth: content.implicitWidth
    implicitHeight: content.implicitHeight * (1 - clippedOffset)

    x: {
        if (content.isDetached)
            return (parent.width - content.nonAnimWidth) / 2;
        return Math.max(0, Math.min(parent.width - content.nonAnimWidth, content.currentCenter - borderThickness - content.nonAnimWidth / 2));
    }
    y: content.isDetached ? (parent.height - content.nonAnimHeight) / 2 : 0

    Anim {
        id: reveal
        target: root
        property: "offsetScale"
        duration: content.animLength
        easing: content.animCurve
    }

    Connections {
        target: content
        function onHasCurrentChanged(): void {
            root.updateVisibility(content.hasCurrent);
        }
        function onRevealRequested(): void {
            if (content.hasCurrent && !content.isDetached)
                root.updateVisibility(true);
        }
        function onIsDetachedChanged(): void {
            root.updateVisibility(false);
        }
    }

    Behavior on x {
        enabled: content.isDetached
        Anim {
            duration: content.animLength
            easing: content.animCurve
        }
    }

    Behavior on y {
        Anim {
            duration: content.animLength
            easing: content.animCurve
        }
    }

    Wrapper {
        id: content
        screen: root.screen
        offsetScale: root.clippedOffset
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: (-implicitHeight - 5) * root.clippedOffset
    }
}
