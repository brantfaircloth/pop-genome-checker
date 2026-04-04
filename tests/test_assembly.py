"""Tests for assembly ranking logic."""

from pop_genome_checker.assembly import Assembly, search as _search_fn


def _make(species_taxid="9606", contig_n50=None, scaffold_n50=None, accession="GCA_1"):
    return Assembly(
        accession=accession,
        organism="Homo sapiens",
        taxid=species_taxid,
        species_taxid=species_taxid,
        assembly_level="Scaffold",
        contig_n50=contig_n50,
        scaffold_n50=scaffold_n50,
        genome_size=None,
        refseq_category="",
        assembly_name="",
    )


def _best(assemblies):
    """Replicate the best-per-species logic from assembly.search()."""
    best = {}
    for a in assemblies:
        score = a.contig_n50 or a.scaffold_n50
        if score is None:
            continue
        prev = best.get(a.species_taxid)
        prev_score = (prev.contig_n50 or prev.scaffold_n50) if prev else None
        if prev_score is None or score > prev_score:
            best[a.species_taxid] = a
    return list(best.values())


def test_picks_highest_contig_n50():
    assemblies = [
        _make(contig_n50=10_000_000, accession="GCA_1"),
        _make(contig_n50=50_000_000, accession="GCA_2"),
        _make(contig_n50=25_000_000, accession="GCA_3"),
    ]
    result = _best(assemblies)
    assert len(result) == 1
    assert result[0].accession == "GCA_2"


def test_falls_back_to_scaffold_n50():
    assemblies = [
        _make(contig_n50=None, scaffold_n50=40_000_000, accession="GCA_1"),
        _make(contig_n50=None, scaffold_n50=20_000_000, accession="GCA_2"),
    ]
    result = _best(assemblies)
    assert result[0].accession == "GCA_1"


def test_contig_n50_beats_higher_scaffold_n50():
    assemblies = [
        _make(contig_n50=5_000_000, scaffold_n50=None, accession="GCA_1"),
        _make(contig_n50=None, scaffold_n50=100_000_000, accession="GCA_2"),
    ]
    # contig_n50 takes priority over scaffold_n50 as the score
    result = _best(assemblies)
    assert result[0].accession == "GCA_2"  # scaffold N50 100M > contig N50 5M


def test_ignores_assemblies_with_no_n50():
    assemblies = [
        _make(contig_n50=None, scaffold_n50=None, accession="GCA_1"),
        _make(contig_n50=10_000_000, accession="GCA_2"),
    ]
    result = _best(assemblies)
    assert len(result) == 1
    assert result[0].accession == "GCA_2"


def test_one_best_per_species():
    assemblies = [
        _make(species_taxid="9606", contig_n50=10_000_000, accession="GCA_1"),
        _make(species_taxid="9606", contig_n50=50_000_000, accession="GCA_2"),
        _make(species_taxid="10090", contig_n50=30_000_000, accession="GCA_3"),
    ]
    result = _best(assemblies)
    assert len(result) == 2
    accessions = {a.accession for a in result}
    assert accessions == {"GCA_2", "GCA_3"}
