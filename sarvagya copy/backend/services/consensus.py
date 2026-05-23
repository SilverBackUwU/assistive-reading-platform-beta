from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re
import unicodedata
from difflib import SequenceMatcher
from logging import getLogger
from typing import Any, Mapping, Sequence

from schemas.consensus import ConsensusLineResult, ConsensusResult, LineContributor, OCRCandidate
from utils.text_cleaner import clean_ocr_text, is_valid_ocr_text, preview_ocr_text


logger = getLogger(__name__)


@dataclass(slots=True)
class _LineEvidence:
    engine: str
    text: str
    confidence: float
    source_index: int


class OCRConsensusEngine:
    def select(self, outputs: Sequence[Mapping[str, Any] | OCRCandidate]) -> ConsensusResult | None:
        candidates = [self._coerce_candidate(output) for output in outputs]
        valid_candidates = [candidate for candidate in candidates if self._is_valid(candidate)]
        rejected_candidates = [candidate for candidate in candidates if candidate not in valid_candidates]

        if rejected_candidates:
            logger.info(
                "OCR consensus rejected engines: %s",
                ", ".join(
                    f"{candidate.engine}({self._rejection_reason(candidate)})"
                    for candidate in rejected_candidates
                ),
            )

        if not valid_candidates:
            logger.warning("OCR consensus skipped because no engine produced usable text.")
            return None

        scores = self._score_candidates(valid_candidates)
        anchor = self._select_anchor(valid_candidates, scores)
        line_results = self._merge_lines(anchor, valid_candidates, scores)

        if not line_results:
            line_results = [
                ConsensusLineResult(
                    index=0,
                    text=anchor.text.strip(),
                    confidence=round(anchor.confidence, 4),
                    support=1.0,
                    inserted=False,
                    contributors=[
                        LineContributor(
                            engine=anchor.engine,
                            text=anchor.text.strip(),
                            confidence=anchor.confidence,
                            similarity=1.0,
                        )
                    ],
                )
            ]

        merged_text = self._render_text(line_results)
        support = self._overall_support(line_results)
        consensus_confidence = self._overall_confidence(line_results)

        logger.info(
            "OCR consensus selected engine=%s support=%.3f confidence=%.3f preview=%s",
            anchor.engine,
            support,
            consensus_confidence,
            preview_ocr_text(merged_text),
        )

        return ConsensusResult(
            selected_engine=anchor.engine,
            text=merged_text,
            confidence=consensus_confidence,
            support=support,
            scores={candidate.engine: scores[candidate.engine] for candidate in valid_candidates},
            candidates=valid_candidates,
            line_results=line_results,
        )

    def _coerce_candidate(self, output: Mapping[str, Any] | OCRCandidate) -> OCRCandidate:
        if isinstance(output, OCRCandidate):
            return output.model_copy(update={"text": clean_ocr_text(output.text)})

        engine = str(output.get("engine") or "unknown")
        text = clean_ocr_text(str(output.get("text") or ""))
        confidence_value = output.get("confidence", 0.0)
        try:
            confidence = float(confidence_value or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0

        return OCRCandidate(
            engine=engine,
            text=text,
            confidence=max(0.0, min(1.0, confidence)),
        )

    def _is_valid(self, candidate: OCRCandidate) -> bool:
        return candidate.confidence > 0.0 and is_valid_ocr_text(candidate.text)

    def _rejection_reason(self, candidate: OCRCandidate) -> str:
        if candidate.confidence <= 0.0:
            return "zero confidence"
        if not candidate.text.strip():
            return "empty"
        if re.search(r"data\s*\\?:\s*image", candidate.text, flags=re.IGNORECASE):
            return "image data"
        if not is_valid_ocr_text(candidate.text):
            return "encoded garbage"
        return "invalid"

    def _score_candidates(self, candidates: Sequence[OCRCandidate]) -> dict[str, float]:
        scores: dict[str, float] = {}
        normalized_texts = {candidate.engine: self._normalize_text(candidate.text) for candidate in candidates}

        for candidate in candidates:
            similarities: list[float] = []
            weights: list[float] = []
            current_text = normalized_texts[candidate.engine]

            for peer in candidates:
                if peer.engine == candidate.engine:
                    continue
                peer_text = normalized_texts[peer.engine]
                similarities.append(self._similarity(current_text, peer_text))
                weights.append(max(peer.confidence, 0.05))

            support = self._weighted_average(similarities, weights, default=1.0)
            score = (candidate.confidence * 0.60) + (support * 0.40)
            scores[candidate.engine] = round(score, 4)

        return scores

    def _select_anchor(self, candidates: Sequence[OCRCandidate], scores: Mapping[str, float]) -> OCRCandidate:
        return max(
            candidates,
            key=lambda candidate: (
                scores[candidate.engine],
                candidate.confidence,
                len(candidate.text),
            ),
        )

    def _merge_lines(
        self,
        anchor: OCRCandidate,
        candidates: Sequence[OCRCandidate],
        candidate_scores: Mapping[str, float],
    ) -> list[ConsensusLineResult]:
        anchor_lines = self._split_lines(anchor.text)
        if not anchor_lines:
            return []

        slot_evidence: dict[int, list[_LineEvidence]] = {
            index: [
                _LineEvidence(
                    anchor.engine,
                    line,
                    self._effective_confidence(anchor.confidence, candidate_scores.get(anchor.engine, anchor.confidence)),
                    index,
                )
            ]
            for index, line in enumerate(anchor_lines)
        }
        insertion_buckets: dict[int, list[_LineEvidence]] = defaultdict(list)

        for peer in candidates:
            if peer.engine == anchor.engine:
                continue

            peer_lines = self._split_lines(peer.text)
            if not peer_lines:
                continue

            alignment = self._align_lines(anchor_lines, peer_lines)
            anchor_cursor = 0

            for anchor_index, peer_index in alignment:
                if anchor_index is not None and peer_index is not None:
                    slot_evidence.setdefault(anchor_index, []).append(
                        _LineEvidence(
                            peer.engine,
                            peer_lines[peer_index],
                            self._effective_confidence(peer.confidence, candidate_scores.get(peer.engine, peer.confidence)),
                            peer_index,
                        )
                    )
                    anchor_cursor = anchor_index + 1
                    continue

                if anchor_index is not None:
                    anchor_cursor = anchor_index + 1
                    continue

                if peer_index is not None:
                    insertion_buckets[anchor_cursor].append(
                        _LineEvidence(
                            peer.engine,
                            peer_lines[peer_index],
                            self._effective_confidence(peer.confidence, candidate_scores.get(peer.engine, peer.confidence)),
                            peer_index,
                        )
                    )

        line_results: list[ConsensusLineResult] = []

        for index in range(len(anchor_lines) + 1):
            inserted_evidences = insertion_buckets.get(index, [])
            if inserted_evidences:
                line_results.extend(self._build_line_results(inserted_evidences, inserted=True))

            if index < len(anchor_lines):
                evidences = slot_evidence.get(index, [])
                line_results.extend(self._build_line_results(evidences, inserted=False, index=index))

        for index, line_result in enumerate(line_results):
            line_results[index] = line_result.model_copy(update={"index": index})

        return line_results

    def _build_line_results(
        self,
        evidences: Sequence[_LineEvidence],
        inserted: bool,
        index: int | None = None,
    ) -> list[ConsensusLineResult]:
        clusters = self._cluster_evidences(evidences)
        if not clusters:
            return []

        results: list[ConsensusLineResult] = []

        if inserted:
            for cluster in sorted(clusters, key=self._cluster_order_key):
                selected, support, confidence, contributors = self._finalize_cluster(cluster)
                results.append(
                    ConsensusLineResult(
                        index=index or 0,
                        text=selected,
                        confidence=confidence,
                        support=support,
                        inserted=True,
                        contributors=contributors,
                    )
                )
            return results

        selected_cluster = max(clusters, key=self._cluster_score)
        selected, support, confidence, contributors = self._finalize_cluster(selected_cluster)
        return [
            ConsensusLineResult(
                index=index or 0,
                text=selected,
                confidence=confidence,
                support=support,
                inserted=False,
                contributors=contributors,
            )
        ]

    def _cluster_evidences(self, evidences: Sequence[_LineEvidence]) -> list[list[_LineEvidence]]:
        clusters: list[list[_LineEvidence]] = []
        ordered = sorted(
            evidences,
            key=lambda evidence: (
                evidence.confidence,
                len(self._normalize_text(evidence.text)),
            ),
            reverse=True,
        )

        for evidence in ordered:
            placed = False
            for cluster in clusters:
                representative = self._choose_representative(cluster)
                similarity = self._similarity(
                    self._normalize_text(evidence.text),
                    self._normalize_text(representative.text),
                )
                threshold = 0.88 if not evidence.text.strip() or not representative.text.strip() else 0.70
                if similarity >= threshold:
                    cluster.append(evidence)
                    placed = True
                    break
            if not placed:
                clusters.append([evidence])

        return clusters

    def _choose_representative(self, cluster: Sequence[_LineEvidence]) -> _LineEvidence:
        return max(cluster, key=lambda evidence: self._line_evidence_score(evidence, cluster))

    def _line_evidence_score(self, evidence: _LineEvidence, cluster: Sequence[_LineEvidence]) -> float:
        support = self._evidence_support(evidence, cluster)
        return (evidence.confidence * 0.60) + (support * 0.40)

    def _evidence_support(self, evidence: _LineEvidence, cluster: Sequence[_LineEvidence]) -> float:
        similarities: list[float] = []
        weights: list[float] = []
        normalized = self._normalize_text(evidence.text)

        for peer in cluster:
            if peer is evidence:
                continue
            similarities.append(self._similarity(normalized, self._normalize_text(peer.text)))
            weights.append(max(peer.confidence, 0.05))

        return self._weighted_average(similarities, weights, default=1.0)

    def _cluster_score(self, cluster: Sequence[_LineEvidence]) -> float:
        representative = self._choose_representative(cluster)
        support = self._evidence_support(representative, cluster)
        confidence = self._weighted_average(
            [evidence.confidence for evidence in cluster],
            [max(evidence.confidence, 0.05) for evidence in cluster],
            default=0.0,
        )
        return (confidence * 0.60) + (support * 0.40)

    def _cluster_order_key(self, cluster: Sequence[_LineEvidence]) -> tuple[int, float, float]:
        representative = self._choose_representative(cluster)
        return (
            min(evidence.source_index for evidence in cluster),
            -self._cluster_score(cluster),
            -representative.confidence,
        )

    def _finalize_cluster(self, cluster: Sequence[_LineEvidence]) -> tuple[str, float, float, list[LineContributor]]:
        representative = self._choose_representative(cluster)
        support = self._evidence_support(representative, cluster)
        confidence = self._weighted_average(
            [evidence.confidence for evidence in cluster],
            [max(evidence.confidence, 0.05) for evidence in cluster],
            default=0.0,
        )
        confidence = min(1.0, max(0.0, (confidence * 0.65) + (support * 0.35)))

        contributors = [
            LineContributor(
                engine=evidence.engine,
                text=evidence.text,
                confidence=max(0.0, min(1.0, evidence.confidence)),
                similarity=self._similarity(
                    self._normalize_text(evidence.text),
                    self._normalize_text(representative.text),
                ),
            )
            for evidence in sorted(
                cluster,
                key=lambda item: (
                    -item.confidence,
                    item.source_index,
                    item.engine,
                ),
            )
        ]

        return representative.text.strip(), round(support, 4), round(confidence, 4), contributors

    def _overall_confidence(self, line_results: Sequence[ConsensusLineResult]) -> float:
        if not line_results:
            return 0.0

        weights = [max(1, len(result.text.strip())) for result in line_results]
        confidences = [result.confidence for result in line_results]
        return round(self._weighted_average(confidences, weights, default=0.0), 4)

    def _overall_support(self, line_results: Sequence[ConsensusLineResult]) -> float:
        if not line_results:
            return 0.0

        weights = [max(1, len(result.text.strip())) for result in line_results]
        supports = [result.support for result in line_results]
        return round(self._weighted_average(supports, weights, default=0.0), 4)

    def _render_text(self, line_results: Sequence[ConsensusLineResult]) -> str:
        lines = [result.text for result in line_results]
        return "\n".join(lines).strip()

    def _normalize_text(self, value: str) -> str:
        value = unicodedata.normalize("NFKC", value)
        value = value.replace("\u200c", "").replace("\u200d", "")
        value = re.sub(r"\s+", " ", value).strip()
        return value.casefold()

    def _similarity(self, left: str, right: str) -> float:
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        return round(SequenceMatcher(None, left, right).ratio(), 4)

    def _split_lines(self, value: str) -> list[str]:
        normalized = value.replace("\r\n", "\n").replace("\r", "\n")
        raw_lines = normalized.split("\n")
        lines: list[str] = []
        pending_blank = False

        for raw_line in raw_lines:
            line = raw_line.strip()
            if line:
                lines.append(line)
                pending_blank = False
                continue

            if lines and not pending_blank:
                lines.append("")
                pending_blank = True

        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return lines

    def _align_lines(self, anchor_lines: Sequence[str], peer_lines: Sequence[str]) -> list[tuple[int | None, int | None]]:
        anchor_count = len(anchor_lines)
        peer_count = len(peer_lines)

        dp: list[list[float]] = [[0.0 for _ in range(peer_count + 1)] for _ in range(anchor_count + 1)]
        back: list[list[tuple[int, int, str] | None]] = [
            [None for _ in range(peer_count + 1)]
            for _ in range(anchor_count + 1)
        ]

        for i in range(1, anchor_count + 1):
            dp[i][0] = dp[i - 1][0] + self._gap_score(anchor_lines[i - 1])
            back[i][0] = (i - 1, 0, "anchor_gap")

        for j in range(1, peer_count + 1):
            dp[0][j] = dp[0][j - 1] + self._gap_score(peer_lines[j - 1])
            back[0][j] = (0, j - 1, "peer_gap")

        for i in range(1, anchor_count + 1):
            for j in range(1, peer_count + 1):
                match_score = dp[i - 1][j - 1] + self._line_match_score(anchor_lines[i - 1], peer_lines[j - 1])
                gap_anchor = dp[i - 1][j] + self._gap_score(anchor_lines[i - 1])
                gap_peer = dp[i][j - 1] + self._gap_score(peer_lines[j - 1])

                options = [
                    (match_score, 2, i - 1, j - 1, "match"),
                    (gap_anchor, 1, i - 1, j, "anchor_gap"),
                    (gap_peer, 0, i, j - 1, "peer_gap"),
                ]
                score, _, prev_i, prev_j, op = max(options, key=lambda item: (item[0], item[1]))
                dp[i][j] = score
                back[i][j] = (prev_i, prev_j, op)

        aligned: list[tuple[int | None, int | None]] = []
        i = anchor_count
        j = peer_count

        while i > 0 or j > 0:
            step = back[i][j]
            if step is None:
                break

            prev_i, prev_j, op = step
            if op == "match":
                aligned.append((i - 1, j - 1))
            elif op == "anchor_gap":
                aligned.append((i - 1, None))
            else:
                aligned.append((None, j - 1))
            i, j = prev_i, prev_j

        aligned.reverse()
        return aligned

    def _line_match_score(self, left: str, right: str) -> float:
        left_normalized = self._normalize_text(left)
        right_normalized = self._normalize_text(right)

        if not left_normalized and not right_normalized:
            return 0.75
        if not left_normalized or not right_normalized:
            return -0.40

        similarity = self._similarity(left_normalized, right_normalized)
        return round((similarity * 1.20) - 0.60, 4)

    def _gap_score(self, value: str) -> float:
        if not value.strip():
            return -0.08
        return -0.35

    def _effective_confidence(self, line_confidence: float, engine_score: float) -> float:
        blended = (line_confidence * 0.60) + (engine_score * 0.40)
        return max(0.0, min(1.0, blended))

    def _weighted_average(self, values: Sequence[float], weights: Sequence[float], default: float) -> float:
        if not values:
            return default

        total_weight = sum(max(weight, 0.0) for weight in weights)
        if total_weight <= 0:
            return default

        total = 0.0
        for value, weight in zip(values, weights):
            total += value * max(weight, 0.0)
        return total / total_weight
