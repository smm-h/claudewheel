"""Fuzzy search functions for matching user input against option lists."""


def fuzzy_score(query: str, candidate: str) -> int:
    """Score: 100 exact, 80 prefix, 60 contains, 40 subsequence, 0 no match."""
    q = query.lower()
    c = candidate.lower()
    if q == c:
        return 100
    if c.startswith(q):
        return 80
    if q in c:
        return 60
    # Subsequence match
    qi = 0
    for ch in c:
        if qi < len(q) and ch == q[qi]:
            qi += 1
    if qi == len(q):
        return 40
    return 0


def fuzzy_rank(query: str, candidates: list[str]) -> list[str]:
    """Return candidates sorted by fuzzy match score (best first). Excludes non-matches."""
    scored = [(fuzzy_score(query, c), c) for c in candidates]
    scored = [(s, c) for s, c in scored if s > 0]
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored]
