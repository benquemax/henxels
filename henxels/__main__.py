"""Enable ``python -m henxels`` (used as a hook fallback when the script isn't on PATH)."""

import sys

from henxels.cli import main

if __name__ == "__main__":
    sys.exit(main())
