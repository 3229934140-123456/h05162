"""Entry point for running noteman as a module."""
import sys

from noteman.core.dispatcher import main

if __name__ == "__main__":
    sys.exit(main())
