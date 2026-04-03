"""Build and write the CSV report."""

import pandas as pd

from .assembly import Assembly
from .sra import SRAProject


def build(
    assemblies: list[Assembly],
    sra_by_taxid: dict[str, list[SRAProject]],
    lineage_by_taxid: dict[str, dict[str, str]],
) -> pd.DataFrame:
    rows = []
    for a in assemblies:
        lineage = lineage_by_taxid.get(a.species_taxid, {})
        projects = sra_by_taxid.get(a.species_taxid, [])
        if projects:
            for proj in projects:
                rows.append(_row(a, proj, lineage))
        else:
            rows.append(_row(a, None, lineage))

    df = pd.DataFrame(rows)
    # Sort by genome quality first (contig N50 desc, falling back to scaffold N50),
    # then by SRA individual count so assembly quality always takes priority.
    df["_n50"] = df["contig_n50"].fillna(df["scaffold_n50"]).fillna(0)
    df = df.sort_values(["_n50", "sra_individuals"], ascending=[False, False]).drop(columns="_n50")
    return df.reset_index(drop=True)


def _row(a: Assembly, proj: SRAProject | None, lineage: dict[str, str]) -> dict:
    return {
        "accession": a.accession,
        "assembly_name": a.assembly_name,
        "organism": a.organism,
        "order": lineage.get("order", ""),
        "family": lineage.get("family", ""),
        "taxid": a.taxid,
        "species_taxid": a.species_taxid,
        "assembly_level": a.assembly_level,
        "contig_n50": a.contig_n50,
        "scaffold_n50": a.scaffold_n50,
        "refseq_category": a.refseq_category,
        "sra_project": proj.project_accession if proj else "",
        "sra_individuals": proj.individual_count if proj else 0,
        "sra_runs": proj.run_count if proj else 0,
    }


def write(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)
