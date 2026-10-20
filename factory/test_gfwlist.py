import unittest
from unittest.mock import patch

from factory import gfwlist


class OfficialSourceTests(unittest.TestCase):
    def test_import_does_not_download(self):
        self.assertEqual(gfwlist.unhandle_rules, [])

    def test_generation_fetches_only_official_source(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'manual_gfwlist_excludes.txt').write_text('www.douyin.com\n')
            text = '\n'.join(f'||site{i}.example' for i in range(1100))
            text += '\n||www.douyin.com\n'
            with patch.object(gfwlist, '__file__', str(root / 'gfwlist.py')), \
                 patch('sys.argv', ['gfwlist.py']), \
                 patch.object(gfwlist, 'get_rule', return_value=text) as fetch:
                gfwlist.main()
            fetch.assert_called_once_with(gfwlist.OFFICIAL_URL, ruleType='base64')
            result = (root / 'resultant/gfw.list').read_text()
            self.assertNotIn('douyin', result)
            self.assertEqual(len(result.splitlines()), 1100)


if __name__ == '__main__':
    unittest.main()
