"""The main program for the proxy process."""

import sys

from .proxy import proxy_main

if __name__ == "__main__":
    sys.exit(proxy_main(sys.argv))
