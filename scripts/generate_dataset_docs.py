#!/usr/bin/env python3
"""Generate LLM-friendly dataset indexes from data.bs.ch using public Explore API."""

from __future__ import annotations

import json
import logging
import re
import sys
from html import unescape
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = ROOT / "llms" / "datasets"
BY_THEME_DIR = DATASETS_DIR / "by-theme"
FULL_DATASETS_DIR = DATASETS_DIR / "full"
LOG = logging.getLogger("generate_dataset_docs")
API_BASE = "https://data.bs.ch/api/explore/v2.1"
CATALOG_ENDPOINT = f"{API_BASE}/catalog/datasets"

CANONICAL_THEME_NAMES = [
    "Arbeit, Erwerb",
    "Bau- und Wohnungswesen",
    "Bevölkerung",
    "Bildung, Wissenschaft",
    "Energie",
    "Finanzen",
    "Gebäude",
    "Geographie",
    "Gesetzgebung",
    "Gesundheit",
    "Handel",
    "Industrie, Dienstleistungen",
    "Kriminalität, Strafrecht",
    "Kultur, Medien, Informationsgesellschaft, Sport",
    "Land- und Forstwirtschaft",
    "Mobilität und Verkehr",
    "Politik",
    "Preise",
    "Raum und Umwelt",
    "Soziale Sicherheit",
    "Statistische Grundlagen",
    "Tourismus",
    "Verwaltung",
    "Volkswirtschaft",
    "Öffentliche Ordnung und Sicherheit",
]

THEME_ALIASES = {
    "Bildung": "Bildung, Wissenschaft",
    "Wissenschaft": "Bildung, Wissenschaft",
    "Kultur": "Kultur, Medien, Informationsgesellschaft, Sport",
}

CANONICAL_THEME_SET = set(CANONICAL_THEME_NAMES)


def configure_logging() -> None:
    """Configure script logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def fetch_json(url: str) -> dict:
    """Fetch and decode JSON from a URL.

    Args:
        url: Absolute URL to fetch.

    Returns:
        Decoded JSON payload.

    Raises:
        RuntimeError: If the request fails.
    """
    try:
        with urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc}") from exc


def slugify(value: str) -> str:
    """Convert theme labels into stable ASCII slugs.

    Args:
        value: Raw theme label.

    Returns:
        URL/file-safe slug.
    """
    value = value.strip().lower()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unknown"


def iter_datasets() -> list[dict]:
    """Fetch all public datasets using Explore API pagination."""
    datasets: list[dict] = []
    limit = 100
    offset = 0
    total_count: int | None = None

    while True:
        url = f"{CATALOG_ENDPOINT}?limit={limit}&offset={offset}"
        payload = fetch_json(url)
        results = payload.get("results", [])
        if total_count is None:
            total_count = int(payload.get("total_count", 0))
            LOG.info("Explore API total datasets reported: %s", total_count)
        datasets.extend(results)
        offset += len(results)
        LOG.info("Fetched %s/%s datasets", offset, total_count)
        if not results or offset >= total_count:
            break

    return datasets


def get_default_meta(dataset: dict) -> dict:
    """Return default metadata block from a dataset record."""
    metas = dataset.get("metas", {})
    return metas.get("default", {}) if isinstance(metas, dict) else {}


def extract_theme_names(dataset: dict) -> list[str]:
    """Extract and normalize theme names from a dataset record.

    Args:
        dataset: Explore API dataset record.

    Returns:
        Normalized theme names.
    """
    metas = dataset.get("metas", {})
    default_meta = metas.get("default", {})
    themes = default_meta.get("theme")
    if not isinstance(themes, list):
        return ["Uncategorized"]

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_theme in themes:
        theme = str(raw_theme).strip()
        if not theme:
            continue

        canonical = THEME_ALIASES.get(theme, theme)
        if canonical not in CANONICAL_THEME_SET:
            LOG.warning("Unknown theme label encountered: %s", theme)
        if canonical not in seen:
            normalized.append(canonical)
            seen.add(canonical)

    return normalized or ["Uncategorized"]


def extract_title(dataset: dict) -> str:
    """Extract dataset title with fallback to dataset identifier."""
    default_meta = get_default_meta(dataset)
    title = default_meta.get("title")
    if title:
        return str(title).strip()
    return dataset.get("dataset_id", "unknown-dataset")


def extract_modified(dataset: dict) -> str:
    """Extract modified timestamp or return n/a."""
    default_meta = get_default_meta(dataset)
    value = default_meta.get("modified")
    return str(value).strip() if value else "n/a"


def extract_records_count(dataset: dict) -> str:
    """Extract records count or return n/a."""
    default_meta = get_default_meta(dataset)
    value = default_meta.get("records_count")
    return str(value) if value is not None else "n/a"


def write_text(path: Path, content: str) -> None:
    """Write text content to file, creating directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def escape_md_cell(value: str) -> str:
    """Escape markdown table cell content."""
    return value.replace("|", "\\|").replace("\n", " ").strip()


def strip_html(value: str) -> str:
    """Remove HTML tags and decode entities for compact text output."""
    no_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(no_tags)).strip()


def format_scalar(value: object) -> str:
    """Format scalar/list values without JSON serialization."""
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        if not value:
            return "n/a"
        return "; ".join(format_scalar(item) for item in value)
    return strip_html(str(value))


def get_nested(source: dict, path: tuple[str, ...]) -> object:
    """Safely read nested dictionary values."""
    current: object = source
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def build_key_value_table(rows: list[tuple[str, object]]) -> list[str]:
    """Render ordered key/value pairs as markdown table."""
    lines = [
        "| key | value |",
        "|---|---|",
    ]
    for key, value in rows:
        lines.append(f"| {escape_md_cell(key)} | {escape_md_cell(format_scalar(value))} |")
    return lines


def render_dataset_link(dataset_id: str) -> str:
    """Build the public dataset page URL."""
    return f"https://data.bs.ch/explore/dataset/{dataset_id}/"


def render_dataset_api_link(dataset_id: str) -> str:
    """Build the Explore API dataset metadata URL."""
    return f"{CATALOG_ENDPOINT}/{dataset_id}"


def render_full_page_filename(dataset_id: str) -> str:
    """Build filename for per-dataset full detail page."""
    return f"{dataset_id}.md"


def build_full_index(datasets: list[dict], generated_at: str) -> str:
    """Build compact index page for full per-dataset metadata/schema pages."""
    lines = [
        "# data.bs.ch full dataset context",
        "",
        f"_Generated: {generated_at}_",
        "",
        "This index points to the bundled full context and the enriched main dataset table.",
        "",
        f"- Total datasets: **{len(datasets)}**",
        "- Full context bundle: [all.md](./all.md)",
        "- Back to dataset index: [../index.md](../index.md)",
        "",
        "Per-dataset `full page` and `api metadata` links are now included directly in the main dataset table:",
        "- [Open main dataset index](../index.md)",
        "",
    ]
    return "\n".join(lines)


def build_schema_table(fields: list[dict]) -> list[str]:
    """Render schema fields as a markdown table."""
    lines = [
        "| name | type | label | description | annotations |",
        "|---|---|---|---|---|",
    ]
    for field in fields:
        name = escape_md_cell(str(field.get("name", "")))
        field_type = escape_md_cell(str(field.get("type", "")))
        label = escape_md_cell(str(field.get("label", "")))
        description = escape_md_cell(
            strip_html(str(field.get("description", "") if field.get("description") is not None else ""))
        )
        annotations = field.get("annotations", {})
        if isinstance(annotations, dict) and annotations:
            parts = [f"{key}={format_scalar(value)}" for key, value in sorted(annotations.items())]
            annotations_cell = escape_md_cell("; ".join(parts))
        else:
            annotations_cell = "n/a"
        lines.append(f"| {name} | {field_type} | {label} | {description} | {annotations_cell} |")
    return lines


def build_full_dataset_page(dataset: dict, generated_at: str) -> str:
    """Build per-dataset full details page with description, metas, and schema."""
    dataset_id = str(dataset.get("dataset_id", "")).strip()
    title = extract_title(dataset)
    dataset_link = render_dataset_link(dataset_id)
    dataset_api_link = render_dataset_api_link(dataset_id)
    default_meta = get_default_meta(dataset)
    description = default_meta.get("description")
    description_text = strip_html(str(description).strip()) if description else "n/a"
    metas = dataset.get("metas", {})
    if not isinstance(metas, dict):
        metas = {}
    fields = dataset.get("fields", [])
    if not isinstance(fields, list):
        fields = []

    key_metadata: list[tuple[str, object]] = [
        ("dataset_identifier", dataset_id),
        ("title", title),
        ("description", description_text),
        ("contact_name", get_nested(metas, ("dcat", "contact_name"))),
        ("issued", get_nested(metas, ("dcat", "issued"))),
        ("modified", get_nested(metas, ("default", "modified"))),
        ("rights", get_nested(metas, ("dcat_ap_ch", "rights"))),
        ("temporal_coverage_start_date", get_nested(metas, ("dcat", "temporal_coverage_start"))),
        ("temporal_coverage_end_date", get_nested(metas, ("dcat", "temporal_coverage_end"))),
        ("themes", get_nested(metas, ("default", "theme"))),
        ("keywords", get_nested(metas, ("default", "keyword"))),
        ("publisher", get_nested(metas, ("default", "publisher"))),
        (
            "reference",
            get_nested(metas, ("dcat", "relation")) or get_nested(metas, ("default", "references")),
        ),
        ("records_count", extract_records_count(dataset)),
        ("public_page", dataset_link),
        ("api_metadata", dataset_api_link),
    ]

    lines = [
        f"# Dataset {dataset_id}: {title}",
        "",
        f"_Generated: {generated_at}_",
        "",
        "## Metadata",
        "",
    ]
    lines.extend(build_key_value_table(key_metadata))
    lines.extend(
        [
            "",
            "## Schema (`fields`)",
            "",
            f"- Field count: **{len(fields)}**",
            "",
        ]
    )

    lines.extend(build_schema_table(fields))
    lines.append("")
    return "\n".join(lines)


def build_full_context_bundle(dataset_pages: list[tuple[str, str]], generated_at: str) -> str:
    """Build one bundled markdown file with all full dataset pages."""
    lines = [
        "# data.bs.ch full dataset context bundle",
        "",
        f"_Generated: {generated_at}_",
        "",
        "This bundled file contains all public datasets with description, full metadata (`metas`), and schema (`fields`).",
        "",
        f"- Included datasets: **{len(dataset_pages)}**",
        "",
    ]
    for dataset_id, page in dataset_pages:
        lines.extend(
            [
                f"## Dataset bundle item: {dataset_id}",
                "",
                page,
                "",
            ]
        )
    return "\n".join(lines)


def build_main_index(datasets: list[dict], generated_at: str) -> str:
    """Build the global dataset index markdown page."""
    lines = [
        "# data.bs.ch dataset index",
        "",
        f"_Generated: {generated_at}_",
        "",
        "This index is generated from the Explore API and grouped by themes in dedicated pages.",
        "",
        f"- Total datasets: **{len(datasets)}**",
        "- Theme index: [by-theme/index.md](./by-theme/index.md)",
        "- Full dataset context: [full/index.md](./full/index.md)",
        "",
        "## Datasets",
        "",
        "| dataset_id | title | records_count | modified | themes | full page | api metadata |",
        "|---|---|---:|---|---|---|---|",
    ]

    for ds in sorted(datasets, key=lambda item: item.get("dataset_id", "")):
        dataset_id = ds.get("dataset_id", "")
        title = escape_md_cell(extract_title(ds))
        records = extract_records_count(ds)
        modified = extract_modified(ds)
        themes = escape_md_cell(", ".join(extract_theme_names(ds)))
        dataset_link = render_dataset_link(dataset_id)
        full_page = f"./full/{render_full_page_filename(str(dataset_id))}"
        api_link = render_dataset_api_link(str(dataset_id))
        lines.append(
            f"| [{dataset_id}]({dataset_link}) | {title} | {records} | {modified} | {themes} | [open]({full_page}) | [api]({api_link}) |"
        )

    lines.append("")
    return "\n".join(lines)


def build_theme_index(theme_map: dict[str, list[dict]], generated_at: str) -> str:
    """Build the by-theme index markdown page."""
    lines = [
        "# data.bs.ch datasets by theme",
        "",
        f"_Generated: {generated_at}_",
        "",
        "## Theme pages",
        "",
        "| theme | datasets | page |",
        "|---|---:|---|",
    ]

    for theme in sorted(theme_map.keys(), key=lambda x: x.lower()):
        datasets = theme_map[theme]
        slug = slugify(theme)
        page = f"./{slug}.md"
        lines.append(f"| {escape_md_cell(theme)} | {len(datasets)} | [open]({page}) |")

    lines.append("")
    return "\n".join(lines)


def build_theme_page(theme: str, datasets: list[dict], generated_at: str) -> str:
    """Build a single theme markdown page."""
    lines = [
        f"# Theme: {theme}",
        "",
        f"_Generated: {generated_at}_",
        "",
        f"- Dataset count: **{len(datasets)}**",
        "- Back to: [theme index](./index.md)",
        "",
        "| dataset_id | title | records_count | modified |",
        "|---|---|---:|---|",
    ]

    for ds in sorted(datasets, key=lambda item: item.get("dataset_id", "")):
        dataset_id = ds.get("dataset_id", "")
        title = escape_md_cell(extract_title(ds))
        records = extract_records_count(ds)
        modified = extract_modified(ds)
        dataset_link = render_dataset_link(dataset_id)
        lines.append(f"| [{dataset_id}]({dataset_link}) | {title} | {records} | {modified} |")

    lines.append("")
    return "\n".join(lines)


def generate() -> None:
    """Generate all dataset and theme markdown pages."""
    LOG.info("Starting dataset doc generation")
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    datasets = iter_datasets()
    if not datasets:
        raise RuntimeError("No datasets returned from API; aborting generation.")
    LOG.info("Datasets normalized: %s", len(datasets))

    theme_map: dict[str, list[dict]] = defaultdict(list)
    for ds in datasets:
        for theme in extract_theme_names(ds):
            theme_map[theme].append(ds)
    LOG.info("Themes aggregated: %s", len(theme_map))

    write_text(DATASETS_DIR / "index.md", build_main_index(datasets, generated_at))
    write_text(BY_THEME_DIR / "index.md", build_theme_index(theme_map, generated_at))
    write_text(FULL_DATASETS_DIR / "index.md", build_full_index(datasets, generated_at))
    LOG.info("Main index files written")

    # Remove stale theme files from previous generations.
    if BY_THEME_DIR.exists():
        for old_file in BY_THEME_DIR.glob("*.md"):
            if old_file.name != "index.md":
                old_file.unlink()

    if FULL_DATASETS_DIR.exists():
        for old_file in FULL_DATASETS_DIR.glob("*.md"):
            if old_file.name != "index.md":
                old_file.unlink()

    for theme, themed_datasets in theme_map.items():
        slug = slugify(theme)
        write_text(BY_THEME_DIR / f"{slug}.md", build_theme_page(theme, themed_datasets, generated_at))

    bundle_pages: list[tuple[str, str]] = []
    for ds in sorted(datasets, key=lambda item: item.get("dataset_id", "")):
        dataset_id = str(ds.get("dataset_id", "")).strip()
        if not dataset_id:
            continue
        page_content = build_full_dataset_page(ds, generated_at)
        write_text(FULL_DATASETS_DIR / render_full_page_filename(dataset_id), page_content)
        bundle_pages.append((dataset_id, page_content))
    write_text(FULL_DATASETS_DIR / "all.md", build_full_context_bundle(bundle_pages, generated_at))
    LOG.info("Theme pages written: %s", len(theme_map))
    LOG.info("Generation completed successfully: datasets=%s themes=%s", len(datasets), len(theme_map))
    print(f"Generated dataset docs for {len(datasets)} datasets across {len(theme_map)} themes.")


if __name__ == "__main__":
    try:
        configure_logging()
        generate()
    except Exception:  # pragma: no cover
        LOG.exception("Dataset doc generation failed")
        sys.exit(1)
