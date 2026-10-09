from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import socket
import json

loader = SourceFileLoader('spotlight', str(Path(__file__).resolve().parents[1] / 'home/.local/bin/juarchy-spotlight'))
helper = module_from_spec(spec_from_loader(loader.name, loader))
loader.exec_module(helper)


TABLE = {'date': '2026-10-06', 'eur': {'eur': 1, 'gbp': .8, 'aed': 3.92, 'usd': 1, 'inr': 80, 'xcg': 1.84}}
FRANKFURTER = [
    {'date': TABLE['date'], 'base': 'EUR', 'quote': code.upper(), 'rate': value}
    for code, value in TABLE['eur'].items() if code != 'eur'
]


class SpotlightTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        for name, value in (('CACHE', Path(directory.name) / 'cache'), ('CONFIG', Path(directory.name) / 'config.json')):
            isolated = patch.object(helper, name, value)
            isolated.start()
            self.addCleanup(isolated.stop)
        memory = patch.object(helper, 'RATE_SNAPSHOT', None)
        memory.start()
        self.addCleanup(memory.stop)

    def test_calculator_precedence_and_functions(self):
        self.assertEqual(helper.calculate('12 * (8 + 3)'), 132)
        self.assertEqual(helper.calculate('sqrt(81) + 2^3'), 17)

    def test_calculator_rejects_code_and_unbounded_work(self):
        for query in ['__import__("os").system("true")', '[1]*100000000', '2^1000000', '9^(9^9)', 'True + 1']:
            with self.subTest(query=query), self.assertRaises((ValueError, SyntaxError)):
                helper.calculate(query)

    def test_units_and_temperature(self):
        self.assertAlmostEqual(float(helper.local('10 km to mi')[0]['value']), 6.213711922, places=8)
        self.assertEqual(helper.local('32 F to C')[0]['value'], '0')
        self.assertEqual(helper.local('1 GiB to MiB')[0]['value'], '1024')
        self.assertEqual(helper.local('1 kg to km'), [])

    def test_extended_conversion_categories_and_compound_units(self):
        cases = {
            '10 kilometres to miles': 6.213711922,
            '1e3 mm to metres': 1,
            '1,000 grams in kilograms': 1,
            'convert .5 litres into ml': 500,
            '10 square feet to m²': .9290304,
            '1 cubic metre to litres': 1000,
            '1 acre to hectares': .40468564224,
            '1 US gal to L': 3.785411784,
            '1 imperial gallon to litres': 4.54609,
            '36 km/h to m/s': 10,
            '1 g/cm³ to kg/m³': 1000,
            '2 weeks to hours': 336,
            '180 degrees to radians': helper.math.pi,
            '1 kWh to J': 3600000,
            '1 kcal to joules': 4184,
            '1 kW to W': 1000,
            '1 atm to Pa': 101325,
            '1 kHz to Hz': 1000,
            '1 newton to kg*m/s^2': 1,
            '1000 mA to A': 1,
            '1 coulomb to A*s': 1,
            '1 C to A*s': 1,
            '1 F to microfarads': 1000000,
            '1 MB to Mb': 8,
            '1 GiB to MiB': 1024,
            '8 Mbps to MB/s': 1,
            '0 Celsius to Fahrenheit': 32,
            '273.15 Kelvin to Celsius': 0,
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                result = helper.local(query)
                self.assertTrue(result)
                self.assertAlmostEqual(float(result[0]['value']), expected, delta=max(abs(expected) * 1e-9, 1e-10))

    def test_conversion_errors_are_answers_without_network_or_files(self):
        for query in ['1 kg to km', '1 gal to L', '-1 K to C', '1 month to days',
                      '1 GB to MHz', '1 m^100 to m', '1e999 km to mi', '1 squid to frogs', '2/0']:
            with self.subTest(query=query), \
                    patch.object(helper, 'fetch', side_effect=AssertionError('network called')), \
                    patch.object(helper, 'files', side_effect=AssertionError('files called')):
                rows, _, _ = helper.contextual(query)
                self.assertEqual(rows[0]['kind'], 'info')

    def test_context_routes_questions_urls_and_local_fallback_without_network(self):
        with patch.object(helper, 'fetch', side_effect=AssertionError('network called')), \
                patch.object(helper, 'files', return_value=([], 'Local files')) as files:
            rows, _, intent = helper.contextual('how do rainbows form', online_previews=False)
            self.assertEqual(intent, 'question')
            self.assertEqual([r['kind'] for r in rows], ['url', 'lookup'])
            self.assertIn('q=how+do+rainbows+form', rows[0]['value'])
            files.assert_called_once_with('how do rainbows form', broad=False)
            files.reset_mock()
            rows, _, intent = helper.contextual('example.com')
            self.assertEqual(intent, 'web')
            self.assertEqual(rows[0]['value'], 'https://example.com')
            rows, _, intent = helper.contextual('budget')
            self.assertEqual(intent, 'search')
            self.assertEqual(rows[0]['kind'], 'url')
            files.assert_called_once_with('budget', broad=False)
            helper.contextual('files: settings.py')
            files.assert_called_with('settings.py', broad=True)

    def test_explicit_web_uses_same_list_and_preserves_fallback(self):
        with patch.object(helper, 'fetch', side_effect=OSError('offline')), \
                patch.object(helper, 'files', side_effect=AssertionError('files called')):
            rows, status, intent = helper.contextual('web what is a rainbow')
            self.assertEqual(intent, 'web')
            self.assertEqual(rows[0]['kind'], 'url')
            self.assertIn('unavailable', status)

    def test_context_routes_currency_names_and_symbols_with_amount_local(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(helper, 'CACHE', Path(directory)), \
                patch.object(helper, 'fetch', return_value=TABLE) as fetch:
            rows, _, intent = helper.contextual('£10 to INR')
            self.assertEqual(intent, 'answer')
            self.assertEqual(rows[0]['value'], '1000.00')
            self.assertIn('/currencies/eur.min.json', fetch.call_args.args[0])
            rows, _, _ = helper.contextual('20 pounds sterling to rupees')
            self.assertEqual(rows[0]['value'], '2000.00')
            self.assertEqual(helper.contextual('20 pounds to rupees')[0][0]['value'], '2000.00')
            fetch.assert_called_once()

    def test_index_excludes_hidden_dependency_and_symlink_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = root / 'Documents'
            files.mkdir()
            for name in ['Report 100%.txt', 'Report_100.txt', '.secret']:
                (files / name).touch()
            for name in ['node_modules', '.git']:
                (files / name).mkdir()
                (files / name / 'Report hidden.txt').touch()
            (files / 'linked').symlink_to(root, target_is_directory=True)
            with patch.object(helper, 'CACHE', root / 'cache'), patch.object(helper, 'settings', return_value={'roots': [str(files)]}):
                helper.index_files()
                rows, _ = helper.files('Report')
                self.assertEqual(len(rows), 2)
                self.assertEqual(len(helper.files('100%')[0]), 1)
                self.assertEqual(len(helper.files('Report_')[0]), 2)  # Underscores are word boundaries.
                (files / 'Report_100.txt').unlink()
                self.assertEqual(len(helper.files('Report')[0]), 1)
                helper.index_files(force=True)
                self.assertEqual(len(helper.files('Report')[0]), 1)

    def test_file_relevance_and_clean_default_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = ['port.pdf', 'Port notes.md', 'report.pdf', 'transport.csv',
                     'settings.py', 'settings.json', 'Project_Report.pdf', 'Project-Report-notes.docx']
            for name in names:
                (root / name).touch()
            with patch.object(helper, 'CACHE', root / '.cache'), patch.object(helper, 'settings', return_value={'roots': [str(root)]}):
                helper.index_files()
                clean, _ = helper.files('port', broad=False)
                self.assertEqual([r['title'] for r in clean], ['port.pdf', 'Port notes.md'])
                broad, _ = helper.files('port')
                self.assertEqual([r['title'] for r in broad][:2], ['port.pdf', 'Port notes.md'])
                self.assertEqual({r['title'] for r in broad[2:]},
                                 {'report.pdf', 'transport.csv', 'Project_Report.pdf', 'Project-Report-notes.docx'})
                self.assertEqual(helper.files('settings', broad=False)[0], [])
                self.assertEqual(len(helper.files('settings')[0]), 2)
                self.assertEqual(helper.files('settings.py', broad=False)[0][0]['title'], 'settings.py')
                self.assertEqual(helper.files('project report', broad=False)[0][0]['title'], 'Project_Report.pdf')
                self.assertEqual(helper.files('project-report', broad=False)[0][0]['title'], 'Project_Report.pdf')
                self.assertEqual(helper.files('p', broad=False)[0], [])

    def test_exclusions_and_project_internals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['backups', 'cache', 'private', 'archives', 'src']:
                (root / name).mkdir()
                (root / name / 'Report notes.md').touch()
            (root / 'Report.md').touch()
            config = {'roots': [str(root)], 'exclude_dirs': [str(root / 'private')], 'exclude_names': ['archives']}
            with patch.object(helper, 'CACHE', root / '.cache'), patch.object(helper, 'settings', return_value=config):
                helper.index_files()
                self.assertEqual([r['title'] for r in helper.files('report', broad=False)[0]], ['Report.md'])
                self.assertEqual(len(helper.files('report')[0]), 2)  # Source docs remain in Files.

    def test_deleted_candidates_do_not_displace_valid_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i in range(45):
                (root / f'Report {i:02}.pdf').touch()
            with patch.object(helper, 'CACHE', root / '.cache'), patch.object(helper, 'settings', return_value={'roots': [str(root)]}):
                helper.index_files()
                for i in range(41):
                    (root / f'Report {i:02}.pdf').unlink()
                self.assertEqual(len(helper.files('report')[0]), 4)

    def test_old_index_is_migrated_even_when_recent(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / '.cache'
            cache.mkdir()
            with sqlite3.connect(cache / 'files.sqlite') as db:
                db.execute('CREATE TABLE files(path TEXT PRIMARY KEY, name TEXT, folded TEXT, folder INTEGER)')
            db.close()
            (root / 'Report.pdf').touch()
            with patch.object(helper, 'CACHE', cache), patch.object(helper, 'settings', return_value={'roots': [str(root)]}):
                helper.index_files()
                self.assertEqual(helper.files('report')[0][0]['title'], 'Report.pdf')

    def test_index_limit_is_enforced_inside_large_directories_and_fresh_index_is_skipped(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i in range(12):
                (root / f'Report {i}.pdf').touch()
            with patch.object(helper, 'CACHE', root / '.cache'), patch.object(helper, 'INDEX_LIMIT', 5), \
                    patch.object(helper, 'settings', return_value={'roots': [str(root)]}):
                self.assertTrue(helper.index_files())
                with helper.closing(sqlite3.connect(root / '.cache/files.sqlite')) as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM files').fetchone()[0], 5)
                with patch.object(helper.os, 'walk', side_effect=AssertionError('fresh index scanned again')):
                    self.assertFalse(helper.index_files())

    def test_compact_lowercase_currency_query_and_all_code_detection(self):
        for query in ['600gbp to aed', '600 GBP to AED', '600gbp in AED', 'convert 600gbp to aed']:
            with self.subTest(query=query):
                self.assertEqual(helper.currency_match(query), ('600', 'GBP', 'AED'))
        for target in ('AED', 'XCG', 'XAU', 'XXX'):
            self.assertEqual(helper.currency_match('600gbp to ' + target), ('600', 'GBP', target))
        self.assertEqual(helper.currency_match('600 pounds to UAE dirhams'), ('600', 'GBP', 'AED'))
        self.assertIsNone(helper.currency_match('1 kg to km'))

    def test_one_shared_table_serves_different_sources_targets_and_amounts(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(helper, 'CACHE', Path(directory)), \
                patch.object(helper, 'fetch', return_value=TABLE) as fetch:
            self.assertEqual(helper.currency('600gbp to aed')[0][0]['value'], '2940.00')
            self.assertEqual(helper.currency('1200gbp to aed')[0][0]['value'], '5880.00')
            self.assertEqual(helper.currency('10aed to gbp')[0][0]['value'], '2.04')
            self.assertEqual(helper.currency('10usd to inr')[0][0]['value'], '800.00')
            self.assertEqual(helper.currency('10gbp to xcg')[0][0]['value'], '23.00')
            fetch.assert_called_once()
            self.assertIn('/currencies/eur.min.json', fetch.call_args.args[0])
            self.assertNotIn('600', fetch.call_args.args[0])
            # A newly started helper can use the persisted table too.
            with patch.object(helper, 'RATE_SNAPSHOT', None), patch.object(helper, 'fetch', side_effect=AssertionError('network')):
                self.assertEqual(helper.currency('10inr to usd')[0][0]['value'], '0.12')

    def test_failed_first_service_falls_back_and_is_skipped_on_next_refresh(self):
        def provider(url, **kwargs):
            if 'jsdelivr' in url:
                raise URLError('first service down')
            return FRANKFURTER
        with tempfile.TemporaryDirectory() as directory, patch.object(helper, 'CACHE', Path(directory)), \
                patch.object(helper, 'fetch', side_effect=provider) as fetch:
            self.assertEqual(helper.currency('600gbp to aed')[0][0]['value'], '2940.00')
            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(helper.refresh_rates('USD', 'INR'), '')
            self.assertEqual(fetch.call_count, 3)
            self.assertIn('frankfurter', fetch.call_args.args[0])

    def test_second_fallback_host_is_used_when_other_services_fail(self):
        def provider(url, **kwargs):
            if 'pages.dev' not in url:
                raise OSError('service unavailable')
            return TABLE
        with tempfile.TemporaryDirectory() as directory, patch.object(helper, 'CACHE', Path(directory)), \
                patch.object(helper, 'fetch', side_effect=provider) as fetch:
            rows, _ = helper.currency('600gbp to aed')
            self.assertEqual(rows[0]['value'], '2940.00')
            self.assertIn('Cloudflare', rows[0]['detail'])
            self.assertEqual(fetch.call_count, 3)

    def test_stale_cache_returns_before_any_network_request(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(helper, 'CACHE', Path(directory)):
            snapshot = helper.normalise_snapshot(TABLE, 'cdn')
            snapshot['fetched'] -= helper.RATE_TTL + 1
            helper.atomic_json(Path(directory) / 'rates-shared.json', snapshot)
            with patch.object(helper, 'fetch', side_effect=AssertionError('network must not block cache')):
                rows, status = helper.currency('600gbp to aed')
                self.assertEqual(rows[0]['value'], '2940.00')
                self.assertTrue(rows[0]['refreshRates'])
                self.assertIn('cached rate', rows[0]['detail'])
                self.assertIn('refreshing', status)
            with patch.object(helper, 'fetch', side_effect=OSError('offline')):
                self.assertTrue(helper.refresh_rates('GBP', 'AED'))
                rows, status = helper.currency('600gbp to aed')
                self.assertEqual(rows[0]['value'], '2940.00')
                self.assertFalse(rows[0]['refreshRates'])
                self.assertIn('offline cached rate', rows[0]['detail'])

    def test_previous_install_table_is_promoted_and_used_for_another_source(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(helper, 'CACHE', Path(directory)):
            helper.atomic_json(Path(directory) / 'rates-GBP-daily.json', {
                'base': 'GBP', 'rates': {'gbp': 1, 'aed': 4.9, 'usd': 1.25},
                'date': '2026-10-06', 'fetched': helper.time.time(), 'provider': 'Currency API · jsDelivr'})
            with patch.object(helper, 'fetch', side_effect=AssertionError('network')):
                rows, _ = helper.currency('10usd to aed')
                self.assertEqual(rows[0]['value'], '39.20')
                self.assertFalse(rows[0]['refreshRates'])
                self.assertTrue((Path(directory) / 'rates-shared.json').exists())

    def test_stream_shows_cached_answer_before_refresh_and_updates_in_place(self):
        import io
        from contextlib import redirect_stdout
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory, patch.object(helper, 'CACHE', Path(directory)):
            snapshot = helper.normalise_snapshot(TABLE, 'cdn')
            snapshot['fetched'] -= helper.RATE_TTL + 1
            helper.atomic_json(Path(directory) / 'rates-shared.json', snapshot)
            updated = {'date': '2026-10-07', 'eur': {**TABLE['eur'], 'aed': 4}}
            def download(url, **kwargs):
                first = json.loads(output.getvalue().splitlines()[0])
                self.assertEqual(first['results'][0]['value'], '2940.00')
                return updated
            with patch('sys.argv', ['spotlight', 'search', '--stream', '--', '600gbp to aed']), \
                    patch.object(helper, 'fetch', side_effect=download), redirect_stdout(output):
                self.assertEqual(helper.main(), 0)
            emissions = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual(len(emissions), 2)
            self.assertEqual(emissions[1]['results'][0]['value'], '3000.00')
            self.assertFalse(emissions[1]['results'][0]['refreshRates'])

    def test_slow_primary_does_not_delay_fast_fallback(self):
        import threading
        import time
        release = threading.Event()
        def download(url, **kwargs):
            if 'jsdelivr' in url:
                release.wait(2)
                raise OSError('slow service')
            return FRANKFURTER
        try:
            with tempfile.TemporaryDirectory() as directory, patch.object(helper, 'CACHE', Path(directory)), \
                    patch.object(helper, 'RATE_HEDGE_DELAY', .02), patch.object(helper, 'fetch', side_effect=download):
                started = time.monotonic()
                self.assertEqual(helper.currency('600gbp to aed')[0][0]['value'], '2940.00')
                self.assertLess(time.monotonic() - started, .5)
        finally:
            release.set()

    def test_total_lookup_deadline_and_failure_cooldown(self):
        import threading
        import time
        release = threading.Event()
        def download(url, **kwargs):
            release.wait(2)
            raise OSError('slow service')
        try:
            with tempfile.TemporaryDirectory() as directory, patch.object(helper, 'CACHE', Path(directory)), \
                    patch.object(helper, 'RATE_HEDGE_DELAY', .02), patch.object(helper, 'RATE_DEADLINE', .12), \
                    patch.object(helper, 'fetch', side_effect=download) as fetch:
                started = time.monotonic()
                self.assertEqual(helper.currency('600gbp to aed')[0], [])
                self.assertLess(time.monotonic() - started, .5)
                count = fetch.call_count
                self.assertEqual(helper.currency('601gbp to aed')[0], [])
                self.assertEqual(fetch.call_count, count)
        finally:
            release.set()

    def test_all_sources_down_produces_visible_currency_error(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(helper, 'CACHE', Path(directory)), \
                patch.object(helper, 'fetch', side_effect=URLError(socket.gaierror(-3, 'DNS failure'))), \
                patch.object(helper, 'files', side_effect=AssertionError('No file fallback')):
            rows, status, intent = helper.contextual('600gbp to aed')
            self.assertEqual(intent, 'answer')
            self.assertEqual(rows[0]['kind'], 'info')
            self.assertIn('DNS', rows[0]['detail'])

    def test_unsupported_pair_does_not_disable_healthy_services_for_other_currencies(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(helper, 'CACHE', Path(directory)), \
                patch.object(helper, 'fetch', side_effect=lambda url, **kwargs: FRANKFURTER if 'frankfurter' in url else TABLE):
            rows, status, _ = helper.contextual('600gbp to xyz')
            self.assertEqual(rows[0]['kind'], 'info')
            self.assertIn('No current rate', status)
            self.assertEqual(helper.currency('600gbp to aed')[0][0]['value'], '2940.00')

    def test_invalid_rate_payload_and_mismatched_base_are_rejected(self):
        for invalid in [float('nan'), -1, 0, True, None]:
            with self.subTest(rate=invalid), self.assertRaises((ValueError, TypeError)):
                helper.normalise_snapshot({'date': '2026-10-06', 'eur': {'eur': 1, 'aed': invalid}}, 'cdn')
        with self.assertRaises(ValueError):
            helper.normalise_snapshot({'date': '2026-10-06', 'eur': {'eur': 2, 'gbp': .8}}, 'cdn')
        with self.assertRaises(ValueError):
            helper.normalise_snapshot([{'date': '2026-10-06', 'base': 'GBP', 'quote': 'AED', 'rate': 4.9}], 'frankfurter')

    def test_broken_cooldown_cache_and_unwritable_cache_do_not_hide_answer(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(helper, 'CACHE', Path(directory)), \
                patch.object(helper, 'fetch', return_value=TABLE):
            helper.atomic_json(Path(directory) / 'rates-provider-health.json', {'cdn': 'invalid'})
            helper.atomic_json(Path(directory) / 'rates-refresh-state.json', {'until': 'invalid', 'pairs': []})
            with patch.object(helper, 'atomic_json', side_effect=OSError('disk full')):
                self.assertEqual(helper.currency('600gbp to aed')[0][0]['value'], '2940.00')

    def test_stream_first_use_emits_loading_before_the_network_answer(self):
        import io
        from contextlib import redirect_stdout
        output = io.StringIO()
        def download(url, **kwargs):
            first = json.loads(output.getvalue().splitlines()[0])
            self.assertEqual(first['results'][0]['kind'], 'info')
            self.assertTrue(first['results'][0]['refreshRates'])
            return TABLE
        with tempfile.TemporaryDirectory() as directory, patch.object(helper, 'CACHE', Path(directory)), \
                patch('sys.argv', ['spotlight', 'search', '--stream', '--', '600gbp to aed']), \
                patch.object(helper, 'fetch', side_effect=download), redirect_stdout(output):
            self.assertEqual(helper.main(), 0)
        emissions = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(len(emissions), 2)
        self.assertEqual(emissions[1]['results'][0]['value'], '2940.00')

    def test_pair_cache_remains_usable_and_same_currency_requires_no_network(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(helper, 'CACHE', Path(directory)), \
                patch.object(helper, 'fetch', side_effect=AssertionError('network')):
            helper.atomic_json(Path(directory) / 'rate-GBP-AED.json', {
                'rate': 4.9, 'date': '2026-10-02', 'fetched': helper.time.time() - helper.RATE_TTL - 1})
            rows, _ = helper.currency('600gbp to aed')
            self.assertEqual(rows[0]['value'], '2940.00')
            self.assertTrue(rows[0]['refreshRates'])
            self.assertEqual(helper.currency('10usd to usd')[0][0]['value'], '10.00')

    def test_web_results_are_labelled_and_html_removed(self):
        from urllib.parse import parse_qs, urlsplit
        with patch.object(helper, 'fetch', return_value={'query': {'pages': [
                {'title': 'Earth', 'pageid': 42, 'index': 1, 'extract': '<span>Earth</span> &amp; space\nwith   oceans'}
        ]}}) as fetch:
            rows, _ = helper.web('earth & moon')
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['kind'], 'web')
            self.assertEqual(rows[0]['source'], 'Wikipedia')
            self.assertEqual(rows[0]['summary'], 'Earth & space with oceans')
            self.assertEqual(rows[0]['value'], 'https://en.wikipedia.org/?curid=42')
            self.assertIn('q=earth+%26+moon', rows[0]['searchUrl'])
            self.assertFalse(rows[0]['loading'])
            fetch.assert_called_once()
            request = parse_qs(urlsplit(fetch.call_args.args[0]).query)
            self.assertEqual(request['generator'], ['search'])
            self.assertEqual(request['gsrsearch'], ['earth & moon'])
            self.assertEqual(request['prop'], ['extracts|pageprops'])
            self.assertEqual(request['explaintext'], ['1'])
            self.assertEqual(request['exintro'], ['1'])

    def test_web_keeps_provider_order_and_caps_secondary_links(self):
        pages = [{'title': f'Article {i}', 'pageid': i, 'index': i, 'extract': 'Text',
                  'fullurl': 'javascript:untrusted'} for i in (4, 2, 1, 3)]
        with patch.object(helper, 'fetch', return_value={'query': {'pages': pages}}):
            rows, _ = helper.web('articles')
        self.assertEqual([r['title'] for r in rows], ['Article 1', 'Article 2', 'Article 3'])
        self.assertEqual([r['kind'] for r in rows], ['web', 'url', 'url'])
        self.assertTrue(all(r['role'] == 'web-link' for r in rows[1:]))
        self.assertTrue(all(r['value'].startswith('https://en.wikipedia.org/?curid=') for r in rows))

    def test_web_filters_missing_disambiguation_and_duplicate_pages(self):
        pages = [
            {'pageid': 1, 'title': 'Ambiguous', 'index': 1, 'pageprops': {'disambiguation': ''}},
            {'pageid': -1, 'title': 'Missing', 'index': 2, 'missing': True},
            {'pageid': 42, 'title': 'Article', 'index': 3, 'extract': None},
            {'pageid': 42, 'title': 'Duplicate', 'index': 4},
        ]
        with patch.object(helper, 'fetch', return_value={'query': {'pages': pages}}):
            rows, _ = helper.web('article')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['title'], 'Article')
        self.assertIn('unavailable', rows[0]['summary'])

    def test_web_empty_or_invalid_response_keeps_browser_search(self):
        for data in ({}, {'error': {'code': 'failure'}}, {'query': {'pages': {}}},
                     {'query': {'pages': [None]}}, {'query': {'pages': [{'pageid': 0}]}}):
            with self.subTest(data=data), patch.object(helper, 'fetch', return_value=data):
                (helper.CACHE / 'web-provider-health.json').unlink(missing_ok=True)
                rows, status = helper.web('topic')
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['kind'], 'url')
                self.assertIn('duckduckgo.com', rows[0]['value'])
                self.assertTrue('unavailable' in status or 'No article' in status)

    def test_clear_web_queries_are_automatic_but_local_matches_stay_local(self):
        with patch.object(helper, 'settings', return_value={}), \
                patch.object(helper, 'files', return_value=([], 'Local files')), \
                patch.object(helper, 'fetch', side_effect=AssertionError('loading must stay local')):
            for query in ('what is a rainbow', 'how do rainbows form', 'tell me about Mars', 'define entropy', 'rainbows?'):
                with self.subTest(query=query):
                    rows, _, intent = helper.contextual(query, allow_network=False)
                    self.assertEqual(intent, 'web')
                    self.assertTrue(rows[0]['loading'])
            rows, _, intent = helper.contextual('rainbows')
            self.assertEqual(intent, 'search')
            self.assertEqual(rows[0]['kind'], 'url')
            self.assertEqual(helper.contextual('2+2')[0][0]['value'], '4')
            self.assertEqual(helper.contextual('1 km to m')[0][0]['value'], '1000')
        file = helper.row('What is a rainbow.pdf', 'Documents', 'file', '/Documents/rainbow.pdf')
        file['score'] = 950
        with patch.object(helper, 'files', return_value=([file], 'Local files')), \
                patch.object(helper, 'fetch', side_effect=AssertionError('local file went online')):
            rows, _, intent = helper.contextual('what is a rainbow')
            self.assertEqual(intent, 'search')
            self.assertEqual(rows[0], file)

    def test_automatic_web_previews_can_be_disabled(self):
        with patch.object(helper, 'settings', return_value={'auto_web_previews': False}), \
                patch.object(helper, 'files', return_value=([], 'Local files')), \
                patch.object(helper, 'fetch', side_effect=AssertionError('disabled preview went online')):
            rows, _, intent = helper.contextual('what is a rainbow')
            self.assertEqual(intent, 'question')
            self.assertEqual([r['kind'] for r in rows], ['url', 'lookup'])
            rows, _, intent = helper.contextual('web rainbow', allow_network=False)
            self.assertEqual(intent, 'web')
            self.assertTrue(rows[0]['loading'])

    def test_web_query_normalisation_retains_the_topic(self):
        for query, expected in (('what is a rainbow?', 'rainbow'), ('Who was Ada Lovelace?', 'Ada Lovelace'),
                                ('define entropy', 'entropy'), ('tell me about the Moon', 'Moon'),
                                ('how do rainbows form', 'how do rainbows form')):
            with self.subTest(query=query):
                self.assertEqual(helper.web_terms(query), expected)

    def test_stream_web_emits_loading_before_preview_and_local_only_never_fetches(self):
        import io
        from contextlib import redirect_stdout
        output = io.StringIO()
        def provider(url, **kwargs):
            initial = json.loads(output.getvalue())
            self.assertTrue(initial['results'][0]['loading'])
            return {'query': {'pages': [{'title': 'Rainbow', 'pageid': 42, 'index': 1, 'extract': 'An optical phenomenon.'}]}}
        with patch.object(helper, 'settings', return_value={}), \
                patch.object(helper, 'files', return_value=([], 'Local files')), \
                patch.object(helper, 'fetch', side_effect=provider) as fetch, \
                patch('sys.argv', ['spotlight', 'search', '--stream', '--', 'what is a rainbow']), \
                redirect_stdout(output):
            self.assertEqual(helper.main(), 0)
        states = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(len(states), 2)
        self.assertEqual(states[1]['results'][0]['title'], 'Rainbow')
        self.assertFalse(states[1]['results'][0]['loading'])
        fetch.assert_called_once()
        output = io.StringIO()
        with patch.object(helper, 'files', return_value=([], 'Local files')), \
                patch.object(helper, 'fetch', side_effect=AssertionError('matching app query went online')), \
                patch('sys.argv', ['spotlight', 'search', '--stream', '--local-only', '--', 'who app']), \
                redirect_stdout(output):
            self.assertEqual(helper.main(), 0)
        self.assertEqual(len(output.getvalue().splitlines()), 1)
        self.assertEqual(json.loads(output.getvalue())['intent'], 'question')

    def test_web_offline_still_offers_browser_search(self):
        with patch.object(helper, 'fetch', side_effect=OSError('offline')):
            rows, status = helper.web('hello')
            self.assertEqual(len(rows), 1)
            self.assertIn('unavailable', status)

    def test_web_total_deadline_and_provider_cooldown_apply_to_different_queries(self):
        import threading
        import time
        release = threading.Event()
        finished = threading.Event()
        def download(url, **kwargs):
            try:
                release.wait(2)
                return {'query': {'pages': []}}
            finally:
                finished.set()
        try:
            with patch.object(helper, 'WEB_DEADLINE', .08), patch.object(helper, 'fetch', side_effect=download) as fetch:
                started = time.monotonic()
                rows, status = helper.web('what is a rainbow')
                self.assertLess(time.monotonic() - started, .5)
                self.assertEqual(rows[0]['previewState'], 'unavailable')
                self.assertIn('unavailable', status)
                self.assertEqual(helper.web('what is the moon', allow_network=False)[0][0]['kind'], 'url')
                self.assertEqual(helper.web('define entropy')[0][0]['kind'], 'url')
                fetch.assert_called_once()
                health = json.loads((helper.CACHE / 'web-provider-health.json').read_text())
                self.assertEqual(list(health), ['until'])
                self.assertNotIn('rainbow', json.dumps(health))
                with patch.object(helper.time, 'time', return_value=health['until'] + 1):
                    self.assertTrue(helper.web('define entropy', allow_network=False)[0][0]['loading'])
        finally:
            release.set()
            self.assertTrue(finished.wait(.5))

    def test_web_bad_cooldown_and_failed_cache_write_do_not_hide_results(self):
        helper.atomic_json(helper.CACHE / 'web-provider-health.json', {'until': 'invalid'})
        with patch.object(helper, 'fetch', return_value={'query': {'pages': [
                {'title': 'Rainbow', 'pageid': 42, 'index': 1, 'extract': 'An optical phenomenon.'}]}}), \
                patch.object(helper, 'atomic_json', side_effect=OSError('disk full')):
            self.assertEqual(helper.web('rainbow')[0][0]['kind'], 'web')
        with patch.object(helper, 'fetch', side_effect=OSError('offline')), \
                patch.object(helper, 'atomic_json', side_effect=OSError('disk full')):
            self.assertEqual(helper.web('rainbow')[0][0]['kind'], 'url')

    def test_local_search_never_uses_network(self):
        with patch.object(helper, 'fetch', side_effect=AssertionError('network called')):
            self.assertEqual(helper.local('100 USD to INR'), [])
            self.assertEqual(helper.local('2+2')[0]['value'], '4')
            self.assertEqual(helper.local('budget spreadsheet'), [])

    def test_all_mode_answers_do_not_search_or_list_unrelated_files(self):
        import io
        import json
        from contextlib import redirect_stdout
        output = io.StringIO()
        with patch('sys.argv', ['juarchy-spotlight', 'all', '2+2']), \
                patch.object(helper, 'files', side_effect=AssertionError('File search for calculation')), \
                redirect_stdout(output):
            self.assertEqual(helper.main(), 0)
        results = json.loads(output.getvalue())['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['value'], '4')


if __name__ == '__main__':
    unittest.main()
