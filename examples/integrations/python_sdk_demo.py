"""Run from the repository root: python examples/integrations/python_sdk_demo.py"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sdk" / "python"))

from galaxy_sdk import GalaxyClient, JsonlSink  # noqa: E402


def main() -> None:
    output = Path(tempfile.mkdtemp(prefix="asterism-sdk-demo-")) / "events.jsonl"
    client = GalaxyClient(JsonlSink(output))
    with client.start_run(
        title="Customer churn investigation", objective="Identify reliable churn drivers"
    ) as run:
        with run.start_node(
            title="Investigate early-tenure churn", node_type="exploration"
        ) as node:
            node.create_claim(
                title="Early-tenure concentration",
                statement="Observed churn is concentrated in early tenure.",
            )
    print(output)


if __name__ == "__main__":
    main()
