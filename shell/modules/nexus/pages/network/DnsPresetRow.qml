pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Caelestia.Config
import qs.components
import qs.components.controls
import qs.services
import qs.modules.nexus.common

ColumnLayout {
    id: root

    required property string ssid
    property string helperPath: Quickshell.env("HOME") + "/.local/bin/jubal-wifi-dns"
    property bool canEdit: true
    property string profileUuid: ""
    property string provider: "custom"
    property string selectedProvider: "custom"
    property string status: ""
    property bool failed: false
    readonly property bool busy: worker.running
    property string requestedSsid: ""
    property string operation: "status"
    signal configurationSaved
    signal configurationLoaded

    spacing: Tokens.spacing.extraSmall / 2

    function refresh(): void {
        if (!ssid || busy) return;
        run("status");
    }

    function run(action: string): void {
        if (busy) return;
        if (action === "set" && (!canEdit || !profileUuid || selectedProvider === "custom")) return;
        operation = action;
        requestedSsid = ssid;
        failed = false;
        status = action === "set" ? "Applying DNS…" : "Reading DNS settings…";
        let args = [helperPath, action, "--ssid", ssid];
        if (action === "set") args = args.concat(["--uuid", profileUuid, "--provider", selectedProvider]);
        worker.command = args;
        worker.running = true;
    }

    function acceptResult(text: string, code: int): void {
        if (requestedSsid !== ssid) { refresh(); return; }
        try {
            const result = JSON.parse(text);
            failed = !result.success || code !== 0;
            if (failed) {
                status = result.message || "Could not update DNS.";
                return;
            }
            profileUuid = result.uuid;
            provider = selectedProvider = result.provider;
            providerSelect.active = provider === "cloudflare" ? cloudflareItem : provider === "google" ? googleItem : provider === "automatic" ? automaticItem : null;
            if (operation === "set") {
                status = result.message;
                configurationSaved();
            } else {
                status = "";
                configurationLoaded();
            }
        } catch (error) {
            failed = true;
            status = "Could not read DNS settings. Check that NetworkManager is running.";
        }
    }

    onSsidChanged: {
        profileUuid = "";
        provider = selectedProvider = "custom";
        Qt.callLater(refresh);
    }
    Component.onCompleted: refresh()

    Process {
        id: worker
        stdout: StdioCollector { id: output }
        stderr: StdioCollector {}
        onExited: code => Qt.callLater(() => root.acceptResult(output.text, code))
    }

    SelectRow {
        id: providerSelect
        first: true
        last: true
        label: "DNS provider"
        fallbackText: root.profileUuid ? "Custom" : "Unavailable"
        fallbackIcon: "dns"
        subtext: root.selectedProvider === "cloudflare" ? "1.1.1.1 · 1.0.0.1" : root.selectedProvider === "google" ? "8.8.8.8 · 8.8.4.4" : root.selectedProvider === "automatic" ? "Use the network’s DNS servers" : "Keep your existing DNS settings"
        enabled: root.canEdit && !root.busy && !!root.profileUuid
        onSelected: item => {
            root.selectedProvider = item === cloudflareItem ? "cloudflare" : item === googleItem ? "google" : "automatic";
            root.status = "";
        }
        menuItems: [
            MenuItem { id: automaticItem; icon: "router"; text: "Automatic" },
            MenuItem { id: cloudflareItem; icon: "cloud"; text: "Cloudflare" },
            MenuItem { id: googleItem; icon: "dns"; text: "Google" }
        ]
    }

    StyledText {
        Layout.fillWidth: true
        Layout.margins: Tokens.padding.small
        wrapMode: Text.Wrap
        font: Tokens.font.body.small
        color: root.failed ? Colours.palette.m3error : Colours.palette.m3outline
        text: !root.canEdit ? "Apply your IPv4 changes below before changing provider." : root.status || "Saved for this Wi-Fi network. Applies to IPv4 and IPv6 where enabled."
    }

    RowButton {
        first: true
        last: true
        visible: root.selectedProvider !== root.provider && root.selectedProvider !== "custom"
        icon: "check"
        text: root.busy ? "Applying DNS…" : "Apply DNS"
        disabled: root.busy || !root.canEdit || !root.profileUuid
        onClicked: root.run("set")
    }

    RowButton {
        first: true
        last: true
        visible: root.failed && !root.profileUuid
        text: "Retry"
        icon: "refresh"
        disabled: root.busy
        onClicked: root.refresh()
    }
}
