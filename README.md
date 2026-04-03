# pop-genome-checker

> **Note:** This project was created as an experiment using [Claude Code](https://claude.ai/code), Anthropic's AI coding assistant. The code was written entirely through a conversational session with Claude.  I've never done this sort of thing before, but I'm actually pretty impressed... this was also using Sonnet 4.6 - so not even the most refined model.

A CLI tool that finds the best genome assembly available for a given organism or taxonomic group in NCBI, then checks the NCBI SRA database for population-level sequencing projects linked to those organisms and limits the returned values by some minimum counts.

## Why you would use this

You want to teach a class using a decent genome and decent population level WGS data and you want to give your students options.  But you also don't want to waste your time trying to figure out what combo of "good genome" and "decent data" will do.

I picked some reasonable defaults - contig N50 of 30 Mbp and count of individuals (in NCBI SRA) > 15.  Both parameters are adjustable.

## What it does

1. Resolves a taxon name (species binomial or higher taxon like "Aves") to an NCBI Taxonomy ID
2. Fetches all genome assemblies for that taxon and selects the best one per species by contig N50
3. Queries NCBI SRA for projects with data from more than a minimum number of individuals for each species (default: 15)
4. Outputs a CSV report

## Installation

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/brantfaircloth/pop-genome-checker.git
cd pop-genome-checker
uv sync
```

## Usage

```bash
uv run pop-genome-checker "Arabidopsis thaliana" --email your@email.com
uv run pop-genome-checker "Aves" --email your@email.com --output birds.csv --min-n50 30
uv run pop-genome-checker --taxon-file organisms.txt --email your@email.com --min-individuals 50
```

Set `NCBI_EMAIL` and optionally `NCBI_API_KEY` as environment variables to avoid passing them on every call. An API key raises the NCBI rate limit from 3 to 10 requests/second, which makes a significant difference for large taxa.

### Options

| Option | Default | Description |
|---|---|---|
| `--output`, `-o` | `results.csv` | Output CSV path |
| `--taxon-file`, `-f` | — | File with one taxon name per line |
| `--min-n50` | `30` | Minimum contig N50 (Mbp) to include a species |
| `--min-individuals` | `15` | Minimum individuals required in an SRA project |
| `--email` | `$NCBI_EMAIL` | Email for NCBI Entrez API |
| `--api-key` | `$NCBI_API_KEY` | NCBI API key for higher rate limits |

## Output

The CSV contains one row per (species, SRA project) combination. Species with no qualifying SRA projects appear as a single row with blank SRA columns.

| Column | Description |
|---|---|
| `accession` | NCBI Assembly accession |
| `assembly_name` | Assembly name |
| `organism` | Species name |
| `order` | Taxonomic order |
| `family` | Taxonomic family |
| `taxid` | NCBI Taxonomy ID (strain/subspecies level) |
| `species_taxid` | NCBI Taxonomy ID (species level) |
| `assembly_level` | Chromosome / Scaffold / Contig / etc. |
| `contig_n50` | Contig N50 of the best assembly (bp) |
| `scaffold_n50` | Scaffold N50 of the best assembly (bp) |
| `refseq_category` | RefSeq category (e.g. reference genome) |
| `sra_project` | SRA project accession (SRP/ERP/DRP) |
| `sra_individuals` | Number of individuals (unique BioSamples) in that project |
| `sra_runs` | Number of sequencing runs in that project |
