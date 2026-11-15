import json
import unittest

from vayoloop_security import html_text, json_for_script


class SecurityEncodingTests(unittest.TestCase):
    def test_html_text_escapes_markup_and_attributes(self):
        value = '<img src=x onerror="alert(1)"> & text'
        encoded = html_text(value)
        self.assertNotIn("<img", encoded)
        self.assertIn("&lt;img", encoded)
        self.assertIn("&quot;", encoded)
        self.assertIn("&amp;", encoded)

    def test_script_json_cannot_close_its_script_element(self):
        value = {"note": "</script><script>alert(1)</script>", "separator": "\\u2028"}
        encoded = json_for_script(value)
        self.assertNotIn("</script>", encoded.lower())
        self.assertNotIn("<", encoded)
        self.assertEqual(json.loads(encoded), value)


if __name__ == "__main__":
    unittest.main()
