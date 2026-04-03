# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

`pop-genome-checker` is a CLI tool that queries NCBI to find high-quality genome assemblies for a given organism or taxon, then checks the NCBI SRA database for population-level sequencing data linked to those organisms. Output is a CSV report.

## Commands

```bash
# Install all dependencies (including dev group)
uv sync

# Run the tool
uv run pop-genome-checker --help
uv run pop-genome-checker "Arabidopsis thaliana"
uv run pop-genome-checker "Aves" --output results.csv --min-n50 30
uv run pop-genome-checker --taxon-file organisms.txt

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_assembly.py::test_filter_by_n50

# Lint / format
uv run ruff check .
uv run ruff format .

# Add a dependency
uv add <package>
uv add --dev <package>
```

## Architecture

### Data flow

1. **Taxon resolution** (`entrez.py`) — resolves a species name or higher taxon (e.g., "Aves") to an NCBI Taxonomy ID using the `taxonomy` database.
2. **Assembly search** (`assembly.py`) — queries the NCBI `assembly` database for that taxon ID and all descendants, selects the best assembly per species by contig N50, and filters by `--min-n50` (Mbp, default 30).
3. **SRA search** (`sra.py`) — for each qualifying assembly's organism taxon ID, queries the NCBI `sra` database for linked experiments (strategy: WGS, AMPLICON, etc.).
4. **Report** (`report.py`) — merges assembly and SRA results into a flat CSV.

### Key modules

- `cli.py` — Click entry point; handles input (species name, taxon file, or higher taxon), output path, and NCBI API key.
- `entrez.py` — thin wrapper around `Bio.Entrez` with rate limiting (3 req/s without API key, 10 req/s with) and retry logic.
- `assembly.py` — assembly database queries and quality filtering logic.
- `sra.py` — SRA database queries; filters for relevant experiment types.
- `report.py` — builds and writes the CSV using `pandas`.

### NCBI API notes

- Set `Bio.Entrez.email` and optionally `Bio.Entrez.api_key` (via `--api-key` flag or `NCBI_API_KEY` env var).
- All Entrez calls go through `entrez.py` helpers to enforce rate limits.
- Use `esearch` → `efetch` or `esummary` patterns; avoid fetching large result sets without batching (`retmax`, `usehistory=y`).

### Other

- Always update the README after making changes