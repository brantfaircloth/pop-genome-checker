"""Fetch taxonomic lineage (order, family) for a set of taxids."""

from Bio import Entrez

from . import entrez

RANKS = {"order", "family"}


def fetch_lineage(taxids: list[str]) -> dict[str, dict[str, str]]:
    """Return {taxid: {"order": ..., "family": ...}} for each taxid in the list.

    Missing ranks are returned as empty strings. All taxids are fetched in a
    single batched call to the NCBI taxonomy database.
    """
    if not taxids:
        return {}

    entrez._rate_limit()
    handle = Entrez.efetch(db="taxonomy", id=",".join(taxids), rettype="xml", retmode="xml")
    records = Entrez.read(handle)

    result: dict[str, dict[str, str]] = {}
    for record in records:
        taxid = str(record["TaxId"])
        lineage: dict[str, str] = {rank: "" for rank in RANKS}
        for node in record.get("LineageEx", []):
            rank = str(node.get("Rank", "")).lower()
            if rank in RANKS:
                lineage[rank] = str(node["ScientificName"])
        result[taxid] = lineage

    return result
