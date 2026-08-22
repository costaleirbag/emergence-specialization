from __future__ import annotations

import json

from emergent_specialization.studies.mechanisms.measurement.analysis import run


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
