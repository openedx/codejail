"""
Test JSON serialization straw
"""

import unittest

from codejail.safe_exec import json_safe


class JsonSafeTest(unittest.TestCase):
    """
    Test JSON serialization straw
    """

    # Unicode surrogate values
    SURROGATE_RANGE = list(range(0xD800, 0xE000))

    def test_unicode(self):
        # Test that json_safe() handles non-surrogate unicode values.

        # Try a few non-ascii UTF-16 characters
        for unicode_char in [chr(512), chr(2**8-1), chr(2**16-1)]:

            # Try it as a dictionary value
            result = json_safe({'test': unicode_char})
            self.assertEqual(result.get('test', None), unicode_char)

            # Try it as a dictionary key
            result = json_safe({unicode_char: 'test'})
            self.assertEqual(result.get(unicode_char, None), 'test')

    def test_surrogate_unicode_values(self):
        # Test that json_safe() excludes surrogate unicode values.

        # Try surrogate unicode values
        for code in self.SURROGATE_RANGE:
            unicode_char = chr(code)

            # Try it as a dictionary value
            json_safe({'test': unicode_char})
            # Different json libraries treat these bad Unicode characters
            # differently. All we care about is that no error is raised from
            # json_safe.

    def test_surrogate_unicode_keys(self):
        # Test that json_safe() excludes surrogate unicode keys.

        # Try surrogate unicode values
        for code in self.SURROGATE_RANGE:
            unicode_char = chr(code)

            # Try it is a dictionary key
            json_safe({unicode_char: 'test'})
            # Different json libraries treat these bad Unicode characters
            # differently. All we care about is that no error is raised from
            # json_safe.
