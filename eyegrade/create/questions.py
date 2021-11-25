# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2021 Jesus Arias Fisteus
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
    "same_variation_selected_group",
    "The same variation must be selected for questions within the same group.",
)

utils.EyegradeException.register_error(
    "variation_index_out_of_range", "A variation index out of range was specified."
)


class ExamQuestions:
    questions: "QuestionsContainer"
    subject: Optional[str]
    degree: Optional[str]
    title: Optional[str]
    date: Optional[str]
    duration: Optional[str]
    student_id_label: Optional[str]
    shuffled_groups: Dict[str, List["QuestionsGroup"]]
    shuffled_questions: Dict[str, List["Question"]]
    permutations: Dict[str, List[int]]
    scores: Optional[Union["scoring.QuestionScores", "scoring.AutomaticScore"]]
    _student_id_length: int

    def __init__(self):
        self.questions = QuestionsContainer()
        self.subject = None
        self.degree = None
        self.title = None
        self.date = None
        self.duration = None
        self.student_id_label = None
        self._student_id_length = None
        self.shuffled_groups = {}
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

    def shuffle(self, model: str, variation: Optional[int] = None) -> None:
        """Shuffles questions and options within questions for the given model."""
        shuffled_groups, shuffled_questions, permutations = self.questions.shuffle()
        self.shuffled_groups[model] = shuffled_groups
        self.shuffled_questions[model] = shuffled_questions
        self.permutations[model] = permutations
        if variation is None:
            self._shuffle_variations(model)
        else:
            self.select_variation(model, variation)
        for question in self.questions:
            question.shuffle(model)

    def _shuffle_variations(self, model: str) -> None:
        """Chooses a variation for each question randomly."""
        self.questions.shuffle_variations(model)

    def select_variations(self, model: str, variations: List[int]) -> None:
        if self.shuffled_groups is None:
            raise ValueError("Permutations muct be set before variations")
        for question, variation in zip(self.shuffled_questions[model], variations):
            question.select_variation(model, variation)
        # Select variations for groups also:
        i = 0
        for group in self.shuffled_groups[model]:
            group.select_variation(model, variations[i])
            i += len(group)
        self.questions.check_variations(model)

    def select_variation(self, model: str, variation: int) -> None:
        self.select_variations(model, [variation] * self.num_questions())

    def selected_variations(self, model: str) -> List[int]:
        return [
            question.selected_variation[model]
            for question in self.shuffled_questions[model]
        ]

    def selected_variation(self, model: str) -> Optional[int]:
        variations = []
        for question in self.shuffled_questions[model]:
            if len(question.variations) > 1:
                variations.append(question.selected_variation[model])
        if variations and min(variations) == max(variations):
            return variations[0]
        else:
            return None

    def set_permutation(
        self, model: str, permutations: List[Tuple[int, List[int]]]
    ) -> None:
        self.permutations[model] = [p[0] - 1 for p in permutations]
        self.shuffled_questions[model] = [
            self.questions[i] for i in self.permutations[model]
        ]
        self.shuffled_groups[model] = self._group_order(self.permutations[model])
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

    def _group_order(self, permutations: List[int]) -> List["QuestionsGroup"]:
        """Computes group order from a permutations list."""
        group_for_question = {}
        i = 0
        for group in self.questions.groups:
            group_for_question[i] = group
            i += len(group)
        shuffled_groups = []
        for question in permutations:
            if question in group_for_question:
                shuffled_groups.append(group_for_question[question])
        return shuffled_groups


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

    def shuffle(self) -> Tuple[List["QuestionsGroup"], List["Question"], List[int]]:
        """Returns a tuple (list of questions, permutations) with data shuffled.

        Permutations is another list with the original position of each
        question. That is, question shuffled[i] was in the original list in
        permutations[i] position.

        It returns just a list of questions, without groupings.

        """
        to_sort = [(random.random(), item) for item in self.groups]
        groups = []
        questions = []
        permutations = []
        for _, group in sorted(to_sort):
            groups.append(group)
            questions.extend(group.questions)
            permutations.extend(self._positions(group))
        return groups, questions, permutations

    def shuffle_variations(self, model: str) -> None:
        """Chooses a variation for each question randomly.

        Variations are chosen group by group:
        the same variation is chosen for all the questions of each group.

        """
        for group in self.groups:
            group.shuffle_variations(model)

    def check_variations(self, model: str) -> None:
        for group in self.groups:
            variations = [
                question.selected_variation[model] for question in group.questions
            ]
            if min(variations) < max(variations):
                raise utils.EyegradeException("", key="same_variation_selected_group")

    def _iterate_questions(self) -> Iterator["Question"]:
        for group in self.groups:
            for question in group:
                yield question

    def _positions(self, group: "QuestionsGroup") -> List[int]:
        pos = 0
        for other_group in self.groups:
            if other_group is group:
                return list(range(pos, pos + len(other_group)))
            pos += len(other_group)
        raise ValueError("Group not in group container")


class QuestionsGroup:
    questions: List["Question"]
    common_text: Optional["GroupCommonComponent"]

    def __init__(
        self,
        questions: List["Question"],
        common_text: Optional["GroupCommonComponent"] = None,
    ):
        if not questions:
            raise ValueError("Empty QuestionsGroup are not allowed")
        self.questions = questions
        self.common_text = common_text
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

    def get_common_text(self, model: str) -> Optional["QuestionComponent"]:
        if self.common_text is not None:
            return self.common_text.component(model)
        return None

    def shuffle_variations(self, model: str) -> None:
        """Chooses a variation for this group randomly.

        All questions get the same variation.

        """
        self.select_variation(model, random.randrange(self.num_variations))

    def select_variation(self, model: str, variation: int) -> None:
        for question in self.questions:
            question.select_variation(model, variation)
        if self.common_text is not None:
            self.common_text.select_variation(model, variation)

    def __str__(self):
        return (
            f"<QuestionGroup: {len(self)} questions, {self.num_variations} variations>"
        )

    def _check_number_variations(self) -> None:
        num_variations_per_question = [
            question.num_variations for question in self.questions
        ]
        num_variations = min(num_variations_per_question)
        if num_variations < max(num_variations_per_question):
            raise utils.EyegradeException("", key="incompatible_variation_num_group")
        if self.common_text is not None:
            num_common_text_variations = self.common_text.num_variations
            if (
                num_common_text_variations > 1
                and num_common_text_variations != num_variations
            ):
                raise utils.EyegradeException(
                    "", key="incompatible_variation_num_group"
                )


class GroupCommonComponent:
    variations: List["QuestionComponent"]
    selected_variation: Dict[str, int]

    def __init__(self):
        self.variations = []
        self.selected_variation = {}

    @property
    def num_variations(self) -> int:
        return len(self.variations)

    def component(self, model: str) -> "QuestionComponent":
        return self.variations[self.selected_variation[model]]

    def add_variation(self, variation: "QuestionComponent") -> None:
        self.variations.append(variation)

    def select_variation(self, model: str, index: int) -> None:
        if index < 0:
            raise utils.EyegradeException(
                f"Variations: expected a value between 1 and {self.num_variations}, got {index + 1}",
                key="variation_index_out_of_range",
            )
        if index >= len(self.variations):
            if len(self.variations) == 1:
                index = 0
            else:
                raise utils.EyegradeException(
                    f"Variations: expected a value between 1 and {self.num_variations}, got {index + 1}",
                    key="variation_index_out_of_range",
                )
        self.selected_variation[model] = index


class FixedGroupCommonComponent(GroupCommonComponent):
    def __init__(self, common_component: "QuestionComponent"):
        super().__init__()
        self.add_variation(common_component)

    def component(self, model: str) -> "QuestionComponent":
        return self.variations[0]

    def add_variation(self, variation: "QuestionComponent") -> None:
        if self.variations:
            raise ValueError("Just one variation allowed in FixedGroupCommonComponent")
        super().add_variation(variation)


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
        if model == "0":
            return self.choices(model)
        return self.variations[self.selected_variation[model]].shuffled_choices(
            self.permutations[model]
        )

    def choices(self, model: str) -> List["QuestionComponent"]:
        return self.variations[self.selected_variation[model]].choices()

    def correct_choices(self, model: str) -> List["QuestionComponent"]:
        return self.variations[self.selected_variation[model]].correct_choices

    def add_variation(self, variation: "QuestionVariation") -> None:
        if self.variations and not self.variations[0].is_compatible(variation):
            raise utils.EyegradeException("", key="incompatible_variation")
        self.variations.append(variation)

    def shuffle(self, model: str) -> None:
        if not self.variations:
            raise ValueError("Cannot shuffle without at least one variation")
        self.permutations[model] = self.variations[0].shuffle()

    def select_variation(self, model: str, index: int) -> None:
        if index < 0:
            raise utils.EyegradeException(
                f"Variations: expected a value between 1 and {self.num_variations}, got {index + 1}",
                key="variation_index_out_of_range",
            )
        if index >= len(self.variations):
            if len(self.variations) == 1:
                index = 0
            else:
                raise utils.EyegradeException(
                    f"Variations: expected a value between 1 and {self.num_variations}, got {index + 1}",
                    key="variation_index_out_of_range",
                )
        self.selected_variation[model] = index


class FixedQuestion(Question):
    """ A question without variations, i.e. just one variation."""

    def __init__(self, variation: "QuestionVariation"):
        super().__init__()
        self.add_variation(variation)

    def text(self, model: str) -> "QuestionComponent":
        return self.variations[0].text

    def shuffled_choices(self, model: str) -> List["QuestionComponent"]:
        if model == "0":
            return self.choices(model)
        return self.variations[0].shuffled_choices(self.permutations[model])

    def choices(self, model: str) -> List["QuestionComponent"]:
        return self.variations[0].choices()

    def correct_choices(self, model: str) -> List["QuestionComponent"]:
        return self.variations[0].correct_choices

    def add_variation(self, variation: "QuestionVariation") -> None:
        if self.variations:
            raise ValueError("Just one variation allowed in FixedQuestion")
        super().add_variation(variation)


class QuestionVariation:
    text: "QuestionComponent"
    correct_choices: List["QuestionComponent"]
    incorrect_choices: List["QuestionComponent"]
    fix_first: List[int]
    fix_last: List[int]

    def __init__(
        self,
        text: "QuestionComponent",
        correct_choices: List["QuestionComponent"],
        incorrect_choices: List["QuestionComponent"],
        fix_first: List[int],
        fix_last: List[int],
    ):
        self.text = text
        self.correct_choices = correct_choices
        self.incorrect_choices = incorrect_choices
        self.fix_first = fix_first
        self.fix_last = fix_last

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
            and self.fix_first == other.fix_first
            and self.fix_last == other.fix_last
        )

    def shuffled_choices(self, permutation: List[int]) -> List["QuestionComponent"]:
        choices = self.correct_choices + self.incorrect_choices
        return [choices[i] for i in permutation]

    def choices(self) -> List["QuestionComponent"]:
        return self.correct_choices + self.incorrect_choices

    def shuffle(self) -> List[int]:
        to_sort = [(random.random(), pos) for pos in range(self.num_choices)]
        for pos in self.fix_first:
            # They will always be first when sorted
            to_sort[pos] = (-1.0, pos)
        for pos in self.fix_last:
            # They will always be last when sorted
            to_sort[pos] = (2.0, pos)
        permutations = []
        for _, pos in sorted(to_sort):
            permutations.append(pos)
        return permutations


class QuestionComponent:
    """A piece of text and optional figure or code.

       Represents both the text of a question and its choices.

    """

    in_choice: bool
    text: Optional[Union[str, List[Tuple[str, str]]]]
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
