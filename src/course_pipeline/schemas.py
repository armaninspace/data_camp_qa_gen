
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


Correctness = Literal["correct", "incorrect", "uncertain"]
TopicType = Literal[
    "concept",
    "procedure",
    "tool",
    "metric",
    "test",
    "chapter_wrapper",
    "example_block",
    "case_study_container",
    "other",
]
RepairStatus = Literal["accepted", "repaired", "rejected"]
QuestionStatus = Literal["answered", "rejected", "errored"]


class Chapter(BaseModel):
    chapter_index: int
    title: str
    summary: str | None = None
    source: Literal["syllabus", "overview_inferred"] = "syllabus"
    confidence: float = 1.0


class NormalizedCourse(BaseModel):
    course_id: str
    title: str
    provider: str | None = None
    summary: str | None = None
    overview: str | None = None
    chapters: list[Chapter] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    source_refs: dict = Field(default_factory=dict)


class TopicEvidence(BaseModel):
    source: str
    text: str


class Topic(BaseModel):
    topic_id: str
    label: str
    topic_type: TopicType = "concept"
    description: str
    evidence: list[TopicEvidence] = Field(default_factory=list)
    confidence: float = 0.5


class CanonicalTopic(BaseModel):
    canonical_topic_id: str
    label: str
    aliases: list[str] = Field(default_factory=list)
    member_topic_ids: list[str] = Field(default_factory=list)
    topic_type: TopicType = "concept"


class QuestionCandidate(BaseModel):
    candidate_id: str
    relevant_topics: list[str]
    family: str
    pattern: str
    question_text: str


class QuestionRepair(BaseModel):
    candidate_id: str
    status: RepairStatus
    original_text: str
    final_text: str | None = None
    reject_reason: str | None = None


class AnswerRecord(BaseModel):
    question_id: str
    question_text: str
    answer_text: str | None = None
    correctness: Correctness = "uncertain"
    confidence: float = 0.0
    evidence: list[TopicEvidence] = Field(default_factory=list)


class LedgerRow(BaseModel):
    row_id: str
    course: dict
    relevant_topics: list[str]
    question_text: str
    question_answer: str | None
    correctness: Correctness | None = None
    question_family: str
    status: QuestionStatus
    reject_reason: str | None = None
    source_evidence: list[TopicEvidence] = Field(default_factory=list)


class CourseBundle(BaseModel):
    course_id: str
    title: str
    normalized_course: NormalizedCourse
    extracted_topics: list[Topic]
    canonical_topics: list[CanonicalTopic]
    question_candidates: list[QuestionCandidate]
    question_repairs: list[QuestionRepair]
    answers: list[AnswerRecord]
    final_rows: list[LedgerRow]
    summary: dict = Field(default_factory=dict)


class ExcludedCourseRecord(BaseModel):
    course_id: str
    source_path: str
    quality_status: Literal["broken"]
    exclude_reason: str
    title_raw: str | None = None
    overview_present: bool = False
    syllabus_count: int = 0
