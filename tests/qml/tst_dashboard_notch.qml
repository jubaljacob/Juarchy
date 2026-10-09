import QtQuick
import QtTest
import "../../shell/modules/dashboard" as Dashboard

TestCase {
    name: "DashboardNotch"
    when: windowShown
    visible: true
    width: 600
    height: 240

    Dashboard.Notch {
        id: notch
        x: 230
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
    }

    Item {
        id: dashboard
        x: 170
        y: notch.barHeight
        width: 310
        height: 100
        visible: notch.expanded

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
        }

        Dashboard.HoverTracker { id: dashboardHover }
    }

    SignalSpy { id: clicks; target: notch; signalName: "toggled" }
    SignalSpy { id: dndClicks; target: notch; signalName: "dndToggleRequested" }
    SignalSpy { id: recordingClicks; target: notch; signalName: "recordingToggleRequested" }
    SignalSpy { id: screenshotClicks; target: notch; signalName: "screenshotRequested" }
    SignalSpy { id: microphoneClicks; target: notch; signalName: "microphoneToggleRequested" }

    function init() {
        notch.expanded = false;
        notch.peekOnHover = true;
        notch.dndEnabled = false;
        notch.recordingActive = false;
        notch.nightLightEnabled = false;
        notch.nightLightBusy = false;
        notch.microphoneMuted = false;
        notch.microphoneAvailable = true;
        notch.keepAwakeEnabled = false;
        notch.screenshotBusy = false;
        notch.pixelsPerMillimeter = 96 / 25.4;
        mouseMove(notch, -100, 100);
        wait(200);
        clicks.clear();
        dndClicks.clear();
        recordingClicks.clear();
        screenshotClicks.clear();
        microphoneClicks.clear();
    }

    function test_microphone_icon_tracks_state_and_unavailable_input_does_not_activate() {
        mouseMove(notch, notch.width / 2, 3);
        tryCompare(findChild(notch, "dashboardNotchSurface"), "height", notch.barHeight / 2);
        const mic = findChild(notch, "dashboardNotchMicrophone");
        compare(mic.symbol, "mic");
        mouseClick(mic, mic.width / 2, mic.height / 2);
        compare(notch.microphoneMuted, true);
        compare(mic.symbol, "mic_off");
        compare(mic.checked, true);
        mouseClick(mic, mic.width / 2, mic.height / 2);
        compare(notch.microphoneMuted, false);
        compare(mic.symbol, "mic");
        // Reflect changes originating in another audio control.
        notch.microphoneMuted = true;
        compare(mic.checked, true);
        notch.microphoneAvailable = false;
        mouseClick(mic, mic.width / 2, mic.height / 2);
        compare(microphoneClicks.count, 2);
        compare(mic.checked, false);
        compare(notch.expanded, false);
        compare(clicks.count, 0);
    }

    function test_keep_awake_and_screenshot_work_without_opening_dashboard() {
        mouseMove(notch, notch.width / 2, 3);
        tryCompare(findChild(notch, "dashboardNotchSurface"), "height", notch.barHeight / 2);
        const awake = findChild(notch, "dashboardNotchKeepAwake");
        const screenshot = findChild(notch, "dashboardNotchScreenshot");
        compare(awake.checked, false);
        mouseClick(awake, awake.width / 2, awake.height / 2);
        compare(notch.keepAwakeEnabled, true);
        compare(awake.checked, true);
        mouseClick(screenshot, screenshot.width / 2, screenshot.height / 2);
        compare(screenshotClicks.count, 1);
        compare(screenshot.isToggle, false);
        compare(screenshot.checked, false);
        notch.screenshotBusy = true;
        mouseClick(screenshot, screenshot.width / 2, screenshot.height / 2);
        compare(screenshotClicks.count, 1);
        mouseClick(awake, awake.width / 2, awake.height / 2);
        compare(notch.keepAwakeEnabled, false);
        compare(notch.expanded, false);
        compare(clicks.count, 0);
    }

    function test_all_six_controls_fit_inside_notch_at_different_display_densities() {
        const names = ["Microphone", "Screenshot", "Recorder", "Dnd", "NightLight", "KeepAwake"];
        for (const density of [2.5, 96 / 25.4, 5]) {
            notch.pixelsPerMillimeter = density;
            wait(1);
            let previousRight = 0;
            for (const name of names) {
                const control = findChild(notch, "dashboardNotch" + name);
                verify(control.x >= previousRight);
                verify(control.x + control.width <= notch.width);
                previousRight = control.x + control.width;
            }
            compare(notch.width, Math.round(80 * density));
        }
    }

    function test_quick_toggles_are_either_side_of_handle_and_independent() {
        mouseMove(notch, notch.width / 2, 3);
        tryCompare(findChild(notch, "dashboardNotchSurface"), "height", notch.barHeight / 2);
        const dnd = findChild(notch, "dashboardNotchDnd");
        const recorder = findChild(notch, "dashboardNotchRecorder");
        verify(recorder.x + recorder.width < notch.width / 2);
        verify(dnd.x > notch.width / 2);
        compare(dnd.symbol, "notifications");
        mouseClick(dnd, dnd.width / 2, dnd.height / 2);
        compare(notch.dndEnabled, true);
        compare(dnd.checked, true);
        compare(dnd.symbol, "notifications_off");
        compare(notch.expanded, false);
        compare(notch.recordingActive, false);
        mouseClick(recorder, recorder.width / 2, recorder.height / 2);
        compare(notch.recordingActive, true);
        compare(recorder.symbol, "stop_circle");
        compare(notch.expanded, false);
        mouseClick(recorder, recorder.width / 2, recorder.height / 2);
        compare(notch.recordingActive, false);
        compare(recorder.symbol, "screen_record");
        mouseClick(dnd, dnd.width / 2, dnd.height / 2);
        compare(notch.dndEnabled, false);
        compare(dnd.symbol, "notifications");
        compare(dndClicks.count, 2);
        compare(recordingClicks.count, 2);
        compare(clicks.count, 0);
        mouseClick(notch, notch.width / 2, 20);
        compare(notch.expanded, true);
        compare(clicks.count, 1);
    }

    function test_night_light_toggle_is_independent_and_ignores_clicks_while_busy() {
        mouseMove(notch, notch.width / 2, 3);
        tryCompare(findChild(notch, "dashboardNotchSurface"), "height", notch.barHeight / 2);
        const night = findChild(notch, "dashboardNotchNightLight");
        const dnd = findChild(notch, "dashboardNotchDnd");
        verify(night.x > dnd.x + dnd.width);
        compare(night.symbol, "light_mode");
        mouseClick(night, night.width / 2, night.height / 2);
        compare(notch.nightLightEnabled, true);
        compare(night.symbol, "nightlight");
        compare(night.checked, true);
        compare(notch.expanded, false);
        compare(notch.dndEnabled, false);
        compare(notch.recordingActive, false);
        notch.nightLightBusy = true;
        mouseClick(night, night.width / 2, night.height / 2);
        compare(notch.nightLightEnabled, true);
        compare(clicks.count, 0);
        notch.nightLightBusy = false;
        mouseClick(night, night.width / 2, night.height / 2);
        compare(notch.nightLightEnabled, false);
        compare(night.symbol, "light_mode");
    }

    function test_hover_stays_within_taskbar_and_does_not_open() {
        const surface = findChild(notch, "dashboardNotchSurface");
        compare(surface.height, 0);
        mouseMove(notch, notch.width / 2, 3);
        tryCompare(notch, "hovered", true);
        for (let i = 0; i < 10; i++) {
            verify(surface.height <= notch.barHeight / 2);
            wait(20);
        }
        compare(surface.height, 24);
        compare(notch.expanded, false);
        compare(clicks.count, 0);
    }

    function test_click_opens_and_second_click_closes() {
        mouseMove(notch, notch.width / 2, 3);
        wait(200);
        mouseClick(notch, notch.width / 2, 20);
        compare(notch.expanded, true);
        mouseClick(notch, notch.width / 2, 20);
        compare(notch.expanded, false);
        compare(clicks.count, 2);
    }

    function test_hover_preview_retracts_each_time_pointer_leaves() {
        const surface = findChild(notch, "dashboardNotchSurface");
        for (let i = 0; i < 3; i++) {
            mouseMove(notch, notch.width / 2, 3);
            tryCompare(surface, "height", notch.barHeight / 2);
            mouseMove(notch, notch.width / 2, notch.barHeight + 20);
            tryCompare(notch, "hovered", false);
            tryCompare(surface, "height", 0);
            compare(notch.expanded, false);
        }
    }

    function test_notch_is_eight_centimeters_wide_at_rest_and_on_hover() {
        const surface = findChild(notch, "dashboardNotchSurface");
        compare(notch.width, Math.round(80 * notch.pixelsPerMillimeter));
        compare(surface.width, notch.width);
        mouseMove(notch, notch.width / 2, 3);
        wait(200);
        compare(surface.width, notch.width);
    }

    function test_leaving_closes_dashboard_and_retracts_notch() {
        mouseMove(notch, notch.width / 2, 3);
        wait(200);
        mouseClick(notch, notch.width / 2, 20);
        compare(notch.expanded, true);
        mouseMove(notch, -100, 100);
        tryCompare(notch, "expanded", false);
        tryCompare(findChild(notch, "dashboardNotchSurface"), "height", 0);
    }

    function test_moving_into_dashboard_keeps_it_open() {
        mouseMove(notch, notch.width / 2, 3);
        wait(200);
        mouseClick(notch, notch.width / 2, 20);
        mouseMove(dashboard, dashboard.width / 2, 30);
        tryCompare(notch, "dashboardHovered", true);
        wait(250);
        compare(notch.expanded, true);
        mouseMove(dashboard, dashboard.width + 20, 30);
        tryCompare(notch, "dashboardHovered", false);
        tryCompare(notch, "expanded", false);
        tryCompare(findChild(notch, "dashboardNotchSurface"), "height", 0);
    }

    function test_window_area_does_not_trigger_notch() {
        mouseMove(notch, notch.width / 2, notch.barHeight + 10);
        mouseClick(notch, notch.width / 2, notch.barHeight + 10);
        compare(notch.hovered, false);
        compare(notch.expanded, false);
        compare(clicks.count, 0);
    }

    function test_hover_option_does_not_enable_full_dashboard() {
        notch.peekOnHover = false;
        mouseMove(notch, notch.width / 2, 3);
        wait(200);
        compare(notch.hovered, true);
        compare(notch.revealed, false);
        compare(notch.expanded, false);
        mouseClick(notch, notch.width / 2, 3);
        compare(notch.expanded, false);
        compare(clicks.count, 0);
    }
}
