import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reprolens.extractor import fingerprint_ci, fingerprint_repository
from reprolens.diff import compare


def test_repository_extraction(tmp_path: Path):
    (tmp_path / ".nvmrc").write_text("20\n")
    (tmp_path / "package.json").write_text(json.dumps({"engines": {"node": ">=20"}}))
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("""jobs:\n  build:\n    runs-on: ubuntu-22.04\n    steps:\n      - uses: actions/setup-node@v6\n        with:\n          node-version: '18'\n""")
    fp = fingerprint_repository(tmp_path).to_dict()
    ci = fingerprint_ci(tmp_path).to_dict()
    assert fp["runtimes"]["node"]["value"] == "20"
    assert fp["requirements"]["node"]["value"] == ">=20"
    assert ci["platform"]["ci_runner"]["value"] == "ubuntu-22.04"
    assert ci["runtimes"]["node"]["value"] == "18"
    assert "ci_runner" not in fp["platform"]
    assert fp["runtimes"]["node"]["evidence"]
