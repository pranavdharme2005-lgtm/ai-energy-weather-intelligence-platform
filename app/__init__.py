"""
AI-Powered Real-Time Energy Intelligence & Weather Analytics Platform.
Root package initialization with automatic sys.path resolution.
"""

import sys
from pathlib import Path

# Ensure project root directory is first entry in sys.path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
