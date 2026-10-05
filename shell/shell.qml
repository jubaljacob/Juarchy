//@ pragma DefaultEnv QS_NO_RELOAD_POPUP=1
//@ pragma DefaultEnv QS_DROP_EXPENSIVE_FONTS=1
//@ pragma DefaultEnv QSG_RENDER_LOOP=threaded
//@ pragma DefaultEnv QT_QUICK_FLICKABLE_WHEEL_DECELERATION=10000

import "modules"
import "modules/drawers"
import "modules/background"
import "modules/areapicker"
import "modules/lock"
import QtQuick
import Quickshell
import Quickshell.Io
import qs.services

ShellRoot {
    id: root

    settings.watchFiles: false

    IpcHandler {
        target: "jubalMenu"
        function toggle(): void {
            const state = ShellState.forActive();
            if (!state) return;
            if (!state.launcher) MenuRequest.request("", state);
            state.launcher = !state.launcher;
        }
        function open(section: string): void {
            const state = ShellState.forActive();
            if (!state) return;
            MenuRequest.request(section, state);
            state.launcher = true;
        }
        function reload(): void {
            Quickshell.reload(false);
        }
    }

    Binding {
        target: ShellState
        property: "shellRoot"
        value: root
    }

    GSFLoader {}
    ServiceLoader {}

    Background {}
    Drawers {}
    AreaPicker {}
    Lock {
        id: lock
    }

    Shortcuts {}
    BatteryMonitor {}
    IdleMonitors {
        lock: lock
    }
}
