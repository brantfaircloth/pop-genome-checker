"""CLI entry point."""

import os
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from . import entrez
from .assembly import search as search_assemblies
from .report import build, write
from .sra import DEFAULT_MIN_INDIVIDUALS, search as search_sra
from .taxonomy import fetch_lineage

console = Console()


def _make_progress(*columns) -> Progress:
    return Progress(*columns, console=console, transient=True)


@click.command()
@click.argument("taxon", required=False)
@click.option("--taxon-file", "-f", type=click.Path(exists=True), help="File with one taxon per line.")
@click.option("--output", "-o", default="results.csv", show_default=True, help="Output CSV path.")
@click.option("--email", default=None, help="Email for NCBI Entrez (required). Falls back to NCBI_EMAIL env var.")
@click.option("--api-key", default=None, help="NCBI API key for higher rate limits. Falls back to NCBI_API_KEY env var.")
@click.option("--min-n50", default=30, show_default=True, type=float, help="Minimum contig N50 in Mbp for a species to be included.")
@click.option("--min-individuals", default=DEFAULT_MIN_INDIVIDUALS, show_default=True, type=int, help="Minimum number of individuals required in an SRA project.")
def main(taxon, taxon_file, output, email, api_key, min_n50, min_individuals):
    min_n50_bp = int(min_n50 * 1_000_000)
    """Find high-quality NCBI genome assemblies and check for SRA population data.

    TAXON can be a species binomial (e.g. "Arabidopsis thaliana") or a higher
    taxon name (e.g. "Aves", "Mammalia", "Arthropoda").
    """
    console.print(Panel.fit("[bold cyan]pop-genome-checker[/bold cyan]", padding=(0, 2)))

    email = email or os.environ.get("NCBI_EMAIL")
    if not email:
        console.print("[red]Error:[/red] provide --email or set NCBI_EMAIL.")
        sys.exit(1)

    api_key = api_key or os.environ.get("NCBI_API_KEY")
    entrez.configure(email, api_key)

    taxa = []
    if taxon:
        taxa.append(taxon)
    if taxon_file:
        with open(taxon_file) as fh:
            taxa.extend(line.strip() for line in fh if line.strip())
    if not taxa:
        console.print("[red]Error:[/red] provide a TAXON argument or --taxon-file.")
        sys.exit(1)

    all_assemblies = []
    for name in taxa:
        # --- Resolve taxon ---
        with _make_progress(SpinnerColumn(), TextColumn("{task.description}")) as p:
            p.add_task(f"Resolving [italic]{name}[/italic]…")
            try:
                taxid = entrez.resolve_taxon(name)
            except ValueError as e:
                console.print(f"  [yellow]Warning:[/yellow] {e}")
                continue
        console.print(f"  [green]✓[/green] [italic]{name}[/italic] → taxid [bold]{taxid}[/bold]")

        # --- Fetch assemblies ---
        with _make_progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
        ) as p:
            task = p.add_task("Fetching assemblies…", total=None)

            def on_assembly_batch(done, total, _task=task, _p=p):
                _p.update(_task, completed=done, total=total)

            assemblies = search_assemblies(taxid, min_n50=min_n50_bp, on_batch=on_assembly_batch)

        console.print(
            f"  [green]✓[/green] Found [bold]{len(assemblies)}[/bold] best-per-species assemblies"
        )
        all_assemblies.extend(assemblies)

    if not all_assemblies:
        console.print("\n[yellow]No assemblies found.[/yellow]")
        sys.exit(0)

    # --- Fetch taxonomic lineage ---
    unique_taxids = {a.species_taxid for a in all_assemblies}
    with _make_progress(SpinnerColumn(), TextColumn("{task.description}")) as p:
        p.add_task(f"Fetching lineage for {len(unique_taxids)} species…")
        lineage_by_taxid = fetch_lineage(list(unique_taxids))
    console.print(f"  [green]✓[/green] Lineage fetched for [bold]{len(lineage_by_taxid)}[/bold] species")

    # --- Query SRA ---
    console.print()
    sra_by_taxid: dict = {}

    for taxid in unique_taxids:
        organism = next(a.organism for a in all_assemblies if a.species_taxid == taxid)
        with _make_progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
        ) as p:
            task = p.add_task(f"Querying SRA: [italic]{organism}[/italic]…", total=None)

            def on_sra_batch(done, total, _task=task, _p=p):
                _p.update(_task, completed=done, total=total)

            sra_by_taxid[taxid] = search_sra(taxid, min_individuals=min_individuals, on_batch=on_sra_batch)

        n = len(sra_by_taxid[taxid])
        if n:
            console.print(
                f"  [green]✓[/green] [italic]{organism}[/italic]: "
                f"[bold]{n}[/bold] project(s) with >{min_individuals} individuals"
            )
        else:
            console.print(f"  [dim]–[/dim] [italic]{organism}[/italic]: no qualifying SRA projects")

    # --- Build report & summary table ---
    df = build(all_assemblies, sra_by_taxid, lineage_by_taxid)
    write(df, output)

    console.print()
    _print_summary(df)
    console.print(f"\nReport written to [bold]{output}[/bold] ([bold]{len(df)}[/bold] rows)")


def _print_summary(df) -> None:
    table = Table(title="Results summary", show_lines=False, header_style="bold cyan")
    table.add_column("Organism")
    table.add_column("Order")
    table.add_column("Family")
    table.add_column("Best assembly", no_wrap=True)
    table.add_column("Level")
    table.add_column("Contig N50", justify="right")
    table.add_column("SRA projects", justify="right")
    table.add_column("Max individuals", justify="right")

    for organism, grp in df.groupby("organism"):
        best_row = grp.iloc[0]
        n50 = best_row["contig_n50"]
        n50_str = f"{int(n50):,}" if n50 and n50 > 0 else "—"
        projects = grp[grp["sra_project"] != ""]["sra_project"].nunique()
        max_ind = grp["sra_individuals"].max()
        max_ind_str = str(int(max_ind)) if max_ind > 0 else "—"
        table.add_row(
            str(organism),
            str(best_row.get("order", "")),
            str(best_row.get("family", "")),
            str(best_row["accession"]),
            str(best_row["assembly_level"]),
            n50_str,
            str(projects) if projects else "—",
            max_ind_str,
        )

    console.print(table)
