from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Resolve to composer/conditional/conditional_questions.json
DEFAULT_JSON_PATH = Path(__file__).with_name("conditional_questions.json")


@dataclass(frozen=True)
class ConditionalQuestion:
    key: str
    label: str
    subsections: list[str]

    def matches_subsection_name(self, name):
        """
        Case-insensitive comparison against any configured subsection name.
        """
        normalized_name = (name or "").strip().casefold()
        return any(
            normalized_name == subsection.strip().casefold()
            for subsection in self.subsections
        )


class ConditionalQuestionRegistry(dict[str, ConditionalQuestion]):
    """
    Registry of ConditionalQuestion objects, keyed by question.key.
    """

    @classmethod
    def from_json(cls, path: str | Path) -> "ConditionalQuestionRegistry":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        reg = cls()
        for row in data:
            q = ConditionalQuestion(
                key=row["key"],
                label=row["label"],
                subsections=row.get("subsections", []),
            )
            reg[q.key] = q
        return reg

    @classmethod
    def load_default(cls) -> "ConditionalQuestionRegistry":
        """
        Load the registry from the default JSON file that lives next
        to this module: conditional_questions.json.
        """
        return cls.from_json(DEFAULT_JSON_PATH)

    def related_subsections(self, question_key, subsections):
        """
        Return all subsections whose name matches this question's subsections.
        """
        question = self[question_key]
        return [
            subsection
            for subsection in subsections
            if question.matches_subsection_name(subsection.name)
        ]


CONDITIONAL_QUESTIONS = ConditionalQuestionRegistry.from_json(DEFAULT_JSON_PATH)


def find_question_for_subsection(subsection):
    for question in CONDITIONAL_QUESTIONS.values():
        if question.matches_subsection_name(subsection.name):
            return question
    return None
