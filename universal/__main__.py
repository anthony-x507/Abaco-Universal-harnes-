"""Allow `python -m universal` to run the CLI."""

from universal.cli import main

raise SystemExit(main())
