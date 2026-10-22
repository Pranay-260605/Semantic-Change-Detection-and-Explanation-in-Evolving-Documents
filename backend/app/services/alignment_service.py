"""Section-aware sentence alignment with one-to-one matching."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.optimize import linear_sum_assignment

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.comparison import AlignmentPair, AlignmentResult, AlignmentStatus
from app.models.document import Sentence

logger = get_logger(__name__)


class AlignmentService:
    """Align old/new sentences using similarity, section, and position."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def align(
        self,
        old_sentences: list[Sentence],
        new_sentences: list[Sentence],
        similarity_matrix: np.ndarray,
    ) -> AlignmentResult:
        """Return MATCHED / ADDED / DELETED pairs with one-to-one constraints."""
        n_old = len(old_sentences)
        n_new = len(new_sentences)
        if similarity_matrix.shape != (max(n_old, 0), max(n_new, 0)) and not (
            n_old == 0 or n_new == 0
        ):
            raise ValueError("Similarity matrix shape does not match sentence lists.")

        used_old: set[int] = set()
        used_new: set[int] = set()
        matched: list[AlignmentPair] = []

        groups = self._section_groups(old_sentences, new_sentences)
        for old_idx, new_idx in groups:
            pairs = self._match_group(
                old_idx,
                new_idx,
                old_sentences,
                new_sentences,
                similarity_matrix,
                threshold=self.settings.similarity_threshold,
            )
            for pair, i, j in pairs:
                used_old.add(i)
                used_new.add(j)
                matched.append(pair)

        leftover_old = [i for i in range(n_old) if i not in used_old]
        leftover_new = [i for i in range(n_new) if i not in used_new]
        if leftover_old and leftover_new:
            cross = self._match_group(
                leftover_old,
                leftover_new,
                old_sentences,
                new_sentences,
                similarity_matrix,
                threshold=self.settings.cross_section_similarity_threshold,
            )
            for pair, i, j in cross:
                used_old.add(i)
                used_new.add(j)
                matched.append(pair)

        pairs: list[AlignmentPair] = list(matched)
        for i, sentence in enumerate(old_sentences):
            if i not in used_old:
                pairs.append(
                    AlignmentPair(
                        status=AlignmentStatus.DELETED,
                        old_sentence_id=sentence.id,
                        similarity=None,
                        confidence=0.9,
                    )
                )
        for j, sentence in enumerate(new_sentences):
            if j not in used_new:
                pairs.append(
                    AlignmentPair(
                        status=AlignmentStatus.ADDED,
                        new_sentence_id=sentence.id,
                        similarity=None,
                        confidence=0.9,
                    )
                )

        logger.info(
            "alignment statistics matched=%s added=%s deleted=%s",
            len(matched),
            n_new - len(used_new),
            n_old - len(used_old),
        )
        return AlignmentResult(pairs=pairs)

    def _section_groups(
        self,
        old_sentences: list[Sentence],
        new_sentences: list[Sentence],
    ) -> list[tuple[list[int], list[int]]]:
        old_by_section: dict[str, list[int]] = defaultdict(list)
        new_by_section: dict[str, list[int]] = defaultdict(list)
        for index, sentence in enumerate(old_sentences):
            old_by_section[self._section_key(sentence)].append(index)
        for index, sentence in enumerate(new_sentences):
            new_by_section[self._section_key(sentence)].append(index)

        keys = sorted(set(old_by_section) | set(new_by_section))
        return [(old_by_section.get(key, []), new_by_section.get(key, [])) for key in keys]

    def _section_key(self, sentence: Sentence) -> str:
        if sentence.section_id:
            return sentence.section_id
        if sentence.section_title:
            return sentence.section_title.strip().lower()
        return "__default__"

    def _match_group(
        self,
        old_idx: list[int],
        new_idx: list[int],
        old_sentences: list[Sentence],
        new_sentences: list[Sentence],
        similarity_matrix: np.ndarray,
        *,
        threshold: float,
    ) -> list[tuple[AlignmentPair, int, int]]:
        if not old_idx or not new_idx:
            return []

        scores = np.zeros((len(old_idx), len(new_idx)), dtype=np.float32)
        for row, i in enumerate(old_idx):
            for col, j in enumerate(new_idx):
                similarity = float(similarity_matrix[i, j])
                scores[row, col] = self._combined_score(
                    similarity,
                    old_index=i,
                    new_index=j,
                    n_old=len(old_sentences),
                    n_new=len(new_sentences),
                    same_section=self._section_key(old_sentences[i]) == self._section_key(new_sentences[j]),
                )

        assignments = self._assign(scores, threshold)
        results: list[tuple[AlignmentPair, int, int]] = []
        for row, col, score in assignments:
            i = old_idx[row]
            j = new_idx[col]
            similarity = float(similarity_matrix[i, j])
            if similarity < threshold and score < threshold:
                continue
            confidence = float(max(0.0, min(1.0, 0.5 * similarity + 0.5 * score)))
            results.append(
                (
                    AlignmentPair(
                        status=AlignmentStatus.MATCHED,
                        old_sentence_id=old_sentences[i].id,
                        new_sentence_id=new_sentences[j].id,
                        similarity=round(similarity, 4),
                        confidence=round(confidence, 4),
                    ),
                    i,
                    j,
                )
            )
        return results

    def _combined_score(
        self,
        similarity: float,
        *,
        old_index: int,
        new_index: int,
        n_old: int,
        n_new: int,
        same_section: bool,
    ) -> float:
        old_pos = old_index / max(n_old - 1, 1)
        new_pos = new_index / max(n_new - 1, 1)
        proximity = 1.0 - abs(old_pos - new_pos)
        section_bonus = 1.0 if same_section else 0.0
        return float(0.75 * similarity + 0.15 * proximity + 0.10 * section_bonus)

    def _assign(self, scores: np.ndarray, threshold: float) -> list[tuple[int, int, float]]:
        rows, cols = scores.shape
        if rows * cols <= 0:
            return []
        use_hungarian = max(rows, cols) <= self.settings.alignment_hungarian_limit
        if use_hungarian:
            cost = 1.0 - scores
            cost = np.where(scores < threshold, 10.0, cost)
            row_ind, col_ind = linear_sum_assignment(cost)
            assigned: list[tuple[int, int, float]] = []
            used_cols: set[int] = set()
            for r, c in zip(row_ind, col_ind):
                score = float(scores[r, c])
                if score < threshold:
                    continue
                assigned.append((int(r), int(c), score))
                used_cols.add(int(c))
            return assigned
        return self._greedy(scores, threshold)

    def _greedy(self, scores: np.ndarray, threshold: float) -> list[tuple[int, int, float]]:
        candidates: list[tuple[float, int, int]] = []
        for r in range(scores.shape[0]):
            for c in range(scores.shape[1]):
                score = float(scores[r, c])
                if score >= threshold:
                    candidates.append((score, r, c))
        candidates.sort(reverse=True)
        used_rows: set[int] = set()
        used_cols: set[int] = set()
        assigned: list[tuple[int, int, float]] = []
        for score, r, c in candidates:
            if r in used_rows or c in used_cols:
                continue
            used_rows.add(r)
            used_cols.add(c)
            assigned.append((r, c, score))
        return assigned
