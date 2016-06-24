"""Helpers for codejail."""

import contextlib
import os
import shutil
import tempfile

try:
    import simplejson as json
except ImportError:
    import json


@contextlib.contextmanager
def temp_directory():
    """
    A context manager to make and use a temp directory.
    The directory will be removed when done.
    """
    temp_dir = tempfile.mkdtemp(prefix="codejail-")
    try:
        yield temp_dir
    finally:
        # if this errors, something is genuinely wrong, so don't ignore errors.
        shutil.rmtree(temp_dir)


@contextlib.contextmanager
def change_directory(new_dir):
    """
    A context manager to change the directory, and then change it back.
    """
    old_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield new_dir
    finally:
        os.chdir(old_dir)


def json_safe(input_dict):
    """
    Return a new `dict` containing only the JSON-safe part of `input_dict`.

    Used to emulate reading data through a serialization straw.
    """
    ok_types = (type(None), int, long, float, str, unicode, list, tuple, dict)
    bad_keys = ("__builtins__",)
    json_dict = {}
    for key, value in input_dict.iteritems():
        if not isinstance(value, ok_types):
            continue
        if key in bad_keys:
            continue
        try:
            # Python's JSON encoder will produce output that
            # the JSON decoder cannot parse if the input string
            # contains unicode "unpaired surrogates" (only on Linux)
            # To test for this, we try decoding the output and check
            # for a ValueError
            json.loads(json.dumps(value))

            # Also ensure that the keys encode/decode correctly
            json.loads(json.dumps(key))
        except (TypeError, ValueError):
            continue
        else:
            json_dict[key] = value
    return json.loads(json.dumps(json_dict))
