pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import Caelestia
import Caelestia.Config
import Caelestia.I18n
import qs.utils

Singleton {
    id: root

    property string city
    property string loc
    property var cc
    property list<var> forecast
    property list<var> hourlyForecast

    property int locationGeneration: 0
    property bool citiesLoaded: false
    property string pendingCoords

    readonly property string icon: cc ? Icons.getWeatherIcon(cc.weatherCode) : "cloud_alert"
    readonly property string description: cc ? getWeatherCondition(cc.weatherCode) : Tr.tr("No weather")
    readonly property string temp: formatTemp(cc?.tempC)
    readonly property string feelsLike: formatTemp(cc?.feelsLikeC)
    readonly property int humidity: cc?.humidity ?? 0
    readonly property real windSpeed: cc?.windSpeed ?? 0
    readonly property string sunrise: cc ? Qt.formatDateTime(new Date(cc.sunrise), Units.twelveHourClock ? "h:mm A" : "h:mm") : "--:--"
    readonly property string sunset: cc ? Qt.formatDateTime(new Date(cc.sunset), Units.twelveHourClock ? "h:mm A" : "h:mm") : "--:--"

    readonly property var cachedCities: new Map()

    function formatTemp(temp: var, compact = false): string {
        const unit = GlobalConfig.services.weatherUnits;
        const value = temp !== undefined ? Math.round(Units.toTemperature(temp, unit)) : "--";
        return Units.formatTemp(value, unit, compact);
    }

    function reload(): void {
        locationGeneration++;
        loc = "";
        city = "";
        cc = null;
        forecast = [];
        hourlyForecast = [];
        pendingCoords = "";
        const configLocation = GlobalConfig.services.weatherLocation.trim();
        if (!configLocation) return;

        if (configLocation.indexOf(",") !== -1 && !isNaN(parseFloat(configLocation.split(",")[0]))) {
            const coords = configLocation.split(",").map(Number);
            if (coords.length !== 2 || !Number.isFinite(coords[0]) || !Number.isFinite(coords[1]) || Math.abs(coords[0]) > 90 || Math.abs(coords[1]) > 180)
                return;
            // Coordinates are already chosen: avoid a separate reverse-geocoding request.
            city = cachedCities.get(configLocation) || configLocation;
            loc = configLocation;
        } else {
            fetchCoordsFromCity(configLocation);
        }
    }

    function fixCityName(cityName: string): string {
        if (!cityName)
            return "";
        const mapping = {
            // Polish
            "Poznan": "Poznań",
            "Wroclaw": "Wrocław",
            "Krakow": "Kraków",
            "Gdansk": "Gdańsk",
            "Lodz": "Łódź",
            "Rzeszow": "Rzeszów",
            "Torun": "Toruń",
            "Bialystok": "Białystok",
            "Czestochowa": "Częstochowa",
            "Plock": "Płock",
            "Ruda Slaska": "Ruda Śląska",
            "Dabrowa Gornicza": "Dąbrowa Górnicza",
            "Elblag": "Elbląg",
            "Gorzow Wielkopolski": "Gorzów Wielkopolski",
            "Zielona Gora": "Zielona Góra",
            "Slupsk": "Słupsk",

            // German
            "Munchen": "München",
            "Koln": "Köln",
            "Dusseldorf": "Düsseldorf",
            "Nurnberg": "Nürnberg",

            // French & Spanish & Portuguese
            "Sao Paulo": "São Paulo",
            "Montreal": "Montréal",
            "Quebec": "Québec",
            "Bogota": "Bogotá",
            "Medellin": "Medellín",
            "Cordoba": "Córdoba",

            // Turkish
            "Istanbul": "İstanbul",
            "Izmir": "İzmir",

            // Scandinavian & others
            "Malmo": "Malmö",
            "Goteborg": "Göteborg",
            "Zurich": "Zürich",
            "Geneve": "Genève"
        };
        return mapping[cityName] || cityName;
    }

    function cacheCity(coords: string, cityName: string): void {
        cachedCities.set(coords, cityName);
        citiesSaveTimer.restart();
    }

    function fetchCoordsFromCity(cityName: string): void {
        const lang = Qt.locale().name.split("_")[0] || "en";
        const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(cityName)}&count=1&language=${lang}&format=json`;

        const generation = locationGeneration;
        Requests.get(url, text => {
            if (generation !== root.locationGeneration) return;
            const json = JSON.parse(text);
            if (json.results && json.results.length > 0) {
                const result = json.results[0];
                loc = result.latitude + "," + result.longitude;
                city = fixCityName(result.name);
            } else {
                loc = "";
                city = Tr.tr("Location not found");
            }
        });
    }

    function fetchWeatherData(): void {
        const url = getWeatherUrl();
        if (url === "")
            return;

        const generation = locationGeneration;
        Requests.get(url, text => {
            if (generation !== root.locationGeneration) return;
            const json = JSON.parse(text);
            if (!json.current || !json.daily)
                return;

            cc = {
                weatherCode: json.current.weather_code,
                tempC: json.current.temperature_2m,
                feelsLikeC: json.current.apparent_temperature,
                humidity: json.current.relative_humidity_2m,
                windSpeed: json.current.wind_speed_10m,
                isDay: json.current.is_day,
                sunrise: json.daily.sunrise[0].replace("T", " "),
                sunset: json.daily.sunset[0].replace("T", " ")
            };

            const forecastList = [];
            for (let i = 0; i < json.daily.time.length; i++)
                forecastList.push({
                    date: json.daily.time[i].replace(/-/g, "/"),
                    maxTempC: json.daily.temperature_2m_max[i],
                    minTempC: json.daily.temperature_2m_min[i],
                    weatherCode: json.daily.weather_code[i],
                    icon: Icons.getWeatherIcon(json.daily.weather_code[i])
                });
            forecast = forecastList;

            const hourlyList = [];
            const now = new Date();
            for (let i = 0; i < json.hourly.time.length; i++) {
                const time = new Date(json.hourly.time[i].replace("T", " "));

                if (time < now)
                    continue;

                hourlyList.push({
                    timestamp: json.hourly.time[i],
                    hour: time.getHours(),
                    tempC: Math.round(json.hourly.temperature_2m[i]),
                    precipChance: json.hourly.precipitation_probability[i],
                    weatherCode: json.hourly.weather_code[i],
                    icon: Icons.getWeatherIcon(json.hourly.weather_code[i])
                });
            }
            hourlyForecast = hourlyList;
        });
    }

    function getWeatherUrl(): string {
        if (!GlobalConfig.services.weatherLocation.trim() || !loc || loc.indexOf(",") === -1)
            return "";

        const [lat, lon] = loc.split(",").map(s => s.trim());
        const baseUrl = "https://api.open-meteo.com/v1/forecast";
        const params = ["latitude=" + lat, "longitude=" + lon, "hourly=weather_code,temperature_2m,precipitation_probability", "daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset", "current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,weather_code,wind_speed_10m", "timezone=auto", "forecast_days=7"];

        return baseUrl + "?" + params.join("&");
    }

    function getWeatherCondition(code: string): string {
        const conditions = {
            "0": Tr.tr("Clear"),
            "1": Tr.tr("Clear"),
            "2": Tr.tr("Partly cloudy"),
            "3": Tr.tr("Overcast"),
            "45": Tr.tr("Fog"),
            "48": Tr.tr("Fog"),
            "51": Tr.tr("Drizzle"),
            "53": Tr.tr("Drizzle"),
            "55": Tr.tr("Drizzle"),
            "56": Tr.tr("Freezing drizzle"),
            "57": Tr.tr("Freezing drizzle"),
            "61": Tr.tr("Light rain"),
            "63": Tr.tr("Rain"),
            "65": Tr.tr("Heavy rain"),
            "66": Tr.tr("Light rain"),
            "67": Tr.tr("Heavy rain"),
            "71": Tr.tr("Light snow"),
            "73": Tr.tr("Snow"),
            "75": Tr.tr("Heavy snow"),
            "77": Tr.tr("Snow"),
            "80": Tr.tr("Light rain"),
            "81": Tr.tr("Rain"),
            "82": Tr.tr("Heavy rain"),
            "85": Tr.tr("Light snow showers"),
            "86": Tr.tr("Heavy snow showers"),
            "95": Tr.tr("Thunderstorm"),
            "96": Tr.tr("Thunderstorm with hail"),
            "99": Tr.tr("Thunderstorm with hail")
        };
        return conditions[code] || Tr.trCtx("Unknown", "weather condition");
    }

    onLocChanged: fetchWeatherData()
    Connections {
        function onWeatherLocationChanged(): void {
            root.reload();
        }

        target: GlobalConfig.services
    }

    Timer {
        interval: 3600000 // 1 hour
        running: !!GlobalConfig.services.weatherLocation.trim() && !!root.loc
        repeat: true
        onTriggered: fetchWeatherData()
    }

    Timer {
        id: citiesSaveTimer

        interval: 1000
        onTriggered: {
            if (!root.citiesLoaded)
                return;

            const data = {};
            root.cachedCities.forEach((cityName, coords) => data[coords] = cityName);
            citiesStorage.setText(JSON.stringify(data));
        }
    }

    FileView {
        id: citiesStorage

        printErrors: false
        path: `${Paths.cache}/cities.json`
        onLoaded: {
            try {
                const data = JSON.parse(text());
                for (const [coords, cityName] of Object.entries(data))
                    if (!root.cachedCities.has(coords))
                        root.cachedCities.set(coords, cityName);
            } catch (error) {
                console.warn(lc, `Unable to parse cached cities: ${error}`);
            }

            root.citiesLoaded = true;
        }
        onLoadFailed: err => {
            root.citiesLoaded = true;
            if (err === FileViewError.FileNotFound)
                Qt.callLater(() => setText("{}"));
            else
                console.warn(lc, `Unable to load cached cities: ${err}`);
        }
    }

    LoggingCategory {
        id: lc

        name: "caelestia.qml.services.weather"
        defaultLogLevel: LoggingCategory.Info
    }
}
