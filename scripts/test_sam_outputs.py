"""DEPRECATED. Tests for the sparse (.npz) SAM outputs.

Replaced by the dense matrix test.

Use instead:

    .\\.venv\\Scripts\\python.exe scripts\\test_sam_dense_matrix.py
"""

import sys


def main() -> None:
    print(__doc__)
    print("This script is deprecated. Run test_sam_dense_matrix.py.")
    sys.exit(1)


if __name__ == "__main__":
    main()
