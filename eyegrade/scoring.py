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

import fractions
import re
import decimal
import enum

from typing import Union, Optional, Sequence

from . import utils


class AnswerStatus(enum.Enum):
    CORRECT = 1
    INCORRECT = 2
    BLANK = 3
    VOID = 4


class QuestionScores(utils.ComparableMixin):
    """Compute the score of a question."""

    correct_score: Union[int, float, decimal.Decimal, fractions.Fraction]
    incorrect_score: Union[int, float, decimal.Decimal, fractions.Fraction]
    blank_score: Union[int, float, decimal.Decimal, fractions.Fraction]
    weight: Union[int, float, decimal.Decimal, fractions.Fraction]
    _correct_score_internal: Union[int, float, fractions.Fraction]
    _incorrect_score_internal: Union[int, float, fractions.Fraction]
    _blank_score_internal: Union[int, float, fractions.Fraction]
    _weight_internal: Union[int, float, fractions.Fraction]

    def __init__(
        self,
        correct_score: Union[str, int, float, decimal.Decimal, fractions.Fraction],
        incorrect_score: Union[str, int, float, decimal.Decimal, fractions.Fraction],
        blank_score: Union[str, int, float, decimal.Decimal, fractions.Fraction],
        weight: Union[str, int, float, decimal.Decimal, fractions.Fraction] = 1,
    ):
        if isinstance(correct_score, str):
            self.correct_score = self._parse_score(correct_score)
        else:
            self.correct_score = correct_score
        if isinstance(incorrect_score, str):
            self.incorrect_score = self._parse_score(
                incorrect_score, invert_negatives=True
            )
        else:
            self.incorrect_score = incorrect_score
        if isinstance(blank_score, str):
            self.blank_score = self._parse_score(blank_score, invert_negatives=True)
        else:
            self.blank_score = blank_score
        if isinstance(weight, str):
            self.weight = self._parse_weight(weight)
        else:
            self.weight = weight
        self._correct_score_internal = _value_for_computations(self.correct_score)
        self._incorrect_score_internal = _value_for_computations(self.incorrect_score)
        self._blank_score_internal = _value_for_computations(self.blank_score)
        self._weight_internal = _value_for_computations(self.weight)

    def score(self, answer_type: AnswerStatus) -> Union[int, float, fractions.Fraction]:
        if answer_type == AnswerStatus.CORRECT:
            return self._weight_internal * self._correct_score_internal
        elif answer_type == AnswerStatus.INCORRECT:
            return -self._weight_internal * self._incorrect_score_internal
        elif answer_type == AnswerStatus.BLANK:
            return -self._weight_internal * self._blank_score_internal
        elif answer_type == AnswerStatus.VOID:
            return 0
        else:
            raise Exception("Bad answer_type value in QuestionScore")

    def format_all(self) -> str:
        data = (
            self._format_score(self.correct_score),
            self._format_score(self.incorrect_score),
            self._format_score(self.blank_score),
        )
        return ";".join(data)

    def format_weight(self) -> str:
        return self._format_score(self.weight)

    def format_score(self, answer_type: AnswerStatus, signed: bool = False) -> str:
        if answer_type == AnswerStatus.CORRECT:
            return self._format_score(self.correct_score, signed=False)
        elif answer_type == AnswerStatus.INCORRECT:
            return self._format_score(self.incorrect_score, signed=signed)
        elif answer_type == AnswerStatus.BLANK:
            return self._format_score(self.blank_score, signed=signed)
        else:
            raise ValueError("Bad answer_type value in QuestionScore")

    def format_correct_score(self, signed: bool = False):
        return self._format_score(self.correct_score, signed=False)

    def format_incorrect_score(self, signed: bool = False):
        return self._format_score(self.incorrect_score, signed=signed)

    def format_blank_score(self, signed: bool = False):
        return self._format_score(self.blank_score, signed=signed)

    def clone(
        self,
        new_weight: Union[int, float, decimal.Decimal, fractions.Fraction, None] = None,
    ) -> "QuestionScores":
        if new_weight is not None:
            weight = new_weight
        else:
            weight = self.weight
        return QuestionScores(
            self.correct_score, self.incorrect_score, self.blank_score, weight=weight
        )

    def __str__(self) -> str:
        return "({0}) * {1}".format(self.format_all(), self.format_weight())

    def _parse_score(
        self, score_str, invert_negatives=False
    ) -> Union[int, float, decimal.Decimal, fractions.Fraction]:
        score = parse_number(score_str, allow_negatives=invert_negatives)
        if score < 0:
            score = -score
        return score

    def _parse_weight(
        self, score_str: str
    ) -> Union[int, float, decimal.Decimal, fractions.Fraction]:
        score = parse_number(score_str)
        if score < 0:
            raise ValueError("Negative weights are forbidden: {}".format(score_str))
        return score

    def _format_score(
        self,
        score: Union[int, float, decimal.Decimal, fractions.Fraction],
        signed: bool = False,
    ):
        if signed:
            score = -score
        return format_number(score)

    def _cmpkey(self) -> tuple:
        return (self.correct_score, self.incorrect_score, self.blank_score, self.weight)


class Score:
    correct: Optional[int]
    incorrect: Optional[int]
    blank: Optional[int]
    score: Optional[float]
    max_score: Optional[float]
    answer_status: Optional[list[AnswerStatus]]
    answers: Optional[list[int]]
    solutions: Optional[list[set[int]]]
    question_scores: Optional[list[QuestionScores]]

    def __init__(
        self,
        answers: Optional[list[int]],
        solutions: Optional[list[set[int]]],
        question_scores: Optional[list[QuestionScores]],
    ) -> None:
        if answers is not None and solutions and len(answers) != len(solutions):
            raise ValueError("Parameters must have the same length in Score")
        if (
            solutions
            and question_scores is not None
            and len(solutions) != len(question_scores)
        ):
            raise ValueError("Parameters must have the same length in Score")
        self.correct = None
        self.incorrect = None
        self.blank = None
        self.score = None
        self.max_score = None
        self.answer_status = None
        self.answers = answers
        self.solutions = solutions
        self.question_scores = question_scores
        self.update()

    def update(self) -> None:
        if not self.answers or not self.solutions:
            return
        self.correct = 0
        self.incorrect = 0
        self.blank = 0
        self.answer_status = []
        internal_scores: Sequence[Optional[QuestionScores]]
        if self.question_scores is not None:
            internal_scores = self.question_scores
        else:
            internal_scores = [None] * len(self.answers)
        for answer, solution, q in zip(self.answers, self.solutions, internal_scores):
            if q is not None and q.weight == 0:
                self.answer_status.append(AnswerStatus.VOID)
            elif answer == 0:
                self.blank += 1
                self.answer_status.append(AnswerStatus.BLANK)
            elif answer in solution:
                self.correct += 1
                self.answer_status.append(AnswerStatus.CORRECT)
            else:
                self.incorrect += 1
                self.answer_status.append(AnswerStatus.INCORRECT)
        if self.question_scores:
            self.score = float(
                sum(
                    [
                        q.score(status)
                        for q, status in zip(self.question_scores, self.answer_status)
                    ]
                )
            )
            self.max_score = float(
                sum([q.score(AnswerStatus.CORRECT) for q in self.question_scores])
            )
        else:
            self.score = None
            self.max_score = None

    def update_question_scores(self, question_scores: list[QuestionScores]) -> None:
        self.question_scores = question_scores
        self.update()


class AutomaticScore:
    max_score: Union[int, float, decimal.Decimal, fractions.Fraction]
    penalize: bool

    def __init__(
        self,
        max_score: Union[str, int, float, decimal.Decimal, fractions.Fraction],
        penalize: bool,
    ) -> None:
        if isinstance(max_score, str):
            self.max_score = parse_number(max_score)
        else:
            self.max_score = max_score
        self.penalize = penalize

    def compute(self, num_questions: int, num_choices: Optional[int]) -> QuestionScores:
        correct_score = self.max_score / num_questions
        if self.penalize:
            if num_choices is not None:
                incorrect_score = self.max_score / (num_choices - 1) / num_questions
            else:
                raise ValueError(
                    "num_choices must be provided when penalizing (null received)"
                )
        else:
            incorrect_score = 0
        return QuestionScores(correct_score, incorrect_score, 0)


def format_number(
    number: Union[int, float, decimal.Decimal, fractions.Fraction, None],
    short: bool = False,
    no_fraction: bool = False,
) -> Union[str, None]:
    if number is None:
        return None
    elif no_fraction and type(number) == fractions.Fraction:
        if number.denominator != 1:
            number = float(number)
    if type(number) == fractions.Fraction:
        if number.denominator != 1:
            return "{0}/{1}".format(number.numerator, number.denominator)
        else:
            return str(number.numerator)
    elif type(number) == float:
        if short:
            return "{0:.2f}".format(number)
        else:
            return "{0:.16f}".format(number)
    else:
        # e.g. decimal.Decimal or int
        return str(number)


# A score is a decimal.Decimal, float or a fraction, e.g.: '0.8' or '4/5'
_re_number = re.compile(r"^(-?)\s*((\d+(\.\d+)?)|((\d+)\s*\/\s*(\d+)))\s*$")
# score_re = re.compile(r'^(-?)((\d*(\.\d+))|((\d+)(\/(\d+))?))$')


def parse_number(
    score_str: str, force_float: bool = False, allow_negatives: bool = False
) -> Union[int, float, decimal.Decimal, fractions.Fraction]:
    value: Union[int, float, decimal.Decimal, fractions.Fraction]
    match = _re_number.match(score_str)
    if match is None:
        raise ValueError("Syntax error in score: " + score_str)
    groups = match.groups()
    sign = -1 if groups[0] else 1
    if sign == -1 and not allow_negatives:
        raise ValueError("The number cannot be negative: " + score_str)
    if groups[2] is not None:
        if groups[3] is not None:
            if force_float:
                value = sign * float(groups[2])
            else:
                value = sign * decimal.Decimal(groups[2])
            numerator = None
        else:
            numerator = int(groups[2])
            denominator = 1
    else:
        numerator = int(groups[5])
        denominator = int(groups[6])
    if numerator is not None:
        value = fractions.Fraction(sign * numerator, denominator)
        if force_float:
            value = float(value)
    return value


def _value_for_computations(
    value: Union[int, float, decimal.Decimal, fractions.Fraction],
) -> Union[int, float, fractions.Fraction]:
    if isinstance(value, decimal.Decimal):
        return fractions.Fraction(value)
    else:
        return value
