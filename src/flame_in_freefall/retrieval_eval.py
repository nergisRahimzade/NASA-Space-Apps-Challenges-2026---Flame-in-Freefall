"""Day 10 (AI): score search automatically, so different chunk settings can be compared fairly.

Day 9 judged every result by hand, but chunk ids change whenever the chunk size changes, so
those judgments don't carry over. Instead, each answerable question gets a short list of
"evidence" phrases taken from the reports: a returned chunk counts as relevant if it contains
at least one of them. The phrases were picked so they reproduce the Day 9 hand judgments in
tests/retrieval.md (tests/test_retrieval_eval.py checks that), then reused for every setting.
Day 11 (AI): the same scoring compares k = 3, 5 and 8, and also counts wrong-experiment chunks."""

from math import comb

# The 10 Day 9 questions, in order. The last 2 aren't covered by the reports.
QUESTIONS = [
    "What gases were tested as fire suppressants in microgravity?",
    "What is the Limiting Oxygen Index and how did FLEX measure it?",
    "What is a cool flame?",
    "What oxygen levels and pressures were used in the FLEX-2 chamber?",
    "How were fuel droplets deployed and ignited in FLEX-2?",
    "How fast does a large fire grow in low gravity?",
    "What airflow speeds were used in Saffire-II?",
    "Why are normal-gravity fire tests risky for designing spacecraft safety systems?",
    "Which spacecraft materials are the most dangerous at 30 percent oxygen?",
    "How do you put out a lithium battery fire on Mars?",
]

# Question number -> phrases that answer it, copied word for word from docs/reports/.
# Questions 9 and 10 have none: nothing in the reports answers them.
EVIDENCE: dict[int, list[str]] = {
    1: ["CO2, He, and SF6"],
    2: ["Limiting Oxygen Index", "for the LOI tests", "to determine the LOI"],
    3: ["cool flames"],  # mentioned, never defined (a weak match on Day 9 too)
    4: ["0.5 atm to 3.0 atm", "0.1 to 0.4 mole fraction"],  # FLEX-2's values, not FLEX's
    5: ["Deploy the droplet(s)", "power to the ignitor", "dispensing needles were retracted"],
    6: ["how rapidly a large scale fire grows"],
    7: ["20 or 30 cm/s"],
    8: ["fire standards to design spacecraft fire safety systems"],
    9: [],
    10: [],
}
ANSWERABLE = [n for n, phrases in EVIDENCE.items() if phrases]

# Day 11: questions that name one experiment, spelled like the chunks' `experiment` tag.
# A chunk from another experiment can't answer them and may carry the wrong numbers into the
# summary (Day 9's Q4 got FLEX's pressure range). A bigger k returns more of these.
NAMED_EXPERIMENT: dict[int, str] = {2: "FLEX", 4: "FLEX-2", 5: "FLEX-2", 7: "Saffire-II"}


def _squash(text: str) -> str:
    # Chunks join words with single spaces, so compare with all whitespace squashed the same way.
    return " ".join(text.split())


def is_relevant(question_num: int, text: str) -> bool:
    """True if the passage contains any evidence phrase for that question."""
    if question_num not in EVIDENCE:
        raise ValueError(f"no question number {question_num}")
    passage = _squash(text)
    return any(_squash(p) in passage for p in EVIDENCE[question_num])


def chance_of_a_hit(n_chunks: int, n_relevant: int, k: int = 3) -> float:
    """Chance that k chunks picked at random include at least one relevant one.
    With big chunks the index is tiny, so even random picks often 'hit'; this shows how often."""
    if n_relevant == 0:
        return 0.0
    k = min(k, n_chunks)
    return 1 - comb(n_chunks - n_relevant, k) / comb(n_chunks, k)


def score_results(results: dict[int, list[str]], chunks: list[dict], k: int = 3) -> dict:
    """Score one setting. `results` maps question number -> returned chunk ids, best first.

    Returns counts over the answerable questions: first result relevant, any of the top k
    relevant, relevant results out of all returned, and what random picking would score.
    `wrong_experiment` counts returned chunks from another experiment than the one a question
    names (NAMED_EXPERIMENT), out of `named_returned`. Chunks with no `experiment` tag are
    skipped."""
    if k <= 0:
        raise ValueError("k must be > 0")
    by_id = {c["id"]: c for c in chunks}
    first = top_k = relevant = returned = wrong = named_returned = 0
    chance = 0.0
    for n in ANSWERABLE:
        picked = [by_id[i] for i in results[n][:k]]
        hits = [is_relevant(n, c["text"]) for c in picked]
        first += bool(hits and hits[0])
        top_k += any(hits)
        relevant += sum(hits)
        returned += len(hits)
        if n in NAMED_EXPERIMENT:
            tagged = [c["experiment"] for c in picked if "experiment" in c]
            named_returned += len(tagged)
            wrong += sum(e != NAMED_EXPERIMENT[n] for e in tagged)
        n_relevant = sum(is_relevant(n, c["text"]) for c in chunks)
        chance += chance_of_a_hit(len(chunks), n_relevant, k)
    return {
        "answerable": len(ANSWERABLE),
        "first": first,
        "top_k": top_k,
        "relevant": relevant,
        "returned": returned,
        "chance_top_k": chance,  # expected top-k hits from random picks
        "wrong_experiment": wrong,
        "named_returned": named_returned,
    }
