"""Import the unchanged, pinned native team runtime in its original module layout."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "vendor" / "native_teams"
sys.path.insert(0, str(NATIVE))
from runtime import Runtime, ROLES, Denied, Fenced  # noqa: E402
from storage import ScopedVFSStore  # noqa: E402
from vendor.native_vfs.model import ArtifactWrite  # noqa: E402
from vendor.native_vfs.store import canonical_json  # noqa: E402
