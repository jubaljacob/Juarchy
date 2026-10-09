import QtQuick
import QtTest
import "../../shell/modules/dashboard" as Dashboard

TestCase {
    name: "DashboardNotchPlacement"
    when: windowShown
    visible: true
    width: 600
    height: 240
    property int screenshotCount: 0

    MouseArea {
        id: interactions
        anchors.fill: parent
        hoverEnabled: true

        Item {
            id: panels
            x: 0
            y: 48
            width: parent.width
            height: parent.height - y

            Dashboard.Notch {
                id: notch
                anchors.horizontalCenter: parent.horizontalCenter
                y: -48
                z: 10
                barHeight: 48
                handleColour: "#eeeeee"
                dashboardHovered: dashboardHover.hovered
                onToggled: expanded = !expanded
                onDismissed: expanded = false
                onDndToggleRequested: dndEnabled = !dndEnabled
                onRecordingToggleRequested: recordingActive = !recordingActive
                onNightLightToggleRequested: nightLightEnabled = !nightLightEnabled
                onMicrophoneToggleRequested: microphoneMuted = !microphoneMuted
                onKeepAwakeToggleRequested: keepAwakeEnabled = !keepAwakeEnabled
                onScreenshotRequested: screenshotCount++
            }

            Item {
                id: dashboard
                anchors.horizontalCenter: parent.horizontalCenter
                width: 400
                height: 100
                visible: notch.expanded

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                }

                Dashboard.HoverTracker { id: dashboardHover }
            }
        }

        Item {
            width: parent.width
            height: 48
        }

        Dashboard.HoverTracker { id: observer }

    }

    function test_hover_then_click_in_drawer_layout() {
        mouseMove(interactions, 20, 100);
        const surface = findChild(notch, "dashboardNotchSurface");
        compare(surface.height, 0);
        mouseMove(interactions, width / 2, 3);
        tryCompare(notch, "hovered", true);
        tryCompare(surface, "height", notch.barHeight / 2);
        compare(observer.hovered, true);
        compare(notch.expanded, false);
        mouseClick(interactions, width / 2, 20);
        compare(notch.expanded, true);
        mouseMove(dashboard, dashboard.width / 2, 20);
        tryCompare(notch, "dashboardHovered", true);
        wait(250);
        compare(notch.expanded, true);
        compare(observer.hovered, true);
        compare(observer.point.position.y, 68);
        mouseMove(interactions, 20, 100);
        tryCompare(notch, "expanded", false);
        tryCompare(surface, "height", 0);
    }

    function test_quick_toggles_receive_clicks_in_drawer_layout() {
        notch.expanded = false;
        notch.dndEnabled = false;
        notch.recordingActive = false;
        notch.nightLightEnabled = false;
        notch.microphoneMuted = false;
        notch.keepAwakeEnabled = false;
        screenshotCount = 0;
        mouseMove(interactions, width / 2, 3);
        tryCompare(findChild(notch, "dashboardNotchSurface"), "height", notch.barHeight / 2);
        for (const suffix of ["Microphone", "NightLight", "Dnd", "Recorder", "Screenshot", "KeepAwake"]) {
            const name = "dashboardNotch" + suffix;
            const button = findChild(notch, name);
            const position = button.mapToItem(interactions, button.width / 2, button.height / 2);
            mouseClick(interactions, position.x, position.y);
            compare(notch.expanded, false);
        }
        compare(notch.dndEnabled, true);
        compare(notch.recordingActive, true);
        compare(notch.nightLightEnabled, true);
        compare(notch.microphoneMuted, true);
        compare(notch.keepAwakeEnabled, true);
        compare(screenshotCount, 1);
        mouseClick(interactions, width / 2, 20);
        compare(notch.expanded, true);
        mouseMove(interactions, 20, 100);
        tryCompare(notch, "expanded", false);
    }
}
