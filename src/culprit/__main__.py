"""Entry point so ``python -m culprit`` runs the same pipeline as ``culprit.run``."""

from culprit.run import main

if __name__ == "__main__":
    raise SystemExit(main())
