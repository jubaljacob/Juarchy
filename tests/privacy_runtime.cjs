const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

// Exercise the functions used by the shell with mocked services and network IO.
function functions(path, names) {
    const source = fs.readFileSync(path, 'utf8');
    return names.map(name => {
        const match = source.match(new RegExp('    function ' + name + '\\(([^)]*)\\)(?::[^\\{]+)? \\{([\\s\\S]*?)\\n    \\}'));
        assert(match, `Missing ${name} in ${path}`);
        return `function ${name}(${match[1].replace(/:\s*\w+/g, '')}) {${match[2]}\n}`;
    }).join('\n');
}
const privacy = {loaded: true, remoteMediaArtwork: false, notificationRetentionDays: 0};
const ctx = vm.createContext({Privacy: privacy});
vm.runInContext(functions('shell/services/Players.qml', ['getArtUrl']), ctx);
assert.equal(ctx.getArtUrl({trackArtUrl: 'https://example.com/music.jpg'}), '');
assert.equal(ctx.getArtUrl({trackArtUrl: 'file:///tmp/music.jpg'}), 'file:///tmp/music.jpg');
assert.equal(ctx.getArtUrl({trackArtUrl: 'file://remote/music.jpg'}), '');
assert.equal(ctx.getArtUrl({metadata: {'xesam:url': 'https://www.youtube.com/watch?v=abcdefghijk'}}), '');
privacy.remoteMediaArtwork = true;
assert.equal(ctx.getArtUrl({trackArtUrl: 'https://example.com/music.jpg'}), 'https://example.com/music.jpg');
assert.equal(ctx.getArtUrl({trackArtUrl: 'ftp://example.com/music.jpg'}), '');
privacy.loaded = false;
assert.equal(ctx.getArtUrl({trackArtUrl: 'https://example.com/music.jpg'}), '');

const requests = [];
const config = {services: {weatherLocation: ''}};
const weather = vm.createContext({GlobalConfig: config, cachedCities: new Map(),
    Requests: {get: (url, callback) => requests.push({url, callback})},
    locationGeneration: 0, loc: 'old location', city: 'old city', cc: {},
    forecast: [], hourlyForecast: [], pendingCoords: '', Qt: {locale: () => ({name: 'en_GB'})},
    Tr: {tr: x => x}, fixCityName: x => x});
weather.root = weather;
vm.runInContext(functions('shell/services/Weather.qml', ['reload', 'getWeatherUrl', 'fetchCoordsFromCity']), weather);
weather.reload();
assert.equal(weather.loc, '');
assert.equal(weather.getWeatherUrl(), '');
assert.equal(requests.length, 0);
config.services.weatherLocation = 'London';
weather.reload();
assert.equal(requests.length, 1);
assert(requests[0].url.startsWith('https://geocoding-api.open-meteo.com/'));
config.services.weatherLocation = '';
weather.reload();
requests[0].callback(JSON.stringify({results: [{latitude: 51.5, longitude: -0.1, name: 'London'}]}));
assert.equal(weather.loc, ''); // A stale response cannot reenable weather.
config.services.weatherLocation = '999,999';
weather.reload();
assert.equal(weather.loc, '');
config.services.weatherLocation = '51.5,-0.1';
weather.reload();
assert.equal(requests.length, 1); // Coordinates need no geolocation/reverse lookup.
assert(weather.getWeatherUrl().startsWith('https://api.open-meteo.com/'));

let writes = 0;
const notifs = vm.createContext({Privacy: privacy, loaded: true,
    storage: {setText: () => writes++},
    notClosed: [{time: new Date(), summary: 'recent'},
        {time: new Date(Date.now() - 2 * 86400000), summary: 'expired'}]});
notifs.root = notifs;
vm.runInContext(functions('shell/services/Notifs.qml', ['saveHistory', 'historyEntries']), notifs);
notifs.saveHistory();
assert.equal(writes, 0);
privacy.notificationRetentionDays = 1;
notifs.saveHistory();
assert.equal(writes, 1);
assert.equal(notifs.historyEntries().length, 1);
assert.equal(notifs.historyEntries()[0].summary, 'recent');
console.log('Privacy behavior checks passed');
