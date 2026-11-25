pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Services.UPower
import Caelestia.Config
import Caelestia.Services
import qs.services

Scope {
    id: root

    readonly property bool hasPlayer: Players.list.some(p => p.isPlaying)
    readonly property bool isCharging: !UPower.onBattery
    readonly property bool enabled: {
        if (GlobalConfig.general.idle.inhibitWhenAudio && hasPlayer)
            return false;
        if (GlobalConfig.general.idle.inhibitWhenCharging && isCharging)
            return false;
        return true;
    }

    function handleIdleAction(action: var): void {
        if (!action)
            return;

        // There is no lock screen; ignore the old default "lock" action so a stale config cannot dispatch it.
        if (action === "lock" || action === "unlock")
            return;

        if (typeof action === "string")
            Hypr.dispatch(Hypr.usingLua && ["dpms off", "dpms on"].includes(action) ? `hl.dsp.dpms({ action = "${action === "dpms off" ? "disable" : "enable"}" })` : action);
        else if (!SessionManager.exec(action))
            Quickshell.execDetached(action);
    }

    Connections {
        function onResumed(): void {
            // Restore display power even if the idle monitor remains idle after sleep.
            root.handleIdleAction("dpms on");
        }

        target: SessionManager
    }

    Variants {
        model: GlobalConfig.general.idle.timeouts.values

        IdleMonitor {
            required property var modelData

            enabled: {
                if (!root.enabled || !(modelData.enabled ?? true))
                    return false;
                if (modelData.inhibitWhenAudio && root.hasPlayer)
                    return false;
                if (modelData.inhibitWhenCharging && root.isCharging)
                    return false;
                return true;
            }
            timeout: modelData.timeout
            respectInhibitors: modelData.respectInhibitors ?? true
            onIsIdleChanged: root.handleIdleAction(isIdle ? modelData.idleAction : modelData.returnAction)
        }
    }
}
