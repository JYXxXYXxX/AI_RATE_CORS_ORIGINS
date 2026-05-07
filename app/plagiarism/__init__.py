from app.plagiarism.scoring import (
    DuplicationDocumentScore,
    DuplicationSectionScore,
    SimilarityEvidence,
    build_embedding_vector,
    score_duplication,
)

__all__ = [
    "DuplicationDocumentScore",
    "DuplicationSectionScore",
    "SimilarityEvidence",
    "build_embedding_vector",
    "score_duplication",
]
