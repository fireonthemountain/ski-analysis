import os
import sys
import tempfile

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

# Tests never touch the real data dir / database and never need the MediaPipe model.
_tmp = tempfile.mkdtemp(prefix="ski-tests-")
os.environ["DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["STORAGE_TYPE"] = "local"
os.environ["POSE_ESTIMATOR"] = "marker"
