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
    property string helperPath: Quickshell.env("HOME") + "/.local/bin/jubal-weather-map"
    property real latitude: 0
    property real longitude: 0
    property int zoom: 6
    property bool hasLocation: false
    property bool browsing: false
    property bool radar: true
    property string placeName: ""
    property string imageSource: ""
    property var conditions: null
    property double radarTime: 0
    property string status: "Search for a city to load its weather map."
    property bool failed: false
    property var results: []
    readonly property bool busy: mapWorker.running || searchWorker.running
    property string requestedView: ""
    readonly property string viewKey: latitude + "," + longitude + "," + zoom + "," + radar
    spacing: Tokens.spacing.extraSmall / 2

    function followLocation(): void {
        if (browsing) return;
        const configured = GlobalConfig.services.weatherLocation;
        const coords = (configured && /^-?\d+(\.\d+)?,\s*-?\d+(\.\d+)?$/.test(configured) ? configured : Weather.loc || "").split(",").map(Number);
        if (coords.length !== 2 || !Number.isFinite(coords[0]) || !Number.isFinite(coords[1])) return;
        if (latitude !== coords[0] || longitude !== coords[1]) {
            imageSource = "";
            conditions = null;
            radarTime = 0;
        }
        latitude = Math.max(-85.0511, Math.min(85.0511, coords[0]));
        longitude = coords[1];
        hasLocation = true;
        placeName = Weather.city || "Weather location";
        refresh();
    }
    function refresh(): void {
        if (!hasLocation || busy) return;
        requestedView = viewKey;
        failed = false;
        status = "Loading map and weather…";
        let args = [helperPath, "view", "--latitude", String(latitude), "--longitude", String(longitude), "--zoom", String(zoom)];
        if (!radar) args.push("--no-radar");
        mapWorker.command = args;
        mapWorker.running = true;
    }
    function acceptMap(text: string, code: int): void {
        if (requestedView !== viewKey) { refresh(); return; }
        try {
            const data = JSON.parse(text);
            if (code !== 0 || !data.success) throw new Error(data.message || "Could not load weather.");
            imageSource = data.image;
            conditions = data.weather;
            radarTime = data.radarTime;
            status = data.warnings.join(" ");
            failed = data.warnings.length > 0;
        } catch (error) {
            failed = true;
            status = error.message || "Could not load weather. Check your connection and retry.";
        }
    }
    function search(): void {
        const query = searchField.field.text.trim();
        if (busy || query.length < 2) return;
        failed = false;
        status = "Searching for places…";
        results = [];
        searchWorker.command = [helperPath, "search", query];
        searchWorker.running = true;
    }
    function acceptSearch(text: string, code: int): void {
        try {
            const data = JSON.parse(text);
            if (code !== 0 || !data.success) throw new Error(data.message || "Location search failed.");
            results = data.results;
            status = results.length ? "Select a place below." : "No matching places. Try a nearby city.";
        } catch (error) {
            failed = true;
            status = error.message;
        }
    }
    function choose(lat: real, lon: real, name: string): void {
        if (busy) return;
        browsing = true;
        latitude = Math.max(-85.0511, Math.min(85.0511, lat));
        longitude = ((lon + 180) % 360 + 360) % 360 - 180;
        placeName = name;
        hasLocation = true;
        results = [];
        imageSource = "";
        conditions = null;
        radarTime = 0;
        refresh();
    }
    function moveBy(dx: real, dy: real): void {
        const size = 256 * Math.pow(2, zoom);
        const x = (longitude + 180) / 360 * size + dx;
        const r = latitude * Math.PI / 180;
        const y = Math.max(0, Math.min(size, (1 - Math.log(Math.tan(Math.PI / 4 + r / 2)) / Math.PI) / 2 * size + dy));
        const lat = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / size))) * 180 / Math.PI;
        const lon = x / size * 360 - 180;
        choose(lat, lon, "Selected map location");
    }
    function changeZoom(amount: int): void {
        if (busy) return;
        zoom = Math.max(3, Math.min(7, zoom + amount));
        imageSource = "";
        refresh();
    }
    function saveLocation(): void {
        GlobalConfig.services.weatherLocation = latitude.toFixed(5) + "," + longitude.toFixed(5);
        browsing = false;
        status = "Weather location saved.";
        failed = false;
    }
    function timeLabel(seconds: real): string {
        return new Date(seconds * 1000).toLocaleString(Qt.locale(), Locale.ShortFormat);
    }
    Component.onCompleted: followLocation()

    Connections {
        target: Weather
        function onLocChanged(): void { root.followLocation(); }
        function onCityChanged(): void { if (!root.browsing) root.placeName = Weather.city; }
    }
    Process {
        id: mapWorker
        stdout: StdioCollector { id: mapOutput }
        onExited: code => Qt.callLater(() => root.acceptMap(mapOutput.text, code))
    }
    Process {
        id: searchWorker
        stdout: StdioCollector { id: searchOutput }
        onExited: code => Qt.callLater(() => root.acceptSearch(searchOutput.text, code))
    }
    Timer {
        interval: 600000
        repeat: true
        running: root.visible && root.hasLocation
        onTriggered: root.refresh()
    }
    TextFieldRow {
        id: searchField
        first: true
        last: true
        label: "Weather location"
        subtext: "Search for a city or town"
        placeholderText: "City name"
        enabled: !root.busy
    }
    Connections {
        target: searchField.field
        function onAccepted(): void { root.search(); }
    }
    RowButton {
        first: true
        last: true
        text: searchWorker.running ? "Searching…" : "Search places"
        icon: "search"
        disabled: root.busy || searchField.field.text.trim().length < 2
        onClicked: root.search()
    }
    Repeater {
        model: root.results
        delegate: RowButton {
            required property var modelData
            required property int index
            first: index === 0
            last: index === root.results.length - 1
            text: modelData.name
            icon: "location_on"
            disabled: root.busy
            onClicked: root.choose(modelData.latitude, modelData.longitude, modelData.name)
        }
    }
    InfoRow {
        visible: root.hasLocation
        first: true
        last: true
        icon: root.conditions ? Weather.getWeatherCondition(String(root.conditions.weather_code)).toLowerCase().includes("rain") ? "rainy" : "partly_cloudy_day" : "location_on"
        label: root.placeName || "Selected location"
        subtext: root.conditions ? Weather.getWeatherCondition(String(root.conditions.weather_code)) + " · Wind " + root.conditions.wind_speed_10m + " km/h · Humidity " + root.conditions.relative_humidity_2m + "%" : root.latitude.toFixed(3) + ", " + root.longitude.toFixed(3)
        value: root.conditions ? Weather.formatTemp(root.conditions.temperature_2m) : ""
    }
    Rectangle {
        id: map
        visible: root.hasLocation
        Layout.fillWidth: true
        implicitHeight: width / 2
        color: Colours.palette.m3surfaceContainerHigh
        clip: true
        Image {
            anchors.fill: parent
            source: root.imageSource
            asynchronous: true
            cache: false
        }
        MouseArea {
            anchors.fill: parent
            enabled: !root.busy && !!root.imageSource
            preventStealing: true
            cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
            property real startX
            property real startY
            onPressed: event => { startX = event.x; startY = event.y; }
            onReleased: event => {
                const dx = event.x - startX, dy = event.y - startY;
                const dragged = Math.abs(dx) + Math.abs(dy) > 8;
                root.moveBy((dragged ? -dx : event.x - width / 2) * 768 / width, (dragged ? -dy : event.y - height / 2) * 384 / height);
            }
        }
        Rectangle {
            anchors.centerIn: parent
            width: 18
            height: 18
            radius: 9
            color: "#c62828"
            border.width: 3
            border.color: "white"
            visible: !!root.imageSource
        }
        Rectangle {
            visible: root.busy || !root.imageSource
            anchors.fill: parent
            color: Colours.palette.m3surfaceContainerHigh
            opacity: 0.85
            StyledText {
                anchors.centerIn: parent
                text: root.busy ? "Loading weather map…" : "Map unavailable · refresh to retry"
                font: Tokens.font.body.small
            }
        }
        Rectangle {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            width: attribution.implicitWidth + 12
            height: attribution.implicitHeight + 8
            color: "#eefafafa"
            Text {
                id: attribution
                anchors.centerIn: parent
                text: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                color: "#182027"
                linkColor: "#174c73"
                font.pixelSize: 12
                onLinkActivated: link => Qt.openUrlExternally(link)
            }
        }
    }
    RowLayout {
        visible: root.hasLocation
        Layout.fillWidth: true
        RowButton { text: "Zoom out"; icon: "remove"; first: true; last: true; disabled: root.busy || root.zoom <= 3; onClicked: root.changeZoom(-1) }
        RowButton { text: "Zoom in"; icon: "add"; first: true; last: true; disabled: root.busy || root.zoom >= 7; onClicked: root.changeZoom(1) }
        RowButton { text: "Refresh"; icon: "refresh"; first: true; last: true; disabled: root.busy; onClicked: root.refresh() }
    }
    ToggleRow {
        visible: root.hasLocation
        first: true
        last: true
        text: "Rain radar"
        subtext: "Latest available radar · coverage varies by region"
        checked: root.radar
        disabled: root.busy
        onToggled: {
            root.radar = checked;
            root.imageSource = "";
            root.radarTime = 0;
            root.refresh();
        }
    }
    StyledText {
        visible: root.hasLocation
        Layout.fillWidth: true
        Layout.margins: Tokens.padding.small
        wrapMode: Text.Wrap
        font: Tokens.font.body.small
        color: Colours.palette.m3outline
        text: "Drag to move · click to select a location.\n" + (root.conditions ? "Conditions: " + root.timeLabel(root.conditions.time) + ". " : "") + (root.radarTime && root.radar ? "Radar frame: " + root.timeLabel(root.radarTime) + ". " : "") + "Refreshes every 10 minutes while visible." + (root.radar ? "\nColoured areas indicate precipitation. Uncoloured areas may also lack radar coverage." : "")
    }
    RowButton {
        visible: root.hasLocation && root.browsing
        first: true
        last: true
        text: "Use this weather location"
        subtext: "Also updates the weather shown throughout the desktop"
        icon: "check"
        disabled: root.busy
        onClicked: root.saveLocation()
    }
    StyledText {
        visible: !!root.status
        Layout.fillWidth: true
        Layout.margins: Tokens.padding.small
        text: root.status
        wrapMode: Text.Wrap
        font: Tokens.font.body.small
        color: root.failed ? Colours.palette.m3error : Colours.palette.m3outline
    }
    StyledText {
        Layout.fillWidth: true
        Layout.margins: Tokens.padding.small
        text: 'Weather: <a style="color:' + Colours.palette.m3primary + '" href="https://open-meteo.com/">Open-Meteo</a> · Radar: <a style="color:' + Colours.palette.m3primary + '" href="https://www.rainviewer.com/">RainViewer</a>'
        textFormat: Text.RichText
        font: Tokens.font.body.small
        linkColor: Colours.palette.m3primary
        wrapMode: Text.Wrap
        onLinkActivated: link => Qt.openUrlExternally(link)
    }
}
