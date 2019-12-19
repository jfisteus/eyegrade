# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2019 Jesus Arias Fisteus
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

import random

from typing import Dict, List, Optional, Iterator, Tuple

from .. import utils


class ExamQuestions:
    def __init__(self):
        self.questions = QuestionsContainer()
        self.subject = None
        self.degree = None
        self.date = None
        self.duration = None
        self.student_id_label = None
        self._student_id_length = None
        self.scores = None
        self.shuffled_questions = {}
        self.permutations = {}

    @property
    def student_id_length(self):
        return self._student_id_length

    @student_id_length.setter
    def student_id_length(self, length):
        if length >= 0 and length <= 16:
            self._student_id_length = length
        else:
            raise utils.EyegradeException(
                "Student id length must be bewteen " "0 and 16 (both included)"
            )

    def num_questions(self):
        """Returns the number of questions of the exam."""
        return len(self.questions)

    def num_choices(self):
        """Returns the number of choices of the questions.

           If not all the questions have the same number of choices,
           it returns the maximum. If there are no exams, it returns None.

        """
        num = [q.num_choices for q in self.questions]
        if len(num) > 0:
            return max(num)
        else:
            return None

    def homogeneous_num_choices(self):
        """Returns True if all the questions have the same number of choices.

        Returns None if the list of questions is empty.

        """
        num = [q.num_choices for q in self.questions]
        if len(num) > 0:
            return min(num) == max(num)
        else:
            return None

    def shuffle(self, model):
        """Shuffles questions and options within questions for the given model.

        """
        shuffled, permutations = self.questions.shuffle()
        self.shuffled_questions[model] = shuffled
        self.permutations[model] = permutations
        for question in self.questions:
            question.shuffle(model)

    def set_permutation(self, model, permutation):
        self.permutations[model] = [p[0] - 1 for p in permutation]
        self.shuffled_questions[model] = [
            self.questions[i] for i in self.permutations[model]
        ]
        for question, permutation in zip(self.shuffled_questions[model], permutation):
            question.permutations[model] = [i - 1 for i in permutation[1]]

    def solutions_and_permutations(self, model):
        solutions = []
        permutations = []
        for qid in self.permutations[model]:
            answers_perm = self.questions[qid].permutations[model]
            solutions.append(1 + answers_perm.index(0))
            permutations.append((qid + 1, utils.increment_list(answers_perm)))
        return solutions, permutations


class QuestionsContainer:
    groups: List["QuestionsGroup"]

    def __init__(self):
        self.groups = []

    def __len__(self) -> int:
        return sum(len(group) for group in self.groups)

    def __iter__(self) -> Iterator["Question"]:
        return self._iterate_questions()

    def __getitem__(self, index: int) -> "Question":
        if index < 0:
            pos = len(self) - index
        else:
            pos = index
        i = 0
        for group in self.groups:
            if i + len(group) > pos:
                return group[pos - i]
            i += len(group)
        raise IndexError("QuestionsContainer index out of range: {}".format(index))

    def append(self, element: "QuestionsGroup") -> None:
        if isinstance(element, QuestionsGroup):
            self.groups.append(element)
        else:
            self.groups.append(QuestionsGroup([element]))

    def shuffle(self) -> Tuple[List["Question"], List[int]]:
        """Returns a tuple (list of questions, permutations) with data shuffled.

        Permutations is another list with the original position of each
        question. That is, question shuffled[i] was in the original list in
        permutations[i] position.

        It returns just a list of questions, without groupings.

        """
        to_sort = [(random.random(), item) for item in self.groups]
        questions = []
        permutations = []
        for _, group in sorted(to_sort):
            questions.extend(group.questions)
            permutations.extend(self._positions(group))
        return questions, permutations

    def _iterate_questions(self) -> Iterator["Question"]:
        for group in self.groups:
            for question in group:
                yield question

    def _positions(self, group: "QuestionsGroup") -> List[int]:
        pos = 0
        for g in self.groups:
            if g is group:
                return list(range(pos, pos + len(g)))
            else:
                pos += len(g)
        raise ValueError("Group not in group container")


class QuestionsGroup:
    questions: List["Question"]

    def __init__(self, questions):
        self.questions = questions

    def __len__(self) -> int:
        return len(self.questions)

    def __iter__(self) -> Iterator["Question"]:
        return iter(self.questions)

    def __getitem__(self, index) -> "Question":
        return self.questions[index]


class Question:
    variations: List["QuestionVariation"]
    permutations: Dict[str, List[int]]
    selected_variation: Dict[str, int]

    def __init__(self):
        self.variations = []
        self.permutations = {}
        self.selected_variation = {}

    @property
    def num_choices(self) -> int:
        if not self.variations:
            raise ValueError("At least one question variation needed")
        return self.variations[0].num_choices

    @property
    def num_correct_choices(self) -> int:
        if not self.variations:
            raise ValueError("At least one question variation needed")
        return self.variations[0].num_correct_choices

    def text(self, model: str) -> "QuestionComponent":
        return self.variations[self.selected_variation[model]].text

    def shuffled_choices(self, model: str) -> List["QuestionComponent"]:
        return self.variations[self.selected_variation[model]].shuffled_choices(
            self.permutations[model]
        )

    def correct_choices(self, model: str) -> List["QuestionComponent"]:
        return self.variations[self.selected_variation[model]].correct_choices

    def add_variation(
        self,
        text: "QuestionComponent",
        correct_choices: List["QuestionComponent"],
        incorrect_choices: List["QuestionComponent"],
    ) -> None:
        variation = QuestionVariation(text, correct_choices, incorrect_choices)
        if self.variations and not self.variations[0].is_compatible(variation):
            raise utils.EyegradeException("incompatible_variation")
        self.variations.append(variation)

    def shuffle(self, model: str) -> None:
        if not self.variations:
            raise ValueError("Cannot shuffle without at least one variation")
        to_sort = [(random.random(), pos) for pos in range(self.num_choices)]
        permutations = []
        for _, pos in sorted(to_sort):
            permutations.append(pos)
        self.permutations[model] = permutations

    def select_variation(self, model: str, index: int) -> None:
        if index < 0 or index >= len(self.variations):
            raise ValueError("Variation index out of range")
        self.selected_variation[model] = index


class FixedQuestion(Question):
    """ A question without variations, i.e. just one variation."""

    def __init__(
        self,
        text: "QuestionComponent",
        correct_choices: List["QuestionComponent"],
        incorrect_choices: List["QuestionComponent"],
    ):
        super().__init__()
        self.add_variation(text, correct_choices, incorrect_choices)

    def text(self, model: str) -> "QuestionComponent":
        return self.variations[0].text

    def shuffled_choices(self, model: str) -> List["QuestionComponent"]:
        return self.variations[0].shuffled_choices(self.permutations[model])

    def correct_choices(self, model: str) -> List["QuestionComponent"]:
        return self.variations[0].correct_choices

    def add_variation(
        self,
        text: "QuestionComponent",
        correct_choices: List["QuestionComponent"],
        incorrect_choices: List["QuestionComponent"],
    ) -> None:
        if self.variations:
            raise ValueError("Just one variation allowed in FixedQuestion")
        super().add_variation(text, correct_choices, incorrect_choices)


class QuestionVariation:
    text: "QuestionComponent"
    correct_choices: List["QuestionComponent"]
    incorrect_choices: List["QuestionComponent"]

    def __init__(
        self,
        text: "QuestionComponent",
        correct_choices: List["QuestionComponent"],
        incorrect_choices: List["QuestionComponent"],
    ):
        self.text = text
        self.correct_choices = correct_choices
        self.incorrect_choices = incorrect_choices

    @property
    def num_choices(self) -> int:
        return len(self.correct_choices) + len(self.incorrect_choices)

    @property
    def num_correct_choices(self) -> int:
        return len(self.correct_choices)

    def is_compatible(self, other: "QuestionVariation") -> bool:
        return (
            self.num_choices == other.num_choices
            and self.num_correct_choices == other.num_correct_choices
        )

    def shuffled_choices(self, permutation: List[int]) -> List["QuestionComponent"]:
        choices = self.correct_choices + self.incorrect_choices
        return [choices[i] for i in permutation]


class QuestionComponent:
    """A piece of text and optional figure or code.

       Represents both the text of a question and its choices.

    """

    in_choice: bool
    text: Optional[str]
    code: Optional[str]
    figure: Optional[str]
    annex_width: Optional[float]
    annex_pos: Optional[str]

    def __init__(self, in_choice: bool):
        self.in_choice = in_choice
        self.text = None
        self.code = None
        self.figure = None
        self.annex_width = None
        self.annex_pos = None

    def check_is_valid(self) -> None:
        if self.code is not None and self.figure is not None:
            raise Exception("Code and figure cannot be in the same block")
        if (
            self.in_choice
            and self.annex_pos != "center"
            and (self.code is not None or self.figure is not None)
        ):
            raise Exception("Figures and code in answers must be centered")
        if (
            self.code is not None
            and self.annex_pos == "center"
            and self.annex_width is not None
        ):
            raise Exception("Centered code cannot have width")
        if not self.in_choice and self.text is None:
            raise Exception("Questions must have a text")
