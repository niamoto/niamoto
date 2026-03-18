#!/usr/bin/env python3
"""Fetch targeted GBIF occurrence batches into regional CSV files.

This script uses the public GBIF occurrence search API and writes one CSV file
per target region under ``data/silver/gbif_targeted/<region>/``.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://api.gbif.org/v1/occurrence/search"
DEFAULT_TARGETS = (
    "new_caledonia=NC",
    "guyane=GF",
    "gabon=GA",
    "cameroon=CM",
)
DEFAULT_PAGE_SIZE = 300
DEFAULT_MAX_RECORDS = 5000
DEFAULT_MAX_SCAN_MULTIPLIER = 20
INSTITUTIONAL_BASIS_OF_RECORD = {
    "PRESERVED_SPECIMEN",
    "MATERIAL_SAMPLE",
    "OCCURRENCE",
}
INSTITUTIONAL_EXCLUDED_DATASET_FRAGMENTS = (
    "inaturalist",
    "observation.org",
    "ebird",
    "pl@ntnet",
    "plantnet",
    "artportalen",
    "artsobservasjoner",
    "naturgucker",
)

PREFERRED_COLUMNS = [
    "gbifID",
    "datasetKey",
    "datasetName",
    "basisOfRecord",
    "occurrenceID",
    "occurrenceStatus",
    "scientificName",
    "acceptedScientificName",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "species",
    "taxonRank",
    "taxonomicStatus",
    "country",
    "countryCode",
    "stateProvince",
    "county",
    "locality",
    "decimalLatitude",
    "decimalLongitude",
    "coordinateUncertaintyInMeters",
    "eventDate",
    "year",
    "month",
    "day",
    "recordedBy",
    "identifiedBy",
    "license",
    "references",
]


def parse_targets(raw_targets: list[str]) -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    for raw_target in raw_targets:
        if "=" not in raw_target:
            raise ValueError(
                f"Invalid target '{raw_target}'. Expected format '<slug>=<COUNTRYCODE>'."
            )
        slug, country_code = raw_target.split("=", 1)
        slug = slug.strip()
        country_code = country_code.strip().upper()
        if not slug or not country_code:
            raise ValueError(
                f"Invalid target '{raw_target}'. Expected format '<slug>=<COUNTRYCODE>'."
            )
        targets.append((slug, country_code))
    return targets


def build_request(params: dict[str, Any]) -> Request:
    query = urlencode(params)
    return Request(
        f"{API_URL}?{query}",
        headers={
            "Accept": "application/json",
            "User-Agent": "niamoto-gbif-targeted-fetcher/1.0",
        },
    )


def fetch_page(params: dict[str, Any]) -> dict[str, Any]:
    request = build_request(params)
    with urlopen(request) as response:
        return json.load(response)


def is_institutional_record(
    record: dict[str, Any],
    *,
    basis_of_record: set[str],
    excluded_dataset_fragments: tuple[str, ...],
) -> bool:
    record_basis = str(record.get("basisOfRecord") or "").upper()
    if basis_of_record and record_basis not in basis_of_record:
        return False

    dataset_name = str(record.get("datasetName") or "").lower()
    if any(fragment in dataset_name for fragment in excluded_dataset_fragments):
        return False

    has_institutional_field = any(
        str(record.get(field) or "").strip()
        for field in (
            "institutionCode",
            "collectionCode",
            "institutionID",
            "collectionKey",
        )
    )
    if not has_institutional_field:
        return False

    return True


def fetch_occurrences(
    *,
    country_code: str,
    kingdom_key: int,
    max_records: int,
    max_scan_records: int,
    page_size: int,
    pause_seconds: float,
    profile: str,
) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    offset = 0
    total_count = 0
    scanned_records = 0

    while len(records) < max_records and scanned_records < max_scan_records:
        limit = min(page_size, max_scan_records - scanned_records)
        payload = fetch_page(
            {
                "country": country_code,
                "kingdomKey": kingdom_key,
                "limit": limit,
                "offset": offset,
            }
        )
        total_count = int(payload.get("count", 0))
        page_results = payload.get("results", [])
        if not page_results:
            break
        scanned_records += len(page_results)
        if profile == "institutional":
            filtered_results = [
                record
                for record in page_results
                if is_institutional_record(
                    record,
                    basis_of_record=INSTITUTIONAL_BASIS_OF_RECORD,
                    excluded_dataset_fragments=INSTITUTIONAL_EXCLUDED_DATASET_FRAGMENTS,
                )
            ]
            records.extend(filtered_results)
        else:
            records.extend(page_results)
        if len(records) > max_records:
            records = records[:max_records]
        offset += len(page_results)
        if payload.get("endOfRecords", False):
            break
        if pause_seconds > 0:
            time.sleep(pause_seconds)

    return records, total_count


def collect_columns(records: list[dict[str, Any]]) -> list[str]:
    all_columns = set()
    for record in records:
        all_columns.update(record.keys())

    ordered = [column for column in PREFERRED_COLUMNS if column in all_columns]
    remaining = sorted(all_columns - set(ordered))
    return ordered + remaining


def serialize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def write_csv(path: Path, records: list[dict[str, Any]]) -> list[str]:
    columns = collect_columns(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {column: serialize_value(record.get(column)) for column in columns}
            )
    return columns


def write_metadata(
    path: Path,
    *,
    slug: str,
    country_code: str,
    kingdom_key: int,
    profile: str,
    max_records: int,
    max_scan_records: int,
    fetched_records: int,
    total_count: int,
    columns: list[str],
) -> None:
    metadata = {
        "slug": slug,
        "country_code": country_code,
        "kingdom_key": kingdom_key,
        "profile": profile,
        "requested_max_records": max_records,
        "max_scan_records": max_scan_records,
        "fetched_records": fetched_records,
        "total_count": total_count,
        "columns": columns,
        "source": "GBIF occurrence search API",
        "api_url": API_URL,
    }
    if profile == "institutional":
        metadata["institutional_filter"] = {
            "basis_of_record": sorted(INSTITUTIONAL_BASIS_OF_RECORD),
            "require_any_fields": [
                "institutionCode",
                "collectionCode",
                "institutionID",
                "collectionKey",
            ],
            "excluded_dataset_name_fragments": list(
                INSTITUTIONAL_EXCLUDED_DATASET_FRAGMENTS
            ),
        }
    path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch targeted GBIF batches into CSV files."
    )
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help="Target in the form '<slug>=<COUNTRYCODE>'. May be repeated.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/silver/gbif_targeted"),
        help="Base output directory.",
    )
    parser.add_argument(
        "--kingdom-key",
        type=int,
        default=6,
        help="GBIF kingdomKey filter. Defaults to Plantae (6).",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=DEFAULT_MAX_RECORDS,
        help="Maximum number of occurrences to fetch per target.",
    )
    parser.add_argument(
        "--max-scan-records",
        type=int,
        default=None,
        help=(
            "Maximum number of raw GBIF records to scan per target before filtering. "
            "Defaults to max-records for general profile and max-records * 20 for institutional."
        ),
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help="GBIF page size per request.",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=0.2,
        help="Pause between GBIF API calls.",
    )
    parser.add_argument(
        "--profile",
        choices=("general", "institutional"),
        default="general",
        help="Fetch profile. 'institutional' keeps only more collection-like datasets.",
    )
    args = parser.parse_args()

    raw_targets = args.target or list(DEFAULT_TARGETS)
    targets = parse_targets(raw_targets)
    max_scan_records = args.max_scan_records
    if max_scan_records is None:
        if args.profile == "institutional":
            max_scan_records = args.max_records * DEFAULT_MAX_SCAN_MULTIPLIER
        else:
            max_scan_records = args.max_records

    for slug, country_code in targets:
        print(f"[gbif:{args.profile}] fetching {slug} ({country_code}) ...")
        records, total_count = fetch_occurrences(
            country_code=country_code,
            kingdom_key=args.kingdom_key,
            max_records=args.max_records,
            max_scan_records=max_scan_records,
            page_size=args.page_size,
            pause_seconds=args.pause_seconds,
            profile=args.profile,
        )
        output_dir = args.out_dir / slug
        csv_path = output_dir / "occurrences.csv"
        metadata_path = output_dir / "metadata.json"
        columns = write_csv(csv_path, records)
        write_metadata(
            metadata_path,
            slug=slug,
            country_code=country_code,
            kingdom_key=args.kingdom_key,
            profile=args.profile,
            max_records=args.max_records,
            max_scan_records=max_scan_records,
            fetched_records=len(records),
            total_count=total_count,
            columns=columns,
        )
        print(
            f"[gbif:{args.profile}] wrote {len(records)} records for {slug} "
            f"({total_count} total available) -> {csv_path}"
        )


if __name__ == "__main__":
    main()
