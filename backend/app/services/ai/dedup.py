"""Semantic deduplication of news items using Gemini embeddings.

Strategy:
  1. Compute embedding for each title+summary
  2. Cluster by cosine similarity (threshold 0.85)
  3. Keep best item per cluster (priority: high-impact source > longer content > newer)

Falls back to title-based dedup if embeddings fail.
"""
import asyncio
import logging
from typing import List, Optional

from app.services.scraper.base import ScrapedItem

logger = logging.getLogger(__name__)

# Cosine similarity threshold — items above this are considered duplicates
SIMILARITY_THRESHOLD = 0.85

# Source priority for picking representative from cluster (higher = keep)
SOURCE_PRIORITY = {
    "forex_factory": 10,      # Official economic calendar
    "forex_factory_xml": 10,
    "reuters": 9,              # Tier-1 wire
    "bloomberg": 9,
    "investing": 7,
    "finviz": 6,
    "forexlive": 6,
    "babypips_rss": 3,
    "tradingview": 1,
}


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _item_priority(item: ScrapedItem) -> tuple:
    """Priority tuple for picking best item from duplicate cluster.

    Returns (source_priority, content_length). Higher is better.
    """
    src_pri = SOURCE_PRIORITY.get((item.source or "").lower(), 5)
    content_len = len(item.content or "")
    return (src_pri, content_len)


class SemanticDeduplicator:
    """Clusters near-duplicate news items via embedding similarity."""

    def __init__(self, gemini_service):
        self._gemini = gemini_service

    async def deduplicate(
        self, items: List[ScrapedItem]
    ) -> List[ScrapedItem]:
        """Cluster items and keep best representative from each cluster.

        If embeddings unavailable → falls back to title-based dedup.
        """
        if not items:
            return []

        if len(items) == 1:
            return items

        # First pass: basic title dedup (cheap, catches exact copies)
        seen_titles: set = set()
        title_deduped: List[ScrapedItem] = []
        for item in items:
            title_key = (item.title or "").strip().lower()[:80]
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                title_deduped.append(item)

        # If very small list, skip expensive embedding step
        if len(title_deduped) <= 3:
            return title_deduped

        # Second pass: semantic dedup via embeddings
        try:
            embeddings = await self._get_embeddings(title_deduped)
        except Exception as e:
            logger.warning(f"[dedup] Embedding batch failed: {e} — using title dedup only")
            return title_deduped

        # Count how many items actually got embeddings
        valid_count = sum(1 for e in embeddings if e is not None)
        if valid_count < len(title_deduped) * 0.5:
            # Less than half got embeddings → fall back to title dedup
            logger.warning(
                f"[dedup] Only {valid_count}/{len(title_deduped)} embeddings — using title dedup"
            )
            return title_deduped

        # Cluster items
        clusters = self._cluster_items(title_deduped, embeddings)

        # Pick best from each cluster
        representatives: List[ScrapedItem] = []
        for cluster in clusters:
            best = max(cluster, key=_item_priority)
            representatives.append(best)

        logger.info(
            f"[dedup] {len(items)} → {len(title_deduped)} (title) → "
            f"{len(representatives)} (semantic, {len(clusters)} clusters)"
        )
        return representatives

    async def _get_embeddings(
        self, items: List[ScrapedItem]
    ) -> List[Optional[List[float]]]:
        """Get embeddings for all items in parallel."""
        tasks = []
        for item in items:
            # Embed title + first 200 chars of content
            text = f"{item.title} {(item.content or '')[:200]}"
            tasks.append(self._gemini.embed_text(text))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        embeddings: List[Optional[List[float]]] = []
        for r in results:
            if isinstance(r, Exception) or r is None:
                embeddings.append(None)
            else:
                embeddings.append(r)
        return embeddings

    def _cluster_items(
        self,
        items: List[ScrapedItem],
        embeddings: List[Optional[List[float]]],
    ) -> List[List[ScrapedItem]]:
        """Greedy clustering: each item joins first cluster with similarity > threshold."""
        clusters: List[List[int]] = []  # list of item indices per cluster

        for i, emb in enumerate(embeddings):
            if emb is None:
                # No embedding → each goes in own cluster
                clusters.append([i])
                continue

            # Try to join existing cluster
            joined = False
            for cluster in clusters:
                # Compare with first item in cluster (representative)
                rep_idx = cluster[0]
                rep_emb = embeddings[rep_idx]
                if rep_emb is None:
                    continue
                sim = _cosine_similarity(emb, rep_emb)
                if sim >= SIMILARITY_THRESHOLD:
                    cluster.append(i)
                    joined = True
                    break

            if not joined:
                clusters.append([i])

        # Return as list of ScrapedItem groups
        return [[items[i] for i in c] for c in clusters]
