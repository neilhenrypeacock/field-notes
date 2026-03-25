"""
Shared utilities for Field Notes scrapers.
Provides keyword loading and article scoring.
"""
import os
from typing import Dict, List


def load_keywords(filepath=None):
    # type: (str) -> Dict[str, List[str]]
    """Load keyword tiers from keywords.txt. Returns dict with keys 'A', 'B', 'C'."""
    if filepath is None:
        filepath = os.path.join(
            os.path.dirname(__file__), '..', 'keywords.txt'
        )

    tiers = {'A': [], 'B': [], 'C': []}
    current_tier = None

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                if 'TIER A' in line:
                    current_tier = 'A'
                elif 'TIER B' in line:
                    current_tier = 'B'
                elif 'TIER C' in line:
                    current_tier = 'C'
                continue
            if current_tier:
                tiers[current_tier].append(line.lower())

    return tiers


def load_keywords_flat(filepath=None):
    # type: (str) -> List[str]
    """Load keywords from Tier A and B as a flat list (for simple relevance checks)."""
    tiers = load_keywords(filepath)
    return tiers['A'] + tiers['B']


def score_article(text, keywords):
    # type: (str, Dict[str, List[str]]) -> int
    """Score an article's relevance. Returns integer score.

    Tier A: +3 per match (EA geography/orgs — almost certainly relevant)
    Tier B: +1 per match (topic relevance — nationally relevant)
    Tier C: -5 per match (discard signals — not relevant)
    """
    text_lower = text.lower()
    score = 0
    score += sum(3 for kw in keywords['A'] if kw in text_lower)
    score += sum(1 for kw in keywords['B'] if kw in text_lower)
    score += sum(-5 for kw in keywords['C'] if kw in text_lower)
    return score
