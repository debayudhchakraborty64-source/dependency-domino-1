import sys
from pathlib import Path

# Ensure backend package is importable from tests directory
sys.path.insert(0, str(Path(__file__).parent.parent))
