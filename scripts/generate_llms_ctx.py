#!/usr/bin/env python3
"""Generate llms-ctx artifacts from root llms.txt."""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
LLMS_TXT = ROOT / "llms.txt"
LLMS_CTX = ROOT / "llms-ctx.txt"
LLMS_CTX_FULL = ROOT / "llms-ctx-full.txt"
PROC_ROOT = ROOT / "_proc"
PROC_LLMS_DIR = PROC_ROOT / "llms"
RAW_GITHUB_PREFIX = "https://raw.githubusercontent.com/opendatabs/data.bs.ch_llms.txt/refs/heads/main/"
LOCAL_DOCS_PREFIX = "https://data.bs.ch/"
LOG = logging.getLogger("generate_llms_ctx")


def configure_logging() -> None:
    """Configure script logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def prepare_local_proc_docs() -> None:
    """Mirror local llms docs under _proc for llms_txt local resolution."""
    if PROC_LLMS_DIR.exists():
        shutil.rmtree(PROC_LLMS_DIR)
    shutil.copytree(ROOT / "llms", PROC_LLMS_DIR)


def build_local_llms_txt() -> str:
    """Build llms.txt content with URLs rewritten to local docs paths."""
    text = LLMS_TXT.read_text(encoding="utf-8")
    return text.replace(RAW_GITHUB_PREFIX, LOCAL_DOCS_PREFIX)


def run_llms_txt2ctx(source_file: Path, *, include_optional: bool) -> str:
    """Run llms_txt2ctx and return rendered context text."""
    cmd = ["llms_txt2ctx", str(source_file)]
    if include_optional:
        cmd.extend(["--optional", "True"])
    LOG.info("Running command: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"llms_txt2ctx failed with exit code {result.returncode}: {stderr}")
    return result.stdout


def write_file(path: Path, content: str) -> None:
    """Write UTF-8 text to a file."""
    path.write_text(content, encoding="utf-8")


def sanitize_ctx_content(content: str) -> str:
    """Reduce ctx size by removing JSON blocks and inline HTML fragments."""
    # Remove fenced JSON code blocks.
    content = re.sub(r"```json\s+.*?\s+```", "", content, flags=re.DOTALL | re.IGNORECASE)
    # Remove common inline HTML fragments that leak from source docs.
    content = re.sub(r"</?p\b[^>]*>", "", content, flags=re.IGNORECASE)
    content = re.sub(r"</?a\b[^>]*>", "", content, flags=re.IGNORECASE)
    # Collapse excessive blank lines after removals.
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content


def generate() -> None:
    """Generate both ctx variants from root llms.txt."""
    if not LLMS_TXT.exists():
        raise RuntimeError(f"Required source file missing: {LLMS_TXT}")

    prepare_local_proc_docs()
    local_llms_txt = ROOT / ".llms.local.txt"
    try:
        write_file(local_llms_txt, build_local_llms_txt())

        LOG.info("Generating llms-ctx.txt (without Optional section)")
        ctx = run_llms_txt2ctx(local_llms_txt, include_optional=False)
        write_file(LLMS_CTX, sanitize_ctx_content(ctx))

        LOG.info("Generating llms-ctx-full.txt (with Optional section)")
        ctx_full = run_llms_txt2ctx(local_llms_txt, include_optional=True)
        write_file(LLMS_CTX_FULL, sanitize_ctx_content(ctx_full))
    finally:
        if local_llms_txt.exists():
            local_llms_txt.unlink()

    LOG.info(
        "Context artifacts generated successfully: %s, %s",
        LLMS_CTX.relative_to(ROOT),
        LLMS_CTX_FULL.relative_to(ROOT),
    )
    print("Generated llms-ctx artifacts.")


if __name__ == "__main__":
    try:
        configure_logging()
        generate()
    except Exception:  # pragma: no cover
        LOG.exception("llms ctx generation failed")
        sys.exit(1)
