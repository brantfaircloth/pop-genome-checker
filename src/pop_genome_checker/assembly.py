"""Query NCBI Assembly database and return the best assembly per species."""

from collections.abc import Callable
from dataclasses import dataclass

from . import entrez


@dataclass
class Assembly:
    accession: str
    organism: str
    taxid: str          # strain/subspecies-level taxid from the assembly record
    species_taxid: str  # species-level taxid — use this for SRA lookups
    assembly_level: str
    contig_n50: int | None
    scaffold_n50: int | None
    genome_size: int | None
    refseq_category: str
    assembly_name: str


def search(
    taxid: str,
    min_n50: int = 0,
    on_batch: Callable[[int, int], None] | None = None,
) -> list[Assembly]:
    """Return the best assembly (highest contig N50) per species for taxid and descendants.

    Assemblies whose best contig/scaffold N50 is below min_n50 are excluded.
    on_batch(completed, total) is called after each batch fetch if provided.
    """
    term = f"txid{taxid}[Organism:exp]"
    result = entrez.esearch("assembly", term, retmax=10000)
    ids = result.get("IdList", [])
    if not ids:
        return []

    all_assemblies: list[Assembly] = []
    batch_size = 200
    for i in range(0, len(ids), batch_size):
        batch = ids[i : i + batch_size]
        summaries = entrez.esummary("assembly", id=",".join(batch))
        for doc in summaries["DocumentSummarySet"]["DocumentSummary"]:
            all_assemblies.append(_parse_summary(doc))
        if on_batch:
            on_batch(min(i + batch_size, len(ids)), len(ids))

    # Keep the best assembly per species by contig N50 (fall back to scaffold N50)
    best: dict[str, Assembly] = {}
    for a in all_assemblies:
        score = a.contig_n50 or a.scaffold_n50
        if score is None:
            continue
        prev = best.get(a.species_taxid)
        prev_score = (prev.contig_n50 or prev.scaffold_n50) if prev else None
        if prev_score is None or score > prev_score:
            best[a.species_taxid] = a

    return [a for a in best.values() if (a.contig_n50 or a.scaffold_n50 or 0) >= min_n50]


def _parse_summary(doc) -> Assembly:
    taxid = str(doc.get("Taxid", ""))
    species_taxid = str(doc.get("SpeciesTaxid", "")) or taxid

    return Assembly(
        accession=str(doc.get("AssemblyAccession", "")),
        organism=str(doc.get("SpeciesName", "")),
        taxid=taxid,
        species_taxid=species_taxid,
        assembly_level=str(doc.get("AssemblyStatus", "")),
        contig_n50=_int(doc.get("ContigN50")),
        scaffold_n50=_int(doc.get("ScaffoldN50")),
        genome_size=_int(doc.get("TotalLength")),
        refseq_category=str(doc.get("RefSeq_category", "")),
        assembly_name=str(doc.get("AssemblyName", "")),
    )


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
