
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


Correctness = Literal["correct", "incorrect", "uncertain"]
CourseQualityStatus = Literal["usable", "partial", "broken"]
AnswerMode = Literal["grounded_course_answer", "synthetic_tutor_answer", "blended_answer"]
TopicType = Literal[
    "concept",
    "procedure",
    "tool",
    "method",
    "metric",
    "test",
    "comparison_pair_candidate",
    "wrapper_or_container_candidate",
    "unknown",
    "chapter_wrapper",
    "example_block",
    "case_study_container",
    "other",
]
RepairStatus = Literal["accepted", "repaired", "rejected"]
QuestionStatus = Literal["answered", "rejected", "errored"]
TopicDecision = Literal["keep", "keep_entry_only", "keep_no_pairwise", "reject"]
PairDecision = Literal["keep_pair", "reject_pair"]


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
    evidence: list[TopicEvidence] = Field(default_factory=list)


class RelatedTopicPair(BaseModel):
    pair_id: str
    topic_x: str
    topic_y: str
    relation_type: str
    evidence_spans: list[TopicEvidence] = Field(default_factory=list)
    confidence: float = 0.0


class VettedTopic(BaseModel):
    canonical_topic_id: str
    canonical_label: str
    decision: TopicDecision
    allow_single_topic_questions: bool
    allow_pairwise_questions: bool
    reason: str
    final_topic_type: TopicType = "concept"
    evidence_spans: list[TopicEvidence] = Field(default_factory=list)


class VettedTopicPair(BaseModel):
    pair_id: str
    topic_x: str
    topic_y: str
    decision: PairDecision
    reason: str
    relation_type: str | None = None
    evidence_spans: list[TopicEvidence] = Field(default_factory=list)


class GeneratedQuestion(BaseModel):
    question_id: str
    relevant_topics: list[str]
    source_topic_ids: list[str] = Field(default_factory=list)
    source_pair_id: str | None = None
    family: str
    pattern: str
    question_text: str
    evidence_spans: list[TopicEvidence] = Field(default_factory=list)
    generation_scope: Literal["single_topic", "pairwise"]


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


class QuestionValidationRecord(BaseModel):
    question_id: str
    relevant_topics: list[str]
    status: RepairStatus
    original_text: str
    final_text: str | None = None
    reject_reason: str | None = None
    question_family: str
    evidence_spans: list[TopicEvidence] = Field(default_factory=list)


class AnswerRecord(BaseModel):
    question_id: str
    question_text: str
    answer_text: str | None = None
    correctness: Correctness = "uncertain"
    confidence: float = 0.0
    evidence: list[TopicEvidence] = Field(default_factory=list)
    answer_mode: AnswerMode = "synthetic_tutor_answer"
    validation_status: str | None = None
    rewrite_applied: bool = False
    provenance: dict = Field(default_factory=dict)


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
    raw_topics: list[Topic]
    canonical_topics: list[CanonicalTopic]
    vetted_topics: list[VettedTopic] = Field(default_factory=list)
    related_topic_pairs: list[RelatedTopicPair] = Field(default_factory=list)
    vetted_topic_pairs: list[VettedTopicPair] = Field(default_factory=list)
    single_topic_questions: list[GeneratedQuestion] = Field(default_factory=list)
    pairwise_questions: list[GeneratedQuestion] = Field(default_factory=list)
    question_validation: list[QuestionValidationRecord] = Field(default_factory=list)
    answers: list[AnswerRecord]
    synthetic_answers: list[SyntheticAnswerRecord] = Field(default_factory=list)
    synthetic_answer_validation: list[SyntheticAnswerValidationRecord] = Field(default_factory=list)
    synthetic_answer_rewrites: list[dict] = Field(default_factory=list)
    final_rows: list[LedgerRow]
    summary: dict = Field(default_factory=dict)


class SyntheticAnswerRecord(BaseModel):
    run_id: str
    course_id: str
    question_id: str
    question_text: str
    canonical_topic: str
    question_family: str
    difficulty_band: str | None = None
    answer_mode: Literal["synthetic_tutor_answer"] = "synthetic_tutor_answer"
    answer_text: str
    target_verbosity: str
    model_name: str
    prompt_family: str
    confidence: float | None = None
    risks: list[str] = Field(default_factory=list)


class SyntheticAnswerValidationRecord(BaseModel):
    run_id: str
    course_id: str
    question_id: str
    original_answer_text: str
    decision: Literal["accept", "rewrite", "reject"]
    correctness: float
    sufficiency: float
    brevity: float
    pedagogical_fit: float
    difficulty_alignment: float
    clarity: float
    contradiction_risk: float
    scope_drift: float
    rewritten_answer_text: str | None = None
    reject_reasons: list[str] = Field(default_factory=list)


class FineTuneRow(BaseModel):
    run_id: str
    course_id: str
    question_id: str
    prompt: str
    completion: str
    question_text: str
    answer_text: str
    canonical_topic: str
    question_family: str
    difficulty_band: str | None = None
    answer_mode: AnswerMode
    provenance: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class ExcludedCourseRecord(BaseModel):
    course_id: str
    source_path: str
    quality_status: Literal["broken"]
    exclude_reason: str
    title_raw: str | None = None
    overview_present: bool = False
    syllabus_count: int = 0


class PreflightCourseDecision(BaseModel):
    course_id: str
    source_path: str
    quality_status: CourseQualityStatus
    exclude_reason: str | None = None
    title_raw: str | None = None
    overview_present: bool = False
    syllabus_count: int = 0
