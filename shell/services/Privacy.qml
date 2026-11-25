pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root

    property bool remoteMediaArtwork: false
    property bool musicVisualisers: false
    property int notificationRetentionDays: 0
    property bool agentUsageLimits: false
    property bool loaded: false
    property bool applying: false

    function loadSettings(): void {
        applying = true;
        try {
            const data = JSON.parse(settings.text() || "{}");
            remoteMediaArtwork = data.remoteMediaArtwork === true;
            musicVisualisers = data.musicVisualisers === true;
            agentUsageLimits = data.agentUsageLimits === true;
            notificationRetentionDays = [0, 1, 7, 30].includes(data.notificationRetentionDays) ? data.notificationRetentionDays : 0;
        } catch (error) {
            remoteMediaArtwork = false;
            musicVisualisers = false;
            agentUsageLimits = false;
            notificationRetentionDays = 0;
            console.warn("Privacy settings could not be read; using private defaults");
        }
        applying = false;
        loaded = true;
    }

    function save(): void {
        if (!loaded || applying) return;
        settings.setText(JSON.stringify({remoteMediaArtwork, musicVisualisers, notificationRetentionDays, agentUsageLimits}, null, 2));
    }

    onRemoteMediaArtworkChanged: save()
    onMusicVisualisersChanged: save()
    onNotificationRetentionDaysChanged: save()
    onAgentUsageLimitsChanged: save()
    Component.onCompleted: loadSettings()

    FileView {
        id: settings
        path: `${Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config"}/juarchy/privacy.json`
        blockLoading: true
        printErrors: false
        watchChanges: true
        onFileChanged: { reload(); }
        onLoaded: { if (!root.applying) root.loadSettings(); }
        onLoadFailed: { root.loaded = true; }
        onSaveFailed: console.warn("Could not save Juarchy privacy preferences")
    }
}
