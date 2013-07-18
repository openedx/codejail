"""Helpers for codejail."""

import contextlib
import os
import shutil
import tempfile


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
