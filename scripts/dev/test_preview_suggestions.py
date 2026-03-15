#!/usr/bin/env python3
"""Test batch de toutes les previews de suggestions.

Lance des requêtes POST inline et GET pour chaque suggestion
et affiche un tableau récapitulatif des résultats.

Usage:
    # Avec le serveur lancé sur port 8080 :
    uv run python scripts/dev/test_preview_suggestions.py
    uv run python scripts/dev/test_preview_suggestions.py --group-by plots
    uv run python scripts/dev/test_preview_suggestions.py --port 5173
"""

import argparse
import re
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError
import json


def fetch(url, method="GET", body=None):
    """Fetch URL and return (status, body_text)."""
    try:
        req = Request(url, method=method)
        if body:
            req.add_header("Content-Type", "application/json")
            req.data = json.dumps(body).encode()
        with urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except URLError as e:
        return 0, str(e)
    except Exception as e:
        return -1, str(e)


def classify_html(html):
    """Classify preview HTML response."""
    if not html or not html.strip():
        return "EMPTY", "Réponse vide"

    # Extract body content
    body_match = re.search(r"<body>(.*?)</body>", html, re.DOTALL)
    body = body_match.group(1).strip() if body_match else html.strip()

    if not body:
        return "EMPTY", "Body vide"

    # Check for error
    error_match = re.search(r"class=['\"]error['\"]>([^<]+)", body)
    if error_match:
        return "ERROR", error_match.group(1).strip()[:60]

    # Check for info message (no data, etc.)
    info_match = re.search(r"class=['\"]info['\"]>([^<]+)", body)
    if info_match:
        return "INFO", info_match.group(1).strip()[:60]

    # Check for Plotly chart
    if "plotly-graph-div" in body or "Plotly.newPlot" in body:
        return "OK", "Plotly chart"

    # Check for widget content (specific class markers, not bare <div>)
    if "widget" in body.lower() or 'class="widget' in body or 'id="widget' in body:
        return "OK", "Widget HTML"

    # Check for navigation
    if "nav" in body.lower() or "tree" in body.lower():
        return "OK", "Navigation"

    return "UNKNOWN", "Unrecognized HTML"


def build_inline_body(suggestion, group_by):
    """Build POST inline body from a suggestion."""
    widget_plugin = suggestion.get("widget_plugin")
    widget_config = suggestion.get("widget_params")
    plugin = suggestion.get("plugin")  # transformer plugin
    config = suggestion.get("config", {})  # transformer params

    if not widget_plugin or not plugin:
        return None

    return {
        "group_by": group_by,
        "mode": "full",
        "inline": {
            "transformer_plugin": plugin,
            "transformer_params": config,
            "widget_plugin": widget_plugin,
            "widget_params": widget_config,
            "widget_title": suggestion.get("name", "Preview"),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Test batch des previews de suggestions"
    )
    parser.add_argument("--port", type=int, default=8080, help="Port du serveur API")
    parser.add_argument("--group-by", default="taxons", help="Groupe à tester")
    parser.add_argument("--host", default="localhost", help="Hôte du serveur")
    args = parser.parse_args()

    base = f"http://{args.host}:{args.port}"
    group_by = args.group_by

    # 1. Fetch suggestions
    print(f"\n  Récupération des suggestions pour '{group_by}'...")
    status, body = fetch(f"{base}/api/templates/{group_by}/suggestions")
    if status != 200:
        print(f"  ERREUR: GET suggestions retourne {status}")
        print(f"  {body[:200]}")
        sys.exit(1)

    try:
        data = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        print(f"  ERREUR: réponse non-JSON: {body[:200]}")
        sys.exit(1)
    suggestions = data.get("suggestions", [])
    print(f"  {len(suggestions)} suggestions trouvées\n")

    if not suggestions:
        print("  Aucune suggestion. Vérifiez que l'instance a des données importées.")
        sys.exit(0)

    # 2. Test each suggestion
    COL_W = 55
    results = []

    header = f"  {'SUGGESTION':<{COL_W}} {'POST':>6} {'GET':>6}  DÉTAIL"
    sep = "  " + "-" * (COL_W + 40)
    print(header)
    print(sep)

    for s in suggestions:
        tid = s["template_id"]
        short_tid = tid[: COL_W - 2] + ".." if len(tid) > COL_W else tid

        # POST inline
        post_body = build_inline_body(s, group_by)
        if post_body:
            post_status, post_html = fetch(f"{base}/api/preview", "POST", post_body)
            post_class, post_detail = (
                classify_html(post_html)
                if post_status == 200
                else ("FAIL", f"HTTP {post_status}")
            )
        else:
            post_class, post_detail = "SKIP", "Pas de widget_plugin"

        # GET
        source_param = (
            f"&source={s.get('source_name', '')}"
            if s.get("source_name") and s["source_name"] != "occurrences"
            else ""
        )
        get_url = (
            f"{base}/api/preview/{tid}?group_by={group_by}&mode=full{source_param}"
        )
        get_status, get_html = fetch(get_url)
        get_class, get_detail = (
            classify_html(get_html)
            if get_status == 200
            else ("FAIL", f"HTTP {get_status}")
        )

        # Symbols
        symbols = {
            "OK": "✓",
            "ERROR": "✗",
            "INFO": "~",
            "EMPTY": "✗",
            "FAIL": "✗",
            "SKIP": "-",
            "UNKNOWN": "?",
        }
        post_sym = symbols.get(post_class, "?")
        get_sym = symbols.get(get_class, "?")

        # Pick most informative detail
        detail = ""
        if post_class not in ("OK", "SKIP"):
            detail = f"POST: {post_detail}"
        if get_class != "OK":
            detail = (
                f"GET: {get_detail}" if not detail else f"{detail} | GET: {get_detail}"
            )

        line = f"  {short_tid:<{COL_W}} {post_sym:>6} {get_sym:>6}  {detail}"
        print(line)

        results.append(
            {
                "template_id": tid,
                "post": post_class,
                "get": get_class,
                "post_detail": post_detail,
                "get_detail": get_detail,
            }
        )

    # 3. Summary
    print(sep)
    total = len(results)
    post_ok = sum(1 for r in results if r["post"] == "OK")
    post_skip = sum(1 for r in results if r["post"] == "SKIP")
    get_ok = sum(1 for r in results if r["get"] == "OK")
    post_fail = total - post_ok - post_skip
    get_fail = total - get_ok

    print(f"\n  RÉSUMÉ: {total} suggestions testées")
    print(f"    POST inline : {post_ok} OK, {post_skip} skip, {post_fail} erreurs")
    print(f"    GET direct  : {get_ok} OK, {get_fail} erreurs")

    # List failures
    failures = [
        r for r in results if r["post"] not in ("OK", "SKIP") or r["get"] != "OK"
    ]
    if failures:
        print(f"\n  ÉCHECS ({len(failures)}):")
        for r in failures:
            issues = []
            if r["post"] not in ("OK", "SKIP"):
                issues.append(f"POST={r['post_detail']}")
            if r["get"] != "OK":
                issues.append(f"GET={r['get_detail']}")
            print(f"    {r['template_id']}")
            for issue in issues:
                print(f"      → {issue}")
    else:
        print("\n  Tous les widgets fonctionnent !")

    print()
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
