pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Notifications
import Caelestia
import Caelestia.Config
import Caelestia.I18n
import qs.components.misc
import qs.services
import qs.utils

Singleton {
    id: root

    property list<NotifData> list: []
    readonly property list<NotifData> notClosed: list.filter(n => !n.closed)
    readonly property list<NotifData> popups: list.filter(n => n.popup)
    property alias dnd: props.dnd

    property bool loaded

    function hasFullscreen(): bool {
        for (const monitor of Hypr.monitors.values) {
            if (monitor?.activeWorkspace?.toplevels.values.some(t => t.lastIpcObject.fullscreen > 1))
                return true;
        }
        return false;
    }

    function shouldShowPopup(): bool {
        if (props.dnd || ShellState.anySidebarOpen())
            return false;
        if (GlobalConfig.notifs.fullscreen === NotifsFullscreen.Off && hasFullscreen())
            return false;
        return true;
    }

    onDndChanged: {
        if (!GlobalConfig.utilities.toasts.dndChanged)
            return;

        if (dnd)
            Toaster.toast(Tr.tr("Do not disturb enabled"), Tr.tr("Popup notifications are now disabled"), "do_not_disturb_on");
        else
            Toaster.toast(Tr.tr("Do not disturb disabled"), Tr.tr("Popup notifications are now enabled"), "do_not_disturb_off");
    }

    function historyEntries(): list<var> {
        const cutoff = Date.now() - Privacy.notificationRetentionDays * 86400000;
        return notClosed.filter(n => n.time.getTime() >= cutoff).map(n => ({
            time: n.time, notificationId: n.notificationId,
            summary: n.summary, body: n.body, appIcon: n.appIcon,
            appName: n.appName, image: n.image, expireTimeout: n.expireTimeout,
            urgency: n.urgency, resident: n.resident, hasActionIcons: false, actions: []
        }));
    }

    function saveHistory(): void {
        if (loaded && Privacy.notificationRetentionDays > 0)
            storage.setText(JSON.stringify(historyEntries()));
    }

    function pruneHistory(): void {
        if (Privacy.notificationRetentionDays === 0) return;
        const cutoff = Date.now() - Privacy.notificationRetentionDays * 86400000;
        for (const notif of list.slice())
            if (notif.time.getTime() < cutoff) notif.close();
        saveHistory();
    }

    function clearHistory(): void {
        for (const notif of list.slice()) notif.close();
        saveTimer.stop();
        // Locks can delay destruction during animations. Erase saved content immediately.
        if (Privacy.notificationRetentionDays > 0) storage.setText("[]");
        eraseHistory.running = true;
    }

    function applyRetention(): void {
        if (!Privacy.loaded) return;
        if (Privacy.notificationRetentionDays === 0) {
            saveTimer.stop();
            loaded = true;
            eraseHistory.running = true;
            for (const notif of list) notif.dummyImageLoader.active = false;
        } else if (loaded) {
            pruneHistory();
        }
    }

    onListChanged: {
        if (loaded && Privacy.notificationRetentionDays > 0) saveTimer.restart();
    }

    Component.onCompleted: applyRetention()

    Connections {
        target: Privacy
        function onLoadedChanged(): void { root.applyRetention(); }
        function onNotificationRetentionDaysChanged(): void { root.applyRetention(); }
    }

    Process {
        id: eraseHistory
        command: [Quickshell.env("HOME") + "/.local/bin/juarchy-notification-history"]
        onExited: code => {
            if (code !== 0) console.warn("Could not erase saved notification history");
            else if (Privacy.notificationRetentionDays > 0) root.saveHistory();
        }
    }

    Process {
        id: pruneImages
        command: [Quickshell.env("HOME") + "/.local/bin/juarchy-notification-history", "--prune-images"]
    }

    Timer {
        id: saveTimer
        interval: 1000
        onTriggered: root.saveHistory()
    }

    Timer {
        interval: 60000
        repeat: true
        running: root.loaded && Privacy.notificationRetentionDays > 0
        onTriggered: root.pruneHistory()
    }

    PersistentProperties {
        id: props

        property bool dnd

        reloadableId: "notifs"
    }

    NotificationServer {
        id: server

        keepOnReload: false
        actionsSupported: true
        bodyHyperlinksSupported: true
        bodyImagesSupported: true
        bodyMarkupSupported: true
        imageSupported: true
        persistenceSupported: true

        onNotification: notif => {
            notif.tracked = true;

            const comp = notifComp.createObject(root, {
                popup: root.shouldShowPopup(),
                notification: notif
            });
            root.list = [comp, ...root.list];
        }
    }

    FileView {
        id: storage

        printErrors: false
        path: Privacy.loaded && Privacy.notificationRetentionDays > 0 ? `${Paths.state}/notifs.json` : ""
        onSaved: { pruneImages.running = true; }
        onLoaded: {
            if (root.loaded) return;
            try {
                const data = JSON.parse(text());
                const cutoff = Date.now() - Privacy.notificationRetentionDays * 86400000;
                if (!Array.isArray(data)) throw new Error("Invalid history");
                for (const notif of data) {
                    if (!notif || !Number.isFinite(new Date(notif.time).getTime()) || new Date(notif.time).getTime() < cutoff) continue;
                    const properties = Object.assign({}, notif);
                    if (properties.notificationId === undefined && properties.id !== undefined)
                        properties.notificationId = String(properties.id);
                    delete properties.id;
                    properties.popup = false;
                    properties.actions = [];
                    root.list.push(notifComp.createObject(root, properties));
                }
                root.list.sort((a, b) => b.time - a.time);
            } catch (error) {
                console.warn("Saved notification history could not be read");
            }
            root.loaded = true;
            root.saveHistory();
        }
        onLoadFailed: {
            root.loaded = true;
            root.saveHistory();
        }
    }

    // qmllint disable unresolved-type
    CustomShortcut {
        // qmllint enable unresolved-type
        name: "clearNotifs"
        description: "Clear all notifications"
        onPressed: root.clearHistory()
    }

    IpcHandler {
        function clear(): void { root.clearHistory(); }

        function isDndEnabled(): bool {
            return props.dnd;
        }

        function toggleDnd(): void {
            props.dnd = !props.dnd;
        }

        function enableDnd(): void {
            props.dnd = true;
        }

        function disableDnd(): void {
            props.dnd = false;
        }

        target: "notifs"
    }

    Component {
        id: notifComp

        NotifData {}
    }
}
