"""The main program for the proxy process."""

from __future__ import absolute_import
import sys

from codejail.proxy import proxy_main

if __name__ == "__main__":
    sys.exit(proxy_main(sys.argv))
