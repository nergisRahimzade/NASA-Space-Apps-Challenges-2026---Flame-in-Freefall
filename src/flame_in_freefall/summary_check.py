"""Day 6 (AI): check a summary before anyone trusts it.

Every takeaway must cite the chunk it came from (chunk_id), and that chunk must be one of
the passages the summary was made from. A takeaway that cites nothing, or cites a chunk
we never sent, could be made up, so it's reported as a problem."""


def check_summary(summary: dict, passages: list[dict]) -> list[str]:
    """Problems found in a summarize() result (docs/contract.md); an empty list = passed."""
    # Missing or extra keys mean the shape drifted from the contract; stop, nothing else fits.
    if set(summary) != {"takeaways", "not_found"}:
        return [f"summary keys must be takeaways and not_found, got {sorted(summary)}"]
    takeaways, not_found = summary["takeaways"], summary["not_found"]
    if not isinstance(takeaways, list) or not isinstance(not_found, bool):
        return ["takeaways must be a list and not_found must be true or false"]

    problems = []
    # "Nothing found" and a list of takeaways would contradict each other.
    if not_found and takeaways:
        problems.append("not_found is true but there are takeaways")
    if not not_found and not takeaways:
        problems.append("there are no takeaways but not_found is false")

    sources = {p["id"]: p["source"] for p in passages}  # chunk id -> its source
    for n, t in enumerate(takeaways, start=1):  # n counts from 1, like the app shows them
        chunk_id = t.get("chunk_id")
        if not str(t.get("text") or "").strip():
            problems.append(f"takeaway {n} has no text")
        if not chunk_id:
            problems.append(f"takeaway {n} cites no chunk_id")
        elif chunk_id not in sources:
            problems.append(f"takeaway {n} cites {chunk_id!r}, which is not one of the passages")
        # The source shown next to a takeaway must be the cited chunk's, not another one.
        elif t.get("source") != sources[chunk_id]:
            problems.append(f"takeaway {n} source {t.get('source')!r} is not {chunk_id!r}'s")
    return problems
