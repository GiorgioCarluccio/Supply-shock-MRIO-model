"""DEPRECATED. Parquet-first SAM extraction.

This script extracted the full long-format SAM to a local Parquet file. That
approach is no longer viable (size / memory) and has been replaced by the dense
matrix workflow, which materializes the matrix directly without storing the
full long SAM locally.

Use instead:

    .\\.venv\\Scripts\\python.exe scripts\\build_sam_dense_matrix_from_databricks.py
"""

import sys


def main() -> None:
    print(__doc__)
    print("This script is deprecated. Run build_sam_dense_matrix_from_databricks.py.")
    sys.exit(1)


if __name__ == "__main__":
    main()
