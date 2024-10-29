# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2024 Jesus Arias Fisteus
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see
# <https://www.gnu.org/licenses/>.
#


from dataclasses import dataclass
from typing import Iterator, Optional


@dataclass(frozen=True)
class QuestionPermutations:
    reference_model: str
    question_permutations: dict[str, list[int]]

    def unwind_question(self, question: int, model: str) -> int:
        # Input question numbers are 1-based
        # Returned question numbers are 0-based
        if model == self.reference_model:
            return question - 1
        elif model in self.question_permutations:
            return self.question_permutations[model][question - 1] - 1
        else:
            raise ValueError(f"Model {model} not defined in permutations")


@dataclass(frozen=True)
class ChoicePermutations:
    num_choices: int
    reference_model: str
    choice_permutations: dict[str, list[int]]

    def __post_init__(self):
        if not len(self.choice_permutations):
            raise ValueError("No permutations have been defined")

    def unwind_choice(self, choice: int, model: str) -> int:
        if choice == 0:
            # Blank answer
            return 0
        elif model == self.reference_model:
            return choice
        elif model in self.choice_permutations:
            return self.choice_permutations[model][choice - 1]
        else:
            raise ValueError(f"Model {model} not defined in permutations")

    def reference_choices(self, model: str) -> list[int]:
        if model == self.reference_model:
            return list(range(1, self.num_choices + 1))
        elif model in self.choice_permutations:
            return self.choice_permutations[model]
        else:
            raise ValueError(f"Model {model} not defined in permutations")


@dataclass(frozen=True)
class ExamPermutations:
    num_questions: int
    num_choices: int
    reference_model: str
    exam_permutations: dict[str, list[tuple[int, list[int]]]]

    def get_question_permutations(self) -> QuestionPermutations:
        return QuestionPermutations(
            reference_model=self.reference_model,
            question_permutations={
                model: [question for question, _ in self.exam_permutations[model]]
                for model in self.exam_permutations
            },
        )

    def unwind_choice_permutations(self) -> list[ChoicePermutations]:
        choice_permutations_list: list[dict[str, list[int]]] = [
            {} for _ in range(self.num_questions)
        ]
        for model, p in self.exam_permutations.items():
            for question_num, choice_permutations in p:
                choice_permutations_list[question_num - 1][model] = choice_permutations
        return [
            ChoicePermutations(
                num_choices=self.num_choices,
                reference_model=self.reference_model,
                choice_permutations=choice_permutations,
            )
            for choice_permutations in choice_permutations_list
        ]


class ExamStats:
    question_permutations: Optional[QuestionPermutations]
    question_stats: list["QuestionStats"]

    def __init__(
        self,
        num_questions: int,
        num_choices: int,
        correct_choices_dict: dict[str, list[set[int]]],
        permutations: Optional[ExamPermutations],
    ) -> None:
        self.question_stats = []
        if permutations is not None:
            self.question_permutations = permutations.get_question_permutations()
            choice_permutations_list = permutations.unwind_choice_permutations()
            correct_choices_dict = self._correct_choices_for_reference_model(
                correct_choices_dict, choice_permutations_list
            )
            correct_choices_list = self._unwind_correct_choices(
                num_questions, correct_choices_dict
            )
            self.question_stats = [
                QuestionStats(num_choices, correct_choices, permutations)
                for correct_choices, permutations in zip(
                    correct_choices_list, choice_permutations_list
                )
            ]
        else:
            self.question_permutations = None
            correct_choices_list = self._unwind_correct_choices(
                num_questions, correct_choices_dict
            )
            self.question_stats = [
                QuestionStats(num_choices, correct_choices, None)
                for correct_choices in correct_choices_list
            ]

    @property
    def models(self) -> list[str]:
        if self.question_permutations is not None:
            return sorted(
                [key for key in self.question_permutations.question_permutations]
            )
        elif self.question_stats:
            return self.question_stats[0].models
        else:
            raise ValueError("No models have been defined")

    @property
    def reference_model(self) -> Optional[str]:
        if self.question_permutations is not None:
            return self.question_permutations.reference_model
        else:
            return None

    def count_answer(self, answer: int, question: int, model: str) -> None:
        # Question numbers are 1-based
        if self.question_permutations is not None:
            reference_question = self.question_permutations.unwind_question(
                question, model
            )
        else:
            reference_question = question - 1
        self.question_stats[reference_question].count_answer(answer, model)

    def count_answers(self, answers: list[int], model: str) -> None:
        for question, answer in enumerate(answers):
            self.count_answer(answer, question + 1, model)

    def get_answer_counts(self, model: str) -> list[list[int]]:
        return [q.get_answer_counts(model) for q in self._reorder_question_stats(model)]

    def _reorder_question_stats(self, model: str) -> list["QuestionStats"]:
        if self.question_permutations is not None and model != self.reference_model:
            return [
                self.question_stats[q - 1]
                for q in self.question_permutations.question_permutations[model]
            ]
        else:
            return list(self.question_stats)

    @staticmethod
    def _unwind_correct_choices(
        num_questions: int, correct_choices: dict[str, list[set[int]]]
    ) -> list[dict[str, set[int]]]:
        return [
            {model: correct_choices[model][i] for model in correct_choices.keys()}
            for i in range(num_questions)
        ]

    def _correct_choices_for_reference_model(
        self,
        correct_choices_dict: dict[str, list[set[int]]],
        choice_permutations_list: list[ChoicePermutations],
    ) -> dict[str, list[set[int]]]:
        if self.question_permutations is None:
            raise ValueError("No question permutations have been defined")
        if not correct_choices_dict:
            raise ValueError("No correct choices have been defined for any model")
        reference_model = self.question_permutations.reference_model
        if reference_model in correct_choices_dict:
            correct_choices = {reference_model: correct_choices_dict[reference_model]}
        else:
            model = next(iter(correct_choices_dict))
            correct_choices = {
                reference_model: [
                    set() for _ in range(len(correct_choices_dict[model]))
                ]
            }
            for i, choices in enumerate(correct_choices_dict[model]):
                question = self.question_permutations.unwind_question(i + 1, model)
                correct_choices[reference_model][question] = {
                    choice_permutations_list[question].unwind_choice(choice, model)
                    for choice in choices
                }
        return correct_choices


class QuestionStats:
    correct_choices: dict[str, set[int]]
    permutations: Optional[ChoicePermutations]
    answer_counts: dict[str, list[int]]

    def __init__(
        self,
        num_choices,
        correct_choices: dict[str, set[int]],
        permutations: Optional[ChoicePermutations],
    ) -> None:
        self.correct_choices = correct_choices
        self.permutations = permutations
        self.answer_counts = {
            model: [0] * (num_choices + 1)  # pos. 0 is for blank answers
            for model in correct_choices
        }

    @property
    def models(self) -> list[str]:
        return sorted([key for key in self.answer_counts])

    def count_answer(self, answer: int, model: str) -> None:
        if self.permutations is not None:
            reference_choice = self.permutations.unwind_choice(answer, model)
            self.answer_counts[self.permutations.reference_model][reference_choice] += 1
        else:
            self.answer_counts[model][answer] += 1

    def get_answer_counts(self, model: str) -> list[int]:
        if self.permutations is not None:
            reference_choices = [0] + self.permutations.reference_choices(model)
            return [
                self.answer_counts[self.permutations.reference_model][choice]
                for choice in reference_choices
            ]
        else:
            return list(self.answer_counts[model])

    def get_answer_ratios(self, model: str) -> list[float]:
        counts = self.get_answer_counts(model)
        total = sum(counts)
        return [count / total for count in counts]

    def get_answer_percentages(self, model: str) -> list[float]:
        return [ratio * 100 for ratio in self.get_answer_ratios(model)]
