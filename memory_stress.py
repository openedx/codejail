"""Memory-stress a long-running CodeJail-using process."""

from codejail import safe_exec

GOBBLE_CHUNK = int(1e7)

def main():
    gobble = []
    for i in xrange(int(1e7)):
        print i
        globs = {}
        safe_exec.safe_exec("a = 17", globs)
        assert globs["a"] == 17

        gobble.append("x"*GOBBLE_CHUNK)

if __name__ == "__main__":
    main()
