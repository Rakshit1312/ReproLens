from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class SourcegraphResult:
    path: str
    repository: str | None
    preview: str
    raw: dict[str, Any]


class SourcegraphService:
    """Small Sourcegraph adapter.

    Preferred mode is the Sourcegraph `src` CLI because it avoids coupling the
    project to an unstable GraphQL schema. HTTP GraphQL is retained as an
    optional fallback for installations that do not have `src` available.
    """

    def __init__(self, endpoint: str | None = None, token: str | None = None):
        self.endpoint = endpoint or os.getenv("SRC_ENDPOINT", "https://sourcegraph.com")
        self.token = token or os.getenv("SRC_ACCESS_TOKEN")

    def search(self, query: str, repo: str | None = None, limit: int = 10) -> list[SourcegraphResult]:
        sg_query = query if not repo else f"repo:{repo} {query}"
        cli = self._cli_search(sg_query, limit)
        if cli is not None:
            return cli
        return self._graphql_search(sg_query, limit)

    def _cli_search(self, query: str, limit: int) -> list[SourcegraphResult] | None:
        try:
            p = subprocess.run(
                ["src", "search", "-json", query],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if p.returncode != 0:
            return None
        try:
            payload = json.loads(p.stdout)
        except json.JSONDecodeError:
            return None
        return self._parse_results(payload, limit)

    def _graphql_search(self, query: str, limit: int) -> list[SourcegraphResult]:
        if not self.token:
            return []
        endpoint = self.endpoint.rstrip("/") + "/.api/graphql"
        gql = """
        query($query: String!) {
          search(query: $query) {
            results {
              results {
                ... on FileMatch {
                  repository { name }
                  file { path }
                  lineMatches { preview }
                }
              }
            }
          }
        }
        """
        body = json.dumps({"query": gql, "variables": {"query": f"{query} count:{limit}"}}).encode()
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={"Authorization": f"token {self.token}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                payload = json.loads(response.read().decode())
        except Exception:
            return []
        return self._parse_results(payload, limit)

    def _parse_results(self, payload: dict[str, Any], limit: int) -> list[SourcegraphResult]:
        raw_results = payload.get("data", {}).get("search", {}).get("results", {}).get("results", [])
        # `src search -json` and GraphQL can return slightly different shapes.
        if not raw_results:
            raw_results = payload.get("results", []) or payload.get("matches", [])
        results: list[SourcegraphResult] = []
        for item in raw_results[:limit]:
            file_obj = item.get("file", {}) if isinstance(item, dict) else {}
            path = file_obj.get("path") or item.get("path") or ""
            repo = item.get("repository", {})
            repo_name = repo.get("name") if isinstance(repo, dict) else repo
            previews = item.get("lineMatches") or item.get("line_matches") or []
            preview = "\n".join(
                str(x.get("preview", "")) for x in previews if isinstance(x, dict)
            )[:2000]
            results.append(SourcegraphResult(path=path, repository=repo_name, preview=preview, raw=item))
        return results
