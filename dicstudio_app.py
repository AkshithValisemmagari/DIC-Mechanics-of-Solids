"""Standalone launcher used by the DIC Studio Windows build."""
import os
import socket
import sys
from pathlib import Path

# Keep experiment output in the user's Documents folder, not inside the EXE bundle.
documents = Path.home() / "Documents"
data_dir = documents / "DIC Studio"
try:
    data_dir.mkdir(parents=True, exist_ok=True)
    probe = data_dir / ".write_test"
    probe.touch()
    probe.unlink()
except OSError:
    data_dir = Path.home() / "DIC Studio Data"
    data_dir.mkdir(parents=True, exist_ok=True)

os.environ["LAB_RUNS_DIR"] = str(data_dir / "outputs" / "interactive")
os.environ["MPLBACKEND"] = "Agg"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ.pop("PORT", None)

# Let multiple local apps coexist by selecting the first available port.
port = None
for candidate in range(8765, 8800):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", candidate))
        port = candidate
        break
    except OSError:
        continue

if port is None:
    raise RuntimeError("No available local port between 8765 and 8799.")

sys.argv = [sys.argv[0], "--host", "127.0.0.1", "--port", str(port)]

from lab_server import main

if __name__ == "__main__":
    main()
