"""Build and write the CSV report."""

import pandas as pd

from .assembly import Assembly
from .sra import SRAProject


def build(assemblies: list[Assembly], sra_by_taxid: dict[str, list[SRAProject]]) -> pd.DataFrame:
    rows = []
    for a in assemblies:
        projects = sra_by_taxid.get(a.species_taxid, [])
        if projects:
            for proj in projects:
                rows.append(_row(a, proj))
        else:
            rows.append(_row(a, None))
    return pd.DataFrame(rows)


def _row(a: Assembly, proj: SRAProject | None) -> dict:
    return {
        "accession": a.accession,
        "assembly_name": a.assembly_name,
        "organism": a.organism,
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
