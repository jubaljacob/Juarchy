# Spotlight search

Press **Super + Space** to open Juarchy Spotlight on the active monitor.
The desktop menu remains on **Super + Alt + Space**.

Spotlight has one search field and one result list. There are no category tabs.
It identifies the query's context and keeps up to five results visible at once.
The card, search field and selected result are translucent; text and app icons
remain opaque, with desktop blur behind the rounded card.

| Input | Result |
| --- | --- |
| `chro` | Matching applications, with their installed icons |
| `settings` | Juarchy's main settings panel |
| `audio settings` | The corresponding settings page |
| `project report` | Strong personal-file matches |
| `12 * (8 + 3)` | Calculator answer |
| `10 kilometres to miles` | Offline unit conversion |
| `36 km/h to m/s` | Compound-unit conversion |
| `£100 to INR` | Currency conversion using reference rates |
| `what is a rainbow` | Automatic Wikipedia article preview and related links |
| `example.com` | Open the website |

Calculations and conversions show the answer without unrelated file suggestions.
Invalid conversions show a useful explanation instead of falling through to files
or a web search. Apps and Settings retain priority in ordinary searches. Web
search is offered when no strong local result exists. Clear questions and requests
such as `define entropy` or `tell me about Mars` automatically show an online preview
when no matching app, Settings destination or personal file exists.

Use arrow keys to select, **Enter** to open or copy an answer,
**Ctrl + Enter** to open a file's containing folder, and **Esc** to dismiss.
**Ctrl + Space** previews the selected file: images render inside the overlay;
other types show their filename and path.

Web previews appear in the same list: one leading article with a title of up to
two lines and a summary of up to three lines, followed by at most two compact
links. The source is labelled Wikipedia. **Enter** opens the selected article;
**Search web** in the footer or **Ctrl + Enter** opens the full query in DuckDuckGo.
While loading, Enter searches the web. Empty or failed previews keep a browser
search available.

To request a preview explicitly, press **Ctrl + W** or type `web your query`.
`files: your query` searches more broadly, including source/configuration files.
These optional prefixes resolve intent without switching the panel into separate tabs.

## Conversions

Conversions accept `to`, `in`, `into`, `as`, `=` or `→` between units, an optional
`convert` prefix, full names or symbols, plurals, negative values, thousands
separators, and scientific notation. Examples:

| Quantity | Examples |
| --- | --- |
| Length | `10 kilometres to miles`, `1e3 mm to metres` |
| Area | `10 square feet to m²`, `1 acre to hectares` |
| Volume | `1 cubic metre to litres`, `1 imperial gallon to L` |
| Mass | `5 pounds to kg`, `2 tonnes to lb` |
| Temperature | `32 F to C`, `273.15 Kelvin to Celsius` |
| Duration | `2 weeks to hours`, `500 ms to seconds` |
| Speed | `36 km/h to m/s`, `10 knots to mph` |
| Data size | `1 GiB to MiB`, `1 MB to Mb` |
| Data rate | `8 Mbps to MB/s` |
| Angle | `180 degrees to radians` |
| Frequency | `1 kHz to Hz` |
| Energy | `1 kWh to J`, `1 kcal to joules` |
| Power | `1 kW to W`, `1 hp to watts` |
| Pressure | `1 atm to Pa`, `1 bar to psi` |
| Force | `1 newton to kg*m/s^2` |
| Density | `1 g/cm³ to kg/m³` |
| Electrical quantities | `1000 mA to A`, `1 coulomb to A*s`, `1 F to microfarads` |
| Currency | `100 GBP to INR`, `20 pounds sterling to euros` |

The dimensional parser handles products, quotients, powers (`m²`, `m^2`, `m2`),
and metric prefixes on registered units. Bits and bytes are case sensitive:
`b` means bit, `B` means byte; `MB` is decimal and `MiB` is binary.
Single C/F/K/R with another temperature unit mean Celsius/Fahrenheit/Kelvin/Rankine;
compound or electrical targets resolve C/F as coulombs/farads.

US and imperial volumes differ. Specify `US gal`, `imperial gallon`, `US pint`,
`imperial pint`, `US cup`, `metric cup`, `US tbsp` or `US tsp`; bare ambiguous
names report an explanation. Tonnes, US short tons and imperial long tons are
separate units. Months and years are variable durations and are not silently
converted to a fixed number of days. Horsepower means mechanical horsepower;
calories are thermochemical calories. Unsupported units and incompatible
quantities are reported explicitly. This covers common measurement conversions,
not every specialised or context-dependent conversion.

Currency accepts three-letter codes without a fixed whitelist, regardless of case
or a space after the amount: `600gbp to aed` works. It also accepts common
names/symbols and official currency names when the desktop iso-codes package is installed. `$` means USD,
`£` GBP, `€` EUR and `₹` INR. Bare dollars mean USD; pounds paired with another
currency mean GBP. A pound-to-kilogram query remains a mass conversion.
Other dollar currencies need their name or code.
Availability depends on the rate providers: an unsupported or unavailable pair
is reported explicitly. These are daily reference rates, not bank fees or live
trading prices.

Math supports parentheses, powers, pi/e, sqrt, sin/cos/tan (radians), log (base 10),
ln, abs, and round. Arithmetic uses a bounded expression parser without evaluating code.

## Result relevance

`settings`, `preferences` and `settings panel` open Juarchy's main settings panel.
Specific searches such as `audio settings`, `wallpaper`, `wifi settings` and
`notification history` open the corresponding page. `display settings` finds the
installed display configuration app, where available.

Applications match their names, with exact names before whole words and word
prefixes. Incidental app-description text does not qualify. Strong app matches
precede files. The general Settings destination takes priority over partial app
names such as “Displays Settings” when searching `settings`.

File ranking uses exact filenames (with or without their extension), phrases,
whole words, then word prefixes. Spaces, underscores, hyphens and camelCase
boundaries are recognised. Matching strength comes before personal locations,
modification date and filename length. Very short queries need an exact name
or whole word.

Ordinary queries suggest common documents, spreadsheets, notes, images, audio,
video and folders. Source/configuration files appear when explicitly searched
with an extension, such as `settings.py`. Partial matches inside words and
project-internal documents are available with `files: query`. With an app or
Settings match, at most two exact filename/stem matches are shown.
Matching title words are highlighted and file results show their type and folder.
Background completion preserves selection when the result is still present.
App icons use the desktop entry and icon theme, with a generic fallback.

## Local files

The index includes Desktop, Documents, Downloads, Pictures, Videos, Music and
Projects under your home. Hidden entries, symbolic links and dependency/build
folders, virtual environments, caches and backup directories are excluded.
The index refreshes when the overlay opens if it is more
than ten minutes old, with a limit of 150,000 entries. Deleted files are filtered
from results immediately. It matches filenames, including partial names, rather
than document contents. Your file index is stored locally under
`~/.cache/juarchy/spotlight/` (or XDG_CACHE_HOME).

To customise the search roots, create `~/.config/juarchy/spotlight.json`
(or XDG_CONFIG_HOME) with an array of absolute paths or paths beginning with `~`:

```json
{
  "roots": ["~/Documents", "~/Downloads", "~/Projects"],
  "exclude_dirs": ["~/Projects/Old project"],
  "exclude_names": ["archives"],
  "auto_web_previews": true
}
```

Run `juarchy-spotlight reindex` after changing roots or to find new files sooner.
`exclude_dirs` excludes named paths and their contents; `exclude_names` excludes
directories with those names anywhere inside the search roots. Exclusions affect
both ordinary and explicit file queries. Settings and file search remain local.
No external indexing service or additional package is required.

## Online requests

App, Settings and matching file queries, offline conversions and calculations do
not send queries online. Context detection is local. Clear questions or requests
for definitions/topics without local matches go to Wikipedia after a 400-millisecond
typing pause. Ordinary unmatched words offer a browser search without sending
the query. DuckDuckGo receives it when you open the browser-search action.

Set `"auto_web_previews": false` in `spotlight.json` to require an explicit online
lookup. Questions then offer **Show instant online results** as a selectable action.
Ctrl + W and explicit web queries still request a preview. Wikipedia provides
article summaries, not a complete web search engine index or generated answers.
Use **Search web** for news, shopping and broader searches. Search and article
extracts are fetched together in one request.

Repeated web previews appear immediately from a memory cache shared across overlay
openings. It holds at most 32 queries, with successful previews expiring after five
minutes and empty/unavailable results after 30 seconds. Reading a cached preview
does not extend its expiry. A shell reload clears this cache. Queries and previews
are never saved to disk.

Web lookups have a two-second socket timeout and a 2.5-second overall deadline,
including slow DNS or a stalled response. When the provider fails, further
requests pause for 30 seconds while browser search remains available. Only the
provider's retry timestamp is saved locally; it contains no query or result.

Currency conversions use a shared local rate table. The first conversion downloads
rates based on EUR from the [Currency API](https://github.com/fawazahmed0/exchange-api).
If it is slow, [Frankfurter](https://frankfurter.dev/) starts after 350 milliseconds;
the Currency API Cloudflare mirror is the next fallback. The first valid table
covering both currencies wins. Each request has a two-second timeout and the
lookup has a three-second overall deadline. Failed services are skipped for five
minutes; repeated failures do not block every new query.

The same table serves different source currencies, targets and amounts using
`amount × target rate / source rate`. Providers receive only a request for the
EUR table, not your currencies, amount or full query. Successful tables are stored
locally for 24 hours. Previous installations' base-currency tables are reused
and promoted without another request when possible.

Cached answers appear immediately. When a table needs refreshing, the panel
keeps the dated cached answer visible while downloading rates, then updates it
in place. If refresh fails, the cached answer remains and its status explains
that refresh was unavailable. Without a cache, a loading row appears first and
is replaced by an answer or a clear error. Changing or clearing the query cancels
the obsolete helper instead of waiting for its request to finish. Ordinary local
searches use a 90-millisecond typing pause, explicit file queries use 220 ms,
and uncached web previews use 400 ms. Cached web previews bypass this pause and
do not start another helper or network request.

These are daily reference rates, not live trading prices or bank fees. The
result identifies its provider and observation date; cross-currency calculations
use the older of the two observation dates when they differ. Identical currencies
require no request. Unit conversion works offline.

Unit factors follow the SI and [NIST conversion tables](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9).

## Relationship to macOS Spotlight

This implements the shared entry point, app and filename search, calculator,
unit and currency conversions, online lookups, keyboard navigation and image
previews. Rich previews for PDFs/video, document-content indexing, dictionaries,
clipboard history, and email/calendar/account integrations are future extensions.
App-specific quick actions require each application's own integration; the
existing desktop menu continues to provide system actions.

Sources: [Apple Spotlight](https://support.apple.com/en-gb/guide/mac-help/mchlp1008/mac),
[Frankfurter API](https://frankfurter.dev/),
[MediaWiki search API](https://www.mediawiki.org/wiki/API:Search),
[MediaWiki article extracts](https://www.mediawiki.org/wiki/Extension:TextExtracts).
