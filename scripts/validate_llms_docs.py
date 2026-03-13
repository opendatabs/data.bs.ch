#!/usr/bin/env python3
"""Validate llms.txt and linked markdown artifacts."""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
LLMS_ROOT = ROOT / "llms.txt"
LLMS_CTX = ROOT / "llms-ctx.txt"
LLMS_CTX_FULL = ROOT / "llms-ctx-full.txt"
DOCS_DIR = ROOT / "llms"

REQUIRED_FILES = [
    ROOT / "llms.txt",
    DOCS_DIR / "getting-started.md",
    DOCS_DIR / "odsql-cheatsheet.md",
    DOCS_DIR / "query-cookbook.md",
    DOCS_DIR / "datasets" / "index.md",
    DOCS_DIR / "datasets" / "by-theme" / "index.md",
    DOCS_DIR / "datasets" / "full" / "index.md",
    DOCS_DIR / "datasets" / "full" / "all.md",
    LLMS_CTX,
    LLMS_CTX_FULL,
]

REQUIRED_SECTIONS = [
    "# data.bs.ch",
    "## Getting Started",
    "## Query Language (ODSQL)",
    "## Examples",
    "## Dataset Catalog",
    "## Optional",
]

MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

REQUIRED_ROOT_LINKS = [
    "https://raw.githubusercontent.com/opendatabs/data.bs.ch_llms.txt/refs/heads/main/llms/getting-started.md",
    "https://raw.githubusercontent.com/opendatabs/data.bs.ch_llms.txt/refs/heads/main/llms/odsql-cheatsheet.md",
    "https://raw.githubusercontent.com/opendatabs/data.bs.ch_llms.txt/refs/heads/main/llms/query-cookbook.md",
    "https://raw.githubusercontent.com/opendatabs/data.bs.ch_llms.txt/refs/heads/main/llms/datasets/index.md",
    "https://raw.githubusercontent.com/opendatabs/data.bs.ch_llms.txt/refs/heads/main/llms/datasets/full/all.md",
    "https://raw.githubusercontent.com/opendatabs/data.bs.ch_llms.txt/refs/heads/main/llms/datasets/full/index.md",
]

OPTIONAL_SECTION_HEADER = "## Optional"
LOG = logging.getLogger("validate_llms_docs")
FULL_DATASET_CONTEXT_SIGNATURE = "# data.bs.ch full dataset context bundle"


def configure_logging() -> None:
    """Configure script logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def find_missing_files() -> list[str]:
    """Return required files that do not exist."""
    missing = []
    for path in REQUIRED_FILES:
        if not path.exists():
            missing.append(str(path.relative_to(ROOT)))
    return missing


def find_missing_sections() -> list[str]:
    """Return required root sections missing from llms.txt."""
    text = LLMS_ROOT.read_text(encoding="utf-8")
    missing = [section for section in REQUIRED_SECTIONS if section not in text]
    return missing


def collect_markdown_files() -> list[Path]:
    """Collect markdown files that should be validated."""
    files = [LLMS_ROOT]
    files.extend(sorted(DOCS_DIR.rglob("*.md")))
    return files


def validate_local_links(path: Path) -> list[str]:
    """Validate local markdown links in one file.

    Args:
        path: Markdown file path to validate.

    Returns:
        A list of link validation errors for that file.
    """
    text = path.read_text(encoding="utf-8")
    errors = []
    for match in MARKDOWN_LINK.finditer(text):
        target = match.group(1).strip()
        if target.startswith("http://") or target.startswith("https://") or target.startswith("mailto:"):
            continue
        if target.startswith("#"):
            continue
        clean_target = target.split("#", 1)[0]
        local_path = (path.parent / clean_target).resolve()
        if not local_path.exists():
            errors.append(f"{path.relative_to(ROOT)} -> missing local link target: {target}")
    return errors


def extract_markdown_links(text: str) -> list[str]:
    """Extract markdown link targets from text."""
    return [match.group(1).strip() for match in MARKDOWN_LINK.finditer(text)]


def is_public_absolute_https(url: str) -> bool:
    """Return whether a URL is public and absolute HTTPS."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return False
    host = parsed.netloc.lower()
    if host in {"localhost", "127.0.0.1"} or host.endswith(".local"):
        return False
    return True


def validate_root_llms_links() -> tuple[list[str], list[str]]:
    """Validate root llms.txt links.

    Returns:
        Tuple of (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    text = LLMS_ROOT.read_text(encoding="utf-8")
    links = extract_markdown_links(text)
    link_set = set(links)

    for required in REQUIRED_ROOT_LINKS:
        if required not in link_set:
            errors.append(f"llms.txt -> missing required root link: {required}")
        elif not is_public_absolute_https(required):
            errors.append(f"llms.txt -> required link must be public https: {required}")

    optional_idx = text.find(OPTIONAL_SECTION_HEADER)
    if optional_idx >= 0:
        optional_text = text[optional_idx:]
        optional_links = extract_markdown_links(optional_text)
        for url in optional_links:
            if not is_public_absolute_https(url):
                warnings.append(f"llms.txt -> optional link is not public https: {url}")

    return errors, warnings


def validate_ctx_artifacts() -> tuple[list[str], list[str]]:
    """Validate llms-ctx generated artifacts."""
    errors: list[str] = []
    warnings: list[str] = []

    if not LLMS_CTX.exists() or not LLMS_CTX_FULL.exists():
        return errors, warnings

    ctx = LLMS_CTX.read_text(encoding="utf-8")
    ctx_full = LLMS_CTX_FULL.read_text(encoding="utf-8")

    if not ctx.strip():
        errors.append("llms-ctx.txt is empty")
    if not ctx_full.strip():
        errors.append("llms-ctx-full.txt is empty")

    if len(ctx_full) < len(ctx):
        warnings.append("llms-ctx-full.txt is smaller than llms-ctx.txt; Optional expansion may be missing")

    if FULL_DATASET_CONTEXT_SIGNATURE in ctx:
        warnings.append("llms-ctx.txt includes full dataset Optional content signature")
    if FULL_DATASET_CONTEXT_SIGNATURE not in ctx_full:
        errors.append("llms-ctx-full.txt is missing full dataset Optional content signature")

    return errors, warnings


def print_messages(messages: list[str]) -> None:
    """Print messages to stderr, one per line."""
    if messages:
        print("\n".join(messages), file=sys.stderr)


def log_messages(messages: list[str], *, level: int) -> None:
    """Log validation messages individually at a given log level."""
    for message in messages:
        LOG.log(level, message)


def main() -> int:
    """Run all validation checks and return an exit code."""
    LOG.info("Starting llms docs validation")
    errors: list[str] = []
    warnings: list[str] = []

    LOG.info("Checking required files")
    missing_files = find_missing_files()
    if missing_files:
        errors.append("Missing required files:")
        errors.extend(f"  - {name}" for name in missing_files)

    if LLMS_ROOT.exists():
        LOG.info("Checking required llms.txt sections and root links")
        missing_sections = find_missing_sections()
        if missing_sections:
            errors.append("Missing required sections in llms.txt:")
            errors.extend(f"  - {section}" for section in missing_sections)
        root_link_errors, root_link_warnings = validate_root_llms_links()
        errors.extend(root_link_errors)
        warnings.extend(root_link_warnings)
    else:
        LOG.error("Root file missing: %s", LLMS_ROOT)

    LOG.info("Checking generated llms ctx artifacts")
    ctx_errors, ctx_warnings = validate_ctx_artifacts()
    errors.extend(ctx_errors)
    warnings.extend(ctx_warnings)

    LOG.info("Checking local markdown links")
    for file_path in collect_markdown_files():
        errors.extend(validate_local_links(file_path))

    if errors:
        LOG.error("Validation failed with %s error(s)", len(errors))
        log_messages(errors, level=logging.ERROR)
        print_messages(errors)
        return 1

    if warnings:
        LOG.warning("Validation completed with %s warning(s)", len(warnings))
        log_messages(warnings, level=logging.WARNING)
    else:
        LOG.info("Validation completed with no warnings")

    print_messages(warnings)

    LOG.info("llms docs validation passed")
    print("llms docs validation passed.")
    return 0


if __name__ == "__main__":
    configure_logging()
    raise SystemExit(main())
