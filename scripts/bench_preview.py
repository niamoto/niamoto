#!/usr/bin/env python3
"""
Benchmark du système de preview unifié.

Mesure les temps de réponse P50/P95/P99 pour les routes :
  - GET /api/preview/{template_id}
  - POST /api/preview (inline mode)

Usage :
  uv run python scripts/bench_preview.py [--base-url http://localhost:8000] [--iterations 20]
"""

import argparse
import statistics
import sys
import time

import httpx


def fetch_template_ids(base_url: str) -> list[str]:
    """Récupère les template IDs disponibles via l'API layout."""
    group_bys = []
    try:
        resp = httpx.get(f"{base_url}/api/config", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            group_bys = list(data.get("group_configs", {}).keys())
    except Exception:
        pass

    if not group_bys:
        group_bys = ["taxon"]

    template_ids = []
    for gb in group_bys:
        try:
            resp = httpx.get(f"{base_url}/api/layout/{gb}", timeout=10)
            if resp.status_code == 200:
                layout = resp.json()
                for w in layout.get("widgets", []):
                    ds = w.get("data_source")
                    if ds:
                        template_ids.append(ds)
        except Exception:
            pass

    return template_ids


def bench_get_preview(
    client: httpx.Client, base_url: str, template_id: str, group_by: str = "taxon"
) -> float:
    """Benchmark GET /api/preview/{template_id}. Retourne le temps en ms."""
    url = f"{base_url}/api/preview/{template_id}?group_by={group_by}"
    start = time.perf_counter()
    resp = client.get(url, timeout=30)
    elapsed = (time.perf_counter() - start) * 1000
    if resp.status_code != 200:
        print(f"  WARN: GET {template_id} → {resp.status_code}", file=sys.stderr)
    return elapsed


def bench_post_preview(
    client: httpx.Client,
    base_url: str,
    group_by: str = "taxon",
) -> float:
    """Benchmark POST /api/preview (inline mode). Retourne le temps en ms."""
    payload = {
        "group_by": group_by,
        "inline": {
            "transformer_plugin": "occurrence_count",
            "transformer_params": {},
            "widget_plugin": "bar_plot",
            "widget_title": "Benchmark test",
        },
    }
    start = time.perf_counter()
    resp = client.post(f"{base_url}/api/preview", json=payload, timeout=30)
    elapsed = (time.perf_counter() - start) * 1000
    if resp.status_code != 200:
        print(f"  WARN: POST inline → {resp.status_code}", file=sys.stderr)
    return elapsed


def percentile(data: list[float], p: int) -> float:
    """Calcule le percentile p d'une liste de valeurs."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[f]
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def print_stats(label: str, times: list[float]) -> None:
    """Affiche les statistiques d'un lot de mesures."""
    if not times:
        print(f"  {label}: aucune mesure")
        return

    p50 = percentile(times, 50)
    p95 = percentile(times, 95)
    p99 = percentile(times, 99)
    mean = statistics.mean(times)
    std = statistics.stdev(times) if len(times) > 1 else 0.0

    print(f"  {label}:")
    print(f"    Requêtes : {len(times)}")
    print(f"    Moyenne  : {mean:8.1f} ms  (σ = {std:.1f})")
    print(f"    P50      : {p50:8.1f} ms")
    print(f"    P95      : {p95:8.1f} ms")
    print(f"    P99      : {p99:8.1f} ms")
    print(f"    Min/Max  : {min(times):8.1f} / {max(times):.1f} ms")

    # Vérification critère plan : P95 < 1500ms
    if p95 < 1500:
        print("    ✓ P95 < 1500ms (critère plan respecté)")
    else:
        print("    ✗ P95 ≥ 1500ms (critère plan NON respecté)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark preview engine")
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="URL de base de l'API"
    )
    parser.add_argument(
        "--iterations", type=int, default=20, help="Nombre d'itérations par template"
    )
    parser.add_argument("--group-by", default="taxon", help="Groupe de référence")
    parser.add_argument(
        "--warmup", type=int, default=2, help="Itérations de warmup (non comptées)"
    )
    args = parser.parse_args()

    print("=== Benchmark Preview Engine ===")
    print(f"Base URL    : {args.base_url}")
    print(f"Group by    : {args.group_by}")
    print(f"Itérations  : {args.iterations} (+{args.warmup} warmup)")
    print()

    # Découverte des templates
    print("Découverte des templates...")
    template_ids = fetch_template_ids(args.base_url)
    if not template_ids:
        print(
            "Aucun template trouvé. Vérifiez que le serveur est démarré.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"  {len(template_ids)} templates trouvés : {', '.join(template_ids[:5])}{'...' if len(template_ids) > 5 else ''}"
    )
    print()

    all_get_times: list[float] = []

    with httpx.Client() as client:
        # Benchmark GET par template
        for tid in template_ids:
            print(f"GET /api/preview/{tid}")

            # Warmup
            for _ in range(args.warmup):
                bench_get_preview(client, args.base_url, tid, args.group_by)

            # Mesures
            times = []
            for _ in range(args.iterations):
                t = bench_get_preview(client, args.base_url, tid, args.group_by)
                times.append(t)

            print_stats(tid, times)
            all_get_times.extend(times)
            print()

        # Résumé GET
        if all_get_times:
            print("--- Résumé GET (tous templates) ---")
            print_stats("GET /api/preview/*", all_get_times)
            print()

        # Benchmark POST inline
        print("POST /api/preview (inline)")
        for _ in range(args.warmup):
            bench_post_preview(client, args.base_url, args.group_by)

        post_times = []
        for _ in range(args.iterations):
            t = bench_post_preview(client, args.base_url, args.group_by)
            post_times.append(t)

        print_stats("POST inline", post_times)
        print()

    print("=== Fin du benchmark ===")


if __name__ == "__main__":
    main()
