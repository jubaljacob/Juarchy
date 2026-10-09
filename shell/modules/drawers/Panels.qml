import QtQuick
import Quickshell
import Quickshell.Io
import Caelestia.Config
import qs.components
import qs.components.misc
import qs.services
import qs.modules.bar as Bar
import qs.modules.dashboard as Dashboard
import qs.modules.groupedlauncher as Launcher
import qs.modules.notifications as Notifications
import qs.modules.osd as Osd
import qs.modules.session as Session
import qs.modules.sidebar as Sidebar
import qs.modules.utilities as Utilities
import qs.modules.bar.popouts as BarPopouts
import qs.modules.utilities.toasts as Toasts

Item {
    id: root

    required property ShellScreen screen
    required property ScreenState screenState
    required property Bar.BarWrapper bar
    required property real borderThickness
    readonly property bool dashboardHovered: dashboard.hovered
    readonly property bool screenshotBusy: screenshotDelay.running || screenshotProcess.running

    function captureScreenshot(): void {
        if (screenshotBusy) return;
        screenState.dashboard = false;
        screenshotDelay.start();
    }

    readonly property alias osd: osd
    readonly property alias osdWrapper: osdWrapper
    readonly property alias notifications: notifications
    readonly property alias session: session
    readonly property alias sessionWrapper: sessionWrapper
    readonly property alias launcher: launcher
    readonly property alias dashboard: dashboard
    readonly property alias notch: notch
    readonly property alias popouts: popoutsWrapper.content
    readonly property alias popoutsWrapper: popoutsWrapper
    readonly property alias utilities: utilities
    readonly property alias toasts: toasts
    readonly property alias sidebar: sidebar

    anchors.fill: parent
    anchors.margins: borderThickness
    anchors.topMargin: bar.implicitHeight

    Item {
        id: osdWrapper

        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: sessionWrapper.anchors.rightMargin + session.width * (1 - session.offsetScale)
        clip: sidebar.visible || session.visible

        implicitWidth: osd.implicitWidth * (1 - osd.offsetScale)
        implicitHeight: osd.implicitHeight

        Osd.Wrapper {
            id: osd

            screen: root.screen
            screenState: root.screenState
            sidebarOrSessionVisible: sidebar.visible || session.visible

            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
        }
    }

    Notifications.Wrapper {
        id: notifications

        screenState: root.screenState
        sidebarPanel: sidebar
        osdPanel: osdWrapper
        sessionPanel: sessionWrapper
        utilitiesPanel: utilities

        anchors.top: parent.top
        anchors.right: parent.right
    }

    Item {
        id: sessionWrapper

        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: sidebar.width * (1 - sidebar.offsetScale)
        clip: sidebar.visible

        implicitWidth: session.implicitWidth * (1 - session.offsetScale)
        implicitHeight: session.implicitHeight

        Session.Wrapper {
            id: session

            screenState: root.screenState
            sidebarVisible: sidebar.visible

            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
        }
    }

    Launcher.Wrapper {
        id: launcher

        screen: root.screen
        screenState: root.screenState
        panels: root

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
    }

    Dashboard.Wrapper {
        id: dashboard

        screenState: root.screenState

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: (-implicitHeight - root.bar.implicitHeight - 5) * offsetScale
    }

    Dashboard.Notch {
        id: notch
        anchors.horizontalCenter: parent.horizontalCenter
        y: -root.bar.implicitHeight
        z: 10
        barHeight: root.bar.implicitHeight
        pixelsPerMillimeter: root.screen.physicalPixelDensity > 0 && root.screen.devicePixelRatio > 0
            ? root.screen.physicalPixelDensity / root.screen.devicePixelRatio : 96 / 25.4
        handleColour: Colours.palette.m3onSurfaceVariant
        activeColour: Colours.palette.m3primary
        recordingColour: Colours.palette.m3error
        iconFont: Tokens.font.icon.small
        dndEnabled: Notifs.dnd
        recordingActive: Recorder.running
        nightLightEnabled: NightLight.enabled
        nightLightBusy: NightLight.busy
        microphoneMuted: Audio.sourceMuted
        microphoneAvailable: !!Audio.source?.ready && !!Audio.source?.audio
        keepAwakeEnabled: IdleInhibitor.enabled
        screenshotBusy: root.screenshotBusy
        visible: Config.dashboard.enabled && root.bar.shouldBeVisible && !root.screenshotBusy
        expanded: root.screenState.dashboard
        dashboardHovered: root.dashboardHovered
        peekOnHover: Config.dashboard.showOnHover
        onToggled: root.screenState.dashboard = !root.screenState.dashboard
        onDismissed: root.screenState.dashboard = false
        onDndToggleRequested: Notifs.dnd = !Notifs.dnd
        onNightLightToggleRequested: NightLight.toggle()
        onMicrophoneToggleRequested: {
            if (Audio.source?.ready && Audio.source?.audio)
                Audio.source.audio.muted = !Audio.sourceMuted;
        }
        onKeepAwakeToggleRequested: IdleInhibitor.enabled = !IdleInhibitor.enabled
        onScreenshotRequested: root.captureScreenshot()
        onRecordingToggleRequested: {
            if (Recorder.running)
                Recorder.stop();
            else
                Recorder.start();
        }
    }

    Timer {
        id: screenshotDelay
        interval: 300
        onTriggered: screenshotProcess.running = true
    }

    Process {
        id: screenshotProcess
        command: [`${Quickshell.env("HOME")}/.local/bin/juarchy-screenshot`]
    }

    Loader {
        active: notch.visible && notch.revealed
        sourceComponent: Ref {
            service: NightLight
        }
    }

    Loader {
        active: notch.visible && (notch.revealed || Recorder.running)
        sourceComponent: Ref {
            service: Recorder
        }
    }

    BarPopouts.ClipWrapper {
        id: popoutsWrapper

        screen: root.screen
        borderThickness: root.borderThickness
    }

    Utilities.Wrapper {
        id: utilities

        screenState: root.screenState
        sidebar: sidebar
        popouts: popoutsWrapper.content

        anchors.bottom: parent.bottom
        anchors.right: parent.right
    }

    Toasts.Toasts {
        id: toasts

        anchors.bottom: sidebar.visible || !utilities.visible ? parent.bottom : utilities.top
        anchors.right: sidebar.left
        anchors.margins: Tokens.padding.medium
    }

    Sidebar.Wrapper {
        id: sidebar

        screenState: root.screenState

        anchors.top: notifications.bottom
        anchors.bottom: utilities.visible ? utilities.top : parent.bottom
        anchors.right: parent.right
        anchors.topMargin: -notifications.anchors.topMargin
    }
}
