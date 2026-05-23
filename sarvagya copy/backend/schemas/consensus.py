from __future__ import annotations

from pydantic import BaseModel, Field


class OCRCandidate(BaseModel):
    engine: str
    text: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class LineContributor(BaseModel):
    engine: str
    text: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    similarity: float = Field(default=0.0, ge=0.0, le=1.0)


class ConsensusLineResult(BaseModel):
    index: int
    text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    support: float = Field(default=0.0, ge=0.0, le=1.0)
    inserted: bool = False
    contributors: list[LineContributor] = Field(default_factory=list)


class ConsensusResult(BaseModel):
    engine: str = Field(default="consensus")
    selected_engine: str
    text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    support: float = Field(default=0.0, ge=0.0, le=1.0)
    scores: dict[str, float] = Field(default_factory=dict)
    candidates: list[OCRCandidate] = Field(default_factory=list)
    line_results: list[ConsensusLineResult] = Field(default_factory=list)


class OCREnsembleResult(BaseModel):
    outputs: list[OCRCandidate] = Field(default_factory=list)
    consensus: ConsensusResult | None = None
