pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import Quickshell.Wayland
import qs.services
import qs.components.containers

Scope {
    id: root
    property bool opened: false
    property ShellScreen targetScreen
    // Bound, short-lived previews survive closing the overlay; nothing is written to disk.
    property var webCache: ({entries: []})

    function toggle() {
        if (opened) { opened = false; return; }
        const state = ShellState.forActive();
        if (state) state.launcher = false;
        targetScreen = state ? state.modelData : Quickshell.screens[0];
        opened = true;
    }

    function toggleMenu() {
        opened = false;
        const state = ShellState.forActive();
        if (!state) return;
        if (!state.launcher) MenuRequest.request("", state);
        state.launcher = !state.launcher;
    }

    // Replace stale bindings in the compositor when starting or reloading the shell.
    // These use native global shortcuts rather than spawning launcher helper scripts.
    function syncBindings() {
        if (!Hypr.usingLua) return;
        Hypr.extras.batchMessage([
            'eval hl.layer_rule({ name = "juarchy-spotlight-blur", match = { namespace = "^caelestia-spotlight$" }, blur = true, ignore_alpha = 0, xray = false })',
            'eval hl.unbind("SUPER + SPACE")',
            'eval hl.unbind("SUPER + ALT + SPACE")',
            'eval hl.bind("SUPER + SPACE", hl.dsp.global("juarchy:spotlight"), { description = "Spotlight search" })',
            'eval hl.bind("SUPER + ALT + SPACE", hl.dsp.global("juarchy:menu"), { description = "Desktop menu" })'
        ]);
    }

    Component.onCompleted: Qt.callLater(syncBindings)
    Connections {
        target: Hypr
        function onConfigReloaded(): void { root.syncBindings(); }
        function onUsingLuaChanged(): void { root.syncBindings(); }
    }

    GlobalShortcut {
        appid: "juarchy"
        name: "spotlight"
        description: "Toggle Spotlight search"
        onPressed: root.toggle()
    }
    GlobalShortcut {
        appid: "juarchy"
        name: "menu"
        description: "Toggle desktop menu"
        onPressed: root.toggleMenu()
    }

    IpcHandler {
        target: "spotlight"
        function toggle(): void { root.toggle(); }
        function close(): void { root.opened = false; }
    }

    LazyLoader {
        active: root.opened
        StyledWindow {
            id: win
            name: "spotlight"
            screen: root.targetScreen
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.exclusionMode: ExclusionMode.Ignore
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
            anchors.top: true
            anchors.bottom: true
            anchors.left: true
            anchors.right: true

            // Blur the rounded card, leaving the surrounding desktop clear.
            BackgroundEffect.blurRegion: Region {
                x: content.x
                y: content.y
                width: content.width
                height: content.height
                radius: content.radius
            }

            MouseArea {
                anchors.fill: parent
                onClicked: root.opened = false
            }
            Content {
                id: content
                webCache: root.webCache
                width: Math.min(720, parent.width - 32)
                height: Math.min(implicitHeight, parent.height - 40)
                anchors.centerIn: parent
                onClose: root.opened = false
            }
        }
    }
}
