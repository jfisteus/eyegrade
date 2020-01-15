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

from typing import Dict, List, Set, Optional, Iterator, Tuple, Union, TYPE_CHECKING

from .. import utils

if TYPE_CHECKING:
    from .. import scoring


utils.EyegradeException.register_error(
    "same-variation-selected-group",
    "The same variation must be selected for questions within the same group.",
)


class ExamQuestions:
    questions: "QuestionsContainer"
    subject: Optional[str]
    degree: Optional[str]
    date: Optional[str]
    duration: Optional[str]
    student_id_label: Optional[str]
    shuffled_questions: Dict[str, List["Question"]]
    permutations: Dict[str, List[int]]
    scores: Optional[Union["scoring.QuestionScores", "scoring.AutomaticScore"]]
    _student_id_length: int

    def __init__(self):
        self.questions = QuestionsContainer()
        self.subject = None
        self.degree = None
        self.date = None
        self.duration = None
        self.student_id_label = None
        self._student_id_length = None
        self.shuffled_questions = {}
        self.permutations = {}
        self.scores = None

    @property
    def student_id_length(self) -> int:
        return self._student_id_length

    @student_id_length.setter
    def student_id_length(self, length: int) -> None:
        if 0 <= length <= 16:
            self._student_id_length = length
        else:
            raise utils.EyegradeException(
                "Student id length must be bewteen " "0 and 16 (both included)"
            )

    def num_questions(self) -> int:
        """Returns the number of questions of the exam."""
        return len(self.questions)

    def num_choices(self) -> Optional[int]:
        """Returns the number of choices of the questions.

           If not all the questions have the same number of choices,
           it returns the maximum. If there are no exams, it returns None.

        """
        num = [q.num_choices for q in self.questions]
        if num:
            return max(num)
        return None

    def homogeneous_num_choices(self) -> Optional[bool]:
        """Returns True if all the questions have the same number of choices.

        Returns None if the list of questions is empty.

        """
        num = [q.num_choices for q in self.questions]
        if num:
            return min(num) == max(num)
        return None

    def shuffle(self, model: str) -> None:
        """Shuffles questions and options within questions for the given model."""
        shuffled, permutations = self.questions.shuffle()
        self.shuffled_questions[model] = shuffled
        self.permutations[model] = permutations
        self._shuffle_variations(model)
        for question in self.questions:
            question.shuffle(model)

    def _shuffle_variations(self, model: str) -> None:
        """Chooses a variation for each question randomly."""
        self.questions.shuffle_variations(model)

    def select_variations(self, model: str, variations: List[int]) -> None:
        self.questions.select_variations(model, variations)

    def select_variation(self, model: str, variation: int) -> None:
        self.select_variations(model, [variation] * self.num_questions())

    def selected_variations(self, model) -> List[int]:
        return [
            question.selected_variation[model]
            for question in self.shuffled_questions[model]
        ]

    def set_permutation(
        self, model: str, permutations: List[Tuple[int, List[int]]]
    ) -> None:
        self.permutations[model] = [p[0] - 1 for p in permutations]
        self.shuffled_questions[model] = [
            self.questions[i] for i in self.permutations[model]
        ]
        for question, permutation in zip(self.shuffled_questions[model], permutations):
            question.permutations[model] = [i - 1 for i in permutation[1]]

    def solutions_and_permutations(
        self, model: str
    ) -> Tuple[List[Set[int]], List[Tuple[int, List[int]]]]:
        solutions = []
        permutations = []
        for qid in self.permutations[model]:
            answers_perm = self.questions[qid].permutations[model]
            solutions.append({1 + answers_perm.index(0)})
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

    def append(self, element: Union["QuestionsGroup", "Question"]) -> None:
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

    def shuffle_variations(self, model: str) -> None:
        """Chooses a variation for each question randomly.

        Variations are chosen group by group:
        the same variation is chosen for all the questions of each group.

        """
        for group in self.groups:
            group.shuffle_variations(model)

    def select_variations(self, model: str, variations: List[int]) -> None:
        pos = 0
        for group in self.groups:
            group_variations = variations[pos : pos + len(group)]
            if min(group_variations) < max(group_variations):
                raise utils.EyegradeException("", key="same-variation-selected-group")
            group.select_variation(model, group_variations[0])

    def _iterate_questions(self) -> Iterator["Question"]:
        for group in self.groups:
            for question in group:
                yield question

    def _positions(self, group: "QuestionsGroup") -> List[int]:
        pos = 0
        for other_group in self.groups:
            if other_group is group:
                return list(range(pos, pos + len(other_group)))
            else:
                pos += len(other_group)
        raise ValueError("Group not in group container")


class QuestionsGroup:
    questions: List["Question"]

    def __init__(self, questions: List["Question"]):
        if not questions:
            raise ValueError("Empty QuestionsGroup are not allowed")
        self.questions = questions
        self._check_number_variations()

    @property
    def num_variations(self) -> int:
        # All questions have been checked to have
        # the same number of variations by the constructor.
        return self.questions[0].num_variations

    def __len__(self) -> int:
        return len(self.questions)

    def __iter__(self) -> Iterator["Question"]:
        return iter(self.questions)

    def __getitem__(self, index) -> "Question":
        return self.questions[index]

    def shuffle_variations(self, model: str) -> None:
        """Chooses a variation for this group randomly.

        All questions get the same variation.

        """
        variation = random.randrange(self.num_variations)
        for question in self.questions:
            question.select_variation(model, variation)

    def select_variation(self, model: str, variation: int) -> None:
        for question in self.questions:
            question.select_variation(model, variation)

    def _check_number_variations(self) -> None:
        num_variations = [question.num_variations for question in self.questions]
        if min(num_variations) < max(num_variations):
            raise utils.EyegradeException("", key="incompatible_variation_num_group")


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

    @property
    def num_variations(self) -> int:
        return len(self.variations)

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
            raise utils.EyegradeException("", key="incompatible_variation")
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
        if index < 0:
            raise ValueError("Variation index out of range (negative)")
        elif index >= len(self.variations):
            if len(self.variations) == 1:
                index = 0
            else:
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

    def __init__(self, in_choice: bool, text: Optional[str] = None):
        self.in_choice = in_choice
        self.text = text
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
