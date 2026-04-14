from __future__ import annotations


def generate_report(confidence: float, diagnosis: str) -> str:
    prompt = (
        "류마티스 관절염 평가 영상이다.\n"
        "Grad-CAM에서 관절 부위 강조됨.\n"
        f"신뢰도: {confidence:.2f}\n"
        f"판정: {diagnosis}\n\n"
        "보수적인 영상의학 판독문 작성"
    )

    sections = [
        "Exam: Hand / Wrist RA evaluation",
        "",
        "[Finding]",
        "- Mild inflammatory change is suggested near the highlighted joint region.",
        "- No definite advanced destructive change is confirmed by this mock AI workflow.",
        "- Correlation with clinical symptom severity and formal radiology review is recommended.",
        "",
        "[Impression]",
        f"- AI assessment: {diagnosis}",
        f"- Confidence score: {confidence:.0%}",
        "",
        "[Prompt Strategy]",
        prompt,
    ]

    report = "\n".join(sections)
    if confidence < 0.5:
        return f"limited confidence\n\n{report}"
    return report
