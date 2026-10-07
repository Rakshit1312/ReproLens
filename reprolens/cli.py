from __future__ import annotations

import argparse
import json
from pathlib import Path

from .diff import compare
from .extractor import fingerprint_ci, fingerprint_local, fingerprint_repository
from .orchestrator import analyze_repository


def main():
    parser = argparse.ArgumentParser(prog="reprolens", description="ReproLens environment fingerprinting V1")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fingerprint", help="Extract a repository fingerprint")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--local", action="store_true", help="Fingerprint the actual local machine")
    p.add_argument("--ci", action="store_true", help="Extract the CI-side GitHub Actions fingerprint")
    p.add_argument("--output", "-o")

    a = sub.add_parser("analyze", help="Run the ReproLens vertical analysis pipeline")
    a.add_argument("path", nargs="?", default=".")
    a.add_argument("--question", "-q")
    a.add_argument("--top-k", type=int, default=5)
    a.add_argument("--no-sourcegraph", action="store_true")

    c = sub.add_parser("compare", help="Compare two fingerprint JSON files")
    c.add_argument("development")
    c.add_argument("ci")
    c.add_argument("--output", "-o")

    args = parser.parse_args()
    if args.command == "analyze":
        result = analyze_repository(args.path, question=args.question, top_k=args.top_k, use_sourcegraph=not args.no_sourcegraph)
    elif args.command == "fingerprint":
        fp = fingerprint_local() if args.local else fingerprint_ci(args.path) if args.ci else fingerprint_repository(args.path)
        result = fp.to_dict()
    else:
        result = compare(json.loads(Path(args.development).read_text()), json.loads(Path(args.ci).read_text()))

    text = json.dumps(result, indent=2)
    if getattr(args, "output", None):
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
