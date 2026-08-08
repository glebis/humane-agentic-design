"""Put `evals/contrast/` on the import path so the tests import the harness the
way the CLI does — `import generate`, `import oracle`, `import score` — rather
than through a package alias that only exists under pytest.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contrast"))
