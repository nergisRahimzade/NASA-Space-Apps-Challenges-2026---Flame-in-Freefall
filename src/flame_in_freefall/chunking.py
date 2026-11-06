"""Day 2 (AI): cut long text into overlapping pieces, keeping where each piece came from.

Search compares a question with small pieces ("chunks") instead of whole documents,
so the best-matching passage can be shown with its source and page."""

import csv
from pathlib import Path

# Word counts, not characters. all-MiniLM-L6-v2 reads at most 256 tokens (word pieces);
# 150 words is about 190 tokens, so a chunk isn't cut off when it's embedded (200 was ~250).
DEFAULT_SIZE = 150
DEFAULT_OVERLAP = 30


def chunk_text(text: str, size: int = DEFAULT_SIZE, overlap: int = DEFAULT_OVERLAP) -> list[str]:
    """Split text into chunks of `size` words; each chunk repeats the last
    `overlap` words of the previous one so ideas aren't cut in half."""
    # Fail loudly on settings that would loop forever or make no sense.
    if size <= 0:
        raise ValueError("size must be > 0")
    if not 0 <= overlap < size:
        raise ValueError("overlap must be >= 0 and smaller than size")
    words = text.split()  # also squeezes newlines and repeated spaces
    if not words:
        return []  # blank page = no chunks, not one empty chunk
    step = size - overlap  # how far each new chunk moves forward
    chunks = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start : start + size]))
        # This chunk reached the end, so stop; another one would only repeat its tail.
        if start + size >= len(words):
            break
    return chunks


def chunk_document(
    pages: list[str],
    source: str,
    doc_id: str,
    size: int = DEFAULT_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[dict]:
    """pages[0] is page 1. Returns chunk dicts with the fields in docs/contract.md, section 2."""
    # Every chunk id and citation is built from these, so empty ones would break tracing.
    if not source.strip() or not doc_id.strip():
        raise ValueError("source and doc_id must not be empty")
    out = []
    # Chunk page by page, so every chunk knows its page number (chunks never span two pages).
    for page_num, page_text in enumerate(pages, start=1):
        for i, piece in enumerate(chunk_text(page_text, size, overlap)):
            out.append(
                {
                    # doc-page-chunk number, e.g. "bass-001-p3-c0": unique and readable.
                    "id": f"{doc_id}-p{page_num}-c{i}",
                    "text": piece,
                    "source": source,
                    "page": page_num,
                }
            )
    return out


def chunk_reports(
    sources_csv: Path,
    reports_dir: Path,
    size: int = DEFAULT_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[dict]:
    """Chunk every report listed in sources.csv. Each report is plain text with no pages,
    so the whole text goes in as page 1. The source is the title, as contract section 2 asks.
    Day 12 (DAT): every chunk also gets its report's `experiment` from sources.csv
    (FLEX-2, Saffire-II or FLEX, spelled as in master.csv), so search can filter by it.
    Day 10 (AI): size and overlap can be changed to compare settings (day10 script)."""
    with open(sources_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for row in rows:
        text = (reports_dir / row["file_name"]).read_text(encoding="utf-8")
        # A blank report would silently vanish from search, so fail loudly instead.
        if not text.strip():
            raise ValueError(f"report is empty: {row['file_name']}")
        # An untagged report would never show up when search is filtered, so fail loudly too.
        experiment = (row.get("experiment") or "").strip()
        if not experiment:
            raise ValueError(f"no experiment listed for {row['file_name']} in sources.csv")
        # flex2_abstract.txt -> flex2, so ids read like flex2-p1-c3
        doc_id = Path(row["file_name"]).stem.removesuffix("_abstract")
        for chunk in chunk_document([text], row["title"], doc_id, size, overlap):
            out.append({**chunk, "experiment": experiment})
    return out
