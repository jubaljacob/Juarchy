pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import Caelestia
import Caelestia.I18n
import Caelestia.Services
import qs.utils

// Omarchy themes: a palette plus its own wallpapers. The CLI does the work
// (juarchy-theme omarchy ...); this keeps the shell in step with it.
Singleton {
    id: root

    readonly property string helper: `${Paths.home}/.local/bin/juarchy-theme`
    readonly property string statePath: `${Quickshell.env("XDG_STATE_HOME") || `${Paths.home}/.local/state`}/juarchy/omarchy-theme.json`

    property var themes: []
    property bool active: false
    property string theme: ""
    property string background: ""
    property bool loaded: false
    readonly property bool busy: worker.running
    readonly property var currentTheme: themes.find(t => t.id === theme) ?? null

    property var queued: null

    function refresh(): void {
        if (!lister.running)
            lister.exec(["python3", helper, "omarchy", "list", "--json"]);
    }

    function apply(id: string): void {
        run(["set", id]);
    }

    function setBackground(name: string): void {
        run(["background", "set", name]);
    }

    function nextBackground(): void {
        run(["background", "next"]);
    }

    function nextTheme(): void {
        run(["next"]);
    }

    function run(args: var): void {
        // A click while a change is still applying replaces any waiting one,
        // so quick presses end on the last choice instead of piling up.
        if (worker.running) {
            queued = args;
            return;
        }
        worker.exec(["python3", helper, "omarchy", ...args]);
    }

    Component.onCompleted: refresh()

    Process {
        id: worker

        stderr: StdioCollector {
            id: workerError
        }
        onExited: (exitCode, exitStatus) => {
            if (exitCode !== 0) {
                const message = workerError.text.trim() || Tr.tr("Could not change the theme.");
                Toaster.toast(Tr.tr("Theme not changed"), message, "palette", Toast.Error);
            }
            root.refresh();
            if (root.queued) {
                const next = root.queued;
                root.queued = null;
                root.run(next);
            }
        }
    }

    Process {
        id: lister

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const data = JSON.parse(text);
                    root.themes = data.themes;
                    root.active = data.active;
                    root.theme = data.theme;
                    root.background = data.background;
                    root.loaded = true;
                } catch (error) {
                    console.warn("Could not read Omarchy themes:", error);
                }
            }
        }
    }

    // Changes made from a terminal or a key binding show up here too.
    FileView {
        path: root.statePath
        watchChanges: true
        printErrors: false
        onFileChanged: root.refresh()
    }

    Connections {
        function onFlavourChanged(): void {
            root.refresh();
        }

        target: Colours
    }
}
