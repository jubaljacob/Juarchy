pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import Caelestia.Config
import qs.components.misc

Singleton {
    id: root

    property list<var> ddcMonitors: []
    readonly property var ddcMonitorMap: {
        const map = {};
        for (const m of ddcMonitors)
            map[m.connector] = m;
        return map;
    }
    readonly property list<Monitor> monitors: variants.instances // qmllint disable incompatible-type
    property bool appleDisplayPresent: false
    // Prefer Intel's panel (an NVIDIA backlight can be listed first), otherwise use
    // whichever backlight the kernel exposes, e.g. amdgpu_bl1 on AMD laptops.
    readonly property string selectBacklight: "dev=intel_backlight; [ -d /sys/class/backlight/$dev ] || dev=$(ls /sys/class/backlight | head -n 1);"

    function getMonitorForScreen(screen: ShellScreen): var {
        return monitors.find(m => m.modelData === screen); // qmllint disable missing-property
    }

    function getMonitor(query: string): var {
        if (query === "active") {
            return monitors.find(m => Hypr.monitorFor(m.modelData)?.focused); // qmllint disable missing-property
        }

        if (query.startsWith("model:")) {
            const model = query.slice(6);
            return monitors.find(m => m.modelData.model === model); // qmllint disable missing-property
        }

        if (query.startsWith("serial:")) {
            const serial = query.slice(7);
            return monitors.find(m => m.modelData.serialNumber === serial); // qmllint disable missing-property
        }

        if (query.startsWith("id:")) {
            const id = parseInt(query.slice(3), 10);
            return monitors.find(m => Hypr.monitorFor(m.modelData)?.id === id); // qmllint disable missing-property
        }

        return monitors.find(m => m.modelData.name === query); // qmllint disable missing-property
    }

    function increaseBrightness(): void {
        const monitor = getMonitor("active");
        if (monitor)
            monitor.setBrightness(monitor.brightness + GlobalConfig.services.brightnessIncrement);
    }

    function decreaseBrightness(): void {
        const monitor = getMonitor("active");
        if (monitor)
            monitor.setBrightness(monitor.brightness - GlobalConfig.services.brightnessIncrement);
    }

    onMonitorsChanged: {
        ddcMonitors = [];
        ddcProc.running = true;
    }

    Variants {
        id: variants

        model: Quickshell.screens // Don't respect excluded screens cause ipc

        Monitor {}
    }

    Process {
        running: true
        command: ["sh", "-c", "asdbctl get"] // To avoid warnings if asdbctl is not installed
        stdout: StdioCollector {
            onStreamFinished: root.appleDisplayPresent = text.trim().length > 0
        }
    }

    Process {
        id: ddcProc

        command: ["ddcutil", "detect", "--brief"]
        stdout: StdioCollector {
            onStreamFinished: root.ddcMonitors = text.trim().split("\n\n").filter(d => d.startsWith("Display ")).map(d => ({
                        busNum: d.match(/I2C bus:[ ]*\/dev\/i2c-([0-9]+)/)[1],
                        connector: d.match(/DRM connector:\s+(.*)/)[1].replace(/^card\d+-/, "") // strip "card1-"
                    }))
        }
    }

    // qmllint disable unresolved-type
    CustomShortcut {
        // qmllint enable unresolved-type
        name: "brightnessUp"
        description: "Increase brightness"
        onPressed: root.increaseBrightness()
    }

    // qmllint disable unresolved-type
    CustomShortcut {
        // qmllint enable unresolved-type
        name: "brightnessDown"
        description: "Decrease brightness"
        onPressed: root.decreaseBrightness()
    }

    IpcHandler {
        function get(): real {
            return getFor("active");
        }

        // Allows searching by active/model/serial/id/name
        function getFor(query: string): real {
            return root.getMonitor(query)?.brightness ?? -1;
        }

        function set(value: string): string {
            return setFor("active", value);
        }

        // Handles brightness value like brightnessctl: 0.1, +0.1, 0.1-, 10%, +10%, 10%-
        function setFor(query: string, value: string): string {
            const monitor = root.getMonitor(query);
            if (!monitor)
                return "Invalid monitor: " + query;

            let targetBrightness;
            if (value.endsWith("%-")) {
                const percent = parseFloat(value.slice(0, -2));
                targetBrightness = monitor.brightness - (percent / 100);
            } else if (value.startsWith("+") && value.endsWith("%")) {
                const percent = parseFloat(value.slice(1, -1));
                targetBrightness = monitor.brightness + (percent / 100);
            } else if (value.endsWith("%")) {
                const percent = parseFloat(value.slice(0, -1));
                targetBrightness = percent / 100;
            } else if (value.startsWith("+")) {
                const increment = parseFloat(value.slice(1));
                targetBrightness = monitor.brightness + increment;
            } else if (value.endsWith("-")) {
                const decrement = parseFloat(value.slice(0, -1));
                targetBrightness = monitor.brightness - decrement;
            } else if (value.includes("%") || value.includes("-") || value.includes("+")) {
                return `Invalid brightness format: ${value}\nExpected: 0.1, +0.1, 0.1-, 10%, +10%, 10%-`;
            } else {
                targetBrightness = parseFloat(value);
            }

            if (isNaN(targetBrightness))
                return `Failed to parse value: ${value}\nExpected: 0.1, +0.1, 0.1-, 10%, +10%, 10%-`;

            monitor.setBrightness(targetBrightness);

            return `Set monitor ${monitor.modelData.name} brightness to ${+monitor.brightness.toFixed(2)}`;
        }

        target: "brightness"
    }

    component Monitor: QtObject {
        id: monitor

        required property ShellScreen modelData
        readonly property var ddcInfo: root.ddcMonitorMap[modelData.name] ?? null
        readonly property bool isDdc: ddcInfo !== null
        readonly property string busNum: ddcInfo?.busNum ?? ""
        readonly property bool isAppleDisplay: root.appleDisplayPresent && modelData.model.startsWith("StudioDisplay")
        readonly property bool isInternal: /^(eDP|LVDS|DSI)-/.test(modelData.name)
        property real brightness
        property real queuedBrightness: NaN

        readonly property Process initProc: Process {
            stdout: StdioCollector {
                onStreamFinished: {
                    // A startup read must not overwrite a newer key/slider target.
                    if (monitor.setProc.running || !isNaN(monitor.queuedBrightness))
                        return;
                    if (monitor.isAppleDisplay) {
                        const val = parseInt(text.trim());
                        monitor.brightness = val / 101;
                    } else {
                        const [, , , cur, max] = text.split(" ");
                        monitor.brightness = parseInt(cur) / parseInt(max);
                    }
                }
            }
        }

        // One hardware command per monitor at a time. While it runs, accumulate
        // key presses in brightness and retain only the latest absolute target.
        readonly property Process setProc: Process {
            onExited: exitCode => {
                if (exitCode !== 0) {
                    monitor.queuedBrightness = NaN;
                    console.warn("Brightness command failed for", monitor.modelData.name);
                    monitor.initBrightness();
                    return;
                }
                monitor.flushBrightness();
            }
        }

        function setBrightness(value: real): void {
            if (!isAppleDisplay && !isDdc && !isInternal) {
                console.warn("No brightness interface for", modelData.name);
                return;
            }
            value = Math.max(isInternal ? 0.01 : 0, Math.min(1, value));
            const rounded = Math.round(value * 100);
            if (Math.round(brightness * 100) === rounded)
                return;

            brightness = rounded / 100;
            queuedBrightness = brightness;
            flushBrightness();
        }

        function flushBrightness(): void {
            if (setProc.running || isNaN(queuedBrightness))
                return;

            const rounded = Math.round(queuedBrightness * 100);
            queuedBrightness = NaN;

            if (isAppleDisplay)
                setProc.command = ["asdbctl", "set", rounded];
            else if (isDdc)
                setProc.command = ["ddcutil", "-b", busNum, "setvcp", "10", rounded];
            else if (isInternal)
                setProc.command = ["sh", "-c", `${root.selectBacklight} exec /usr/bin/brightnessctl -d "$dev" s "$1"`, "sh", `${rounded}%`];
            else
                return;

            setProc.running = true;
        }

        function initBrightness(): void {
            if (isAppleDisplay)
                initProc.command = ["asdbctl", "get"];
            else if (isDdc)
                initProc.command = ["ddcutil", "-b", busNum, "getvcp", "10", "--brief"];
            else if (isInternal)
                initProc.command = ["sh", "-c", `${root.selectBacklight} echo a b c $(/usr/bin/brightnessctl -d "$dev" g) $(/usr/bin/brightnessctl -d "$dev" m)`];
            else
                return;

            initProc.running = true;
        }

        onBusNumChanged: initBrightness()
        Component.onCompleted: initBrightness()
    }
}
