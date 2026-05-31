"""DEPRECATED. Sparse SAM model-input builder.

This script read a local Parquet extract and built a sparse (.npz) Z matrix.
The SAM has no truly zero entries and small values are meaningful, so a sparse
representation is not appropriate. It has been replaced by the dense matrix
workflow.

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
