import sys
from pathlib import Path

print("Python executable:")
print(sys.executable)

print("\nPython version:")
print(sys.version)

print("\nCurrent working directory:")
print(Path.cwd())

print("\nEnvironment guess:")
exe = sys.executable.lower()

if ".venv" in exe:
    print("Using main project environment: .venv")
else:
    print("Using global or unknown Python environment")
