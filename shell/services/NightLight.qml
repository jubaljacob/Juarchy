pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import Caelestia

Singleton {
    id: root

    property bool enabled: false
    property bool available: true
    property int temperature: 4500
    property int refCount: 0
    readonly property bool busy: command?.running ?? false
    property string action: "status"

    function refresh(): void {
        run("status");
    }

    function toggle(): void {
        run("toggle");
    }

    function run(request: string): void {
        if (busy) return;
        action = request;
        command.exec([`${Quickshell.env("HOME")}/.local/bin/juarchy-night-light`, request]);
    }

    Component.onCompleted: refresh()

    Process {
        id: command
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    if (typeof result.enabled === "boolean") root.enabled = result.enabled;
                    if (typeof result.available === "boolean") root.available = result.available;
                    if (typeof result.temperature === "number") root.temperature = result.temperature;
                    if (result.error && root.action !== "status")
                        Toaster.toast("Night light could not change", result.error, "nightlight");
                } catch (error) {
                    console.warn("Could not read night-light state:", error);
                }
            }
        }
    }

    Timer {
        interval: 3000
        running: root.refCount > 0
        repeat: true
        triggeredOnStart: true
        onTriggered: root.refresh()
    }
}
