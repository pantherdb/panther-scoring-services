"""`python -m panther_engine`: the same as the `panther-engine` command."""

import sys

from panther_engine.cli import main

if __name__ == "__main__":
    sys.exit(main())
