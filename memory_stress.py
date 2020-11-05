"""Memory-stress a long-running CodeJail-using process."""

from __future__ import absolute_import
from __future__ import print_function
from codejail import safe_exec
from six.moves import range

GOBBLE_CHUNK = int(1e7)

def main():
    gobble = []
    for i in range(int(1e7)):
        print(i)
        globs = {}
        safe_exec.safe_exec("a = 17", globs)
        assert globs["a"] == 17

        gobble.append("x"*GOBBLE_CHUNK)

if __name__ == "__main__":
    main()
