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
    SURROGATE_RANGE = range(55296, 57344)

    def test_unicode(self):
        """
        Test that json_safe() handles non-surrogate unicode values
        """

        # Try a few non-ascii UTF-16 characters
        for unicode_char in [unichr(512), unichr(2**8-1), unichr(2**16-1)]:

            # Try it as a dictionary value
            result = json_safe({'test': unicode_char})
            self.assertEqual(result.get('test', None), unicode_char)

            # Try it as a dictionary key
            result = json_safe({unicode_char: 'test'})
            self.assertEqual(result.get(unicode_char, None), 'test')

    def test_surrogate_unicode_values(self):
        """
        Test that json_safe() excludes surrogate unicode values
        """

        # Try surrogate unicode values
        for code in self.SURROGATE_RANGE:

            unicode_char = unichr(code)

            # Try it as a dictionary value
            result = json_safe({'test': unicode_char})
            self.assertFalse('test' in result)

    def test_surrogate_unicode_keys(self):
        """
        Test that json_safe() excludes surrogate unicode keys
        """

        # Try surrogate unicode values
        for code in self.SURROGATE_RANGE:

            unicode_char = unichr(code)

            # Try it is a dictionary key
            result = json_safe({unicode_char: 'test'})
            self.assertFalse(unicode_char in result)
