pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import Caelestia.I18n
import qs.utils

// Claude Code and Codex usage. The collector (juarchy-agent-usage) reads each
// agent's own sign-in and session files and decides how often a limit is
// really asked for, so refreshing here is cheap.
Singleton {
    id: root

    readonly property string helper: `${Paths.home}/.local/bin/juarchy-agent-usage`

    property var agents: []
    property bool loaded: false
    property bool failed: false
    property double updatedAt: 0
    property bool forceNext: false

    readonly property bool busy: collector.running
    readonly property var ready: agents.filter(agent => agent.ready)
    // The most-spent window of any agent, so the bar can warn about the worst one.
    readonly property real worst: ready.reduce((top, agent) => Math.max(top, primaryPercent(agent)), 0)

    function find(id: string): var {
        return agents.find(agent => agent.id === id) ?? null;
    }

    // Windows that belong to the account, not to one model.
    function generalLimits(agent: var): var {
        return (agent?.limits ?? []).filter(window => !window.scoped);
    }

    // How spent the agent is: its most-used general window, or -1 with none.
    function primaryPercent(agent: var): real {
        const windows = generalLimits(agent);
        return windows.length === 0 ? -1 : windows.reduce((top, window) => Math.max(top, window.percent), 0);
    }

    // Quiet while there is room, warm near the limit, urgent at it.
    function tone(percent: real): color {
        if (percent >= 0.9)
            return Colours.palette.m3error;
        if (percent >= 0.75)
            return Colours.palette.m3tertiary;
        return Colours.palette.m3primary;
    }

    function refresh(force: bool): void {
        if (collector.running) {
            forceNext = forceNext || force;
            return;
        }
        collector.exec(force ? ["python3", helper, "--force"] : ["python3", helper]);
    }

    function formatTokens(count: real): string {
        if (count >= 1e9)
            return `${(count / 1e9).toFixed(1)}B`;
        if (count >= 1e6)
            return `${(count / 1e6).toFixed(1)}M`;
        if (count >= 1e4)
            return `${Math.round(count / 1e3)}k`;
        if (count >= 1e3)
            return `${(count / 1e3).toFixed(1)}k`;
        return `${Math.round(count)}`;
    }

    // "2h 14m", "3d 4h", "12m": what is left until a window resets.
    function formatReset(iso: string, now: date): string {
        const target = Date.parse(iso);
        if (!iso || isNaN(target))
            return "";
        const minutes = Math.round((target - now.getTime()) / 60000);
        if (minutes <= 0)
            return Tr.tr("now");
        const days = Math.floor(minutes / 1440);
        const hours = Math.floor((minutes % 1440) / 60);
        if (days > 0)
            return `${days}d ${hours}h`;
        if (hours > 0)
            return `${hours}h ${minutes % 60}m`;
        return `${minutes}m`;
    }

    function formatAge(stamp: real, now: date): string {
        const minutes = Math.round((now.getTime() - stamp) / 60000);
        if (stamp <= 0)
            return "";
        if (minutes < 1)
            return Tr.tr("just now");
        if (minutes < 60)
            return Tr.tr("%1 min ago").arg(minutes);
        return Tr.tr("%1 h ago").arg(Math.round(minutes / 60));
    }

    Component.onCompleted: refresh(false)

    Process {
        id: collector

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const data = JSON.parse(text);
                    root.agents = data.agents;
                    root.updatedAt = Date.now();
                    root.failed = false;
                    root.loaded = true;
                } catch (error) {
                    console.warn("Could not read agent usage:", error);
                    root.failed = true;
                }
            }
        }
        onExited: (exitCode, exitStatus) => {
            if (exitCode !== 0)
                root.failed = true;
            if (root.forceNext) {
                root.forceNext = false;
                root.refresh(true);
            }
        }
    }

    // Turning limit checks on or off in Settings takes effect straight away. The
    // short wait lets the privacy file finish saving before the collector reads it.
    Connections {
        function onAgentUsageLimitsChanged(): void {
            privacyChanged.restart();
        }

        target: Privacy
    }

    Timer {
        id: privacyChanged

        interval: 500
        onTriggered: root.refresh(true)
    }

    // Local counts follow the agents as they work; limits are asked for far less often.
    Timer {
        interval: 60000
        running: true
        repeat: true
        onTriggered: root.refresh(false)
    }
}
