"""pytest 를 어느 위치에서 돌려도 저장소 루트를 import 경로에 넣는다.

scripts/tests 가 실행 위치에 묶여 있던 문제와 같은 종류를 미리 막는다.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
