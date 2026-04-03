"""Query NCBI SRA and return projects with sufficient population-level coverage."""

import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from . import entrez

DEFAULT_MIN_INDIVIDUALS = 15

# SRA esummary ExpXml contains study and sample accessions in attributes like:
#   <Study acc="SRP123456" .../>
#   <Sample acc="SRS123456" .../>
_STUDY_RE = re.compile(r'<Study acc="((?:SRP|ERP|DRP)\d+)"')
_SAMPLE_RE = re.compile(r'<Sample acc="((?:SRS|ERS|DRS)\d+)"')
_RUN_RE = re.compile(r'acc="([EDS]RR\d+)"')


@dataclass
class SRAProject:
    project_accession: str  # SRP/ERP/DRP accession
    individual_count: int   # unique SRA samples (one per individual)
    run_count: int


def search(
    taxid: str,
    min_individuals: int = DEFAULT_MIN_INDIVIDUALS,
    on_batch: Callable[[int, int], None] | None = None,
) -> list[SRAProject]:
    """Return SRA projects with > min_individuals individuals for this taxon.

    on_batch(completed, total) is called after each batch fetch if provided.
    """
    term = f"txid{taxid}[Organism:exp]"
    count = int(entrez.esearch("sra", term, retmax=0).get("Count", 0))
    if count == 0:
        return []

    ids = entrez.esearch("sra", term, retmax=10000).get("IdList", [])
    if not ids:
        return []

    # project accession -> set of sample accessions / run accessions
    project_samples: dict[str, set[str]] = defaultdict(set)
    project_runs: dict[str, set[str]] = defaultdict(set)

    batch_size = 200
    for i in range(0, len(ids), batch_size):
        batch = ids[i : i + batch_size]
        summaries = entrez.esummary("sra", id=",".join(batch))
        for doc in summaries:
            exp_xml = str(doc.get("ExpXml", ""))
            runs_xml = str(doc.get("Runs", ""))

            study_m = _STUDY_RE.search(exp_xml)
            sample_m = _SAMPLE_RE.search(exp_xml)
            if not study_m or not sample_m:
                continue

            proj = study_m.group(1)
            project_samples[proj].add(sample_m.group(1))
            for m in _RUN_RE.finditer(runs_xml):
                project_runs[proj].add(m.group(1))
        if on_batch:
            on_batch(min(i + batch_size, len(ids)), len(ids))

    return [
        SRAProject(
            project_accession=proj,
            individual_count=len(samples),
            run_count=len(project_runs[proj]),
        )
        for proj, samples in project_samples.items()
        if len(samples) > min_individuals
    ]
