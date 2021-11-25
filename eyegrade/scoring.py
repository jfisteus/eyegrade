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

from . import utils


class QuestionScores(utils.ComparableMixin):
    """Compute the score of a question."""

    CORRECT = 1
    INCORRECT = 2
    BLANK = 3
    VOID = 4

    def __init__(self, correct_score, incorrect_score, blank_score, weight=1):
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

    def score(self, answer_type):
        if answer_type == QuestionScores.CORRECT:
            return self.weight * self.correct_score
        elif answer_type == QuestionScores.INCORRECT:
            return -self.weight * self.incorrect_score
        elif answer_type == QuestionScores.BLANK:
            return -self.weight * self.blank_score
        elif answer_type == QuestionScores.VOID:
            return 0
        else:
            raise Exception("Bad answer_type value in QuestionScore")

    def format_all(self):
        data = (
            self._format_score(self.correct_score),
            self._format_score(self.incorrect_score),
            self._format_score(self.blank_score),
        )
        return ";".join(data)

    def format_weight(self):
        return self._format_score(self.weight)

    def format_score(self, answer_type, signed=False):
        if answer_type == QuestionScores.CORRECT:
            return self._format_score(self.correct_score, signed=False)
        elif answer_type == QuestionScores.INCORRECT:
            return self._format_score(self.incorrect_score, signed=signed)
        elif answer_type == QuestionScores.BLANK:
            return self._format_score(self.blank_score, signed=signed)
        else:
            raise ValueError("Bad answer_type value in QuestionScore")

    def format_correct_score(self, signed=False):
        return self._format_score(self.correct_score, signed=False)

    def format_incorrect_score(self, signed=False):
        return self._format_score(self.incorrect_score, signed=signed)

    def format_blank_score(self, signed=False):
        return self._format_score(self.blank_score, signed=signed)

    def clone(self, new_weight=None):
        if new_weight is not None:
            weight = new_weight
        else:
            weight = self.weight
        return QuestionScores(
            self.correct_score, self.incorrect_score, self.blank_score, weight=weight
        )

    def __str__(self):
        return "({0}) * {1}".format(self.format_all(), self.format_weight())

    def _parse_score(self, score_str, invert_negatives=False):
        score = parse_number(score_str, allow_negatives=invert_negatives)
        if score < 0:
            score = -score
        return score

    def _parse_weight(self, score_str):
        score = parse_number(score_str)
        if score < 0:
            raise ValueError("Negative weights are forbidden: {}".format(score_str))
        return score

    def _format_score(self, score, signed=False):
        if signed:
            score = -score
        return format_number(score)

    def _cmpkey(self):
        return (self.correct_score, self.incorrect_score, self.blank_score, self.weight)


class Score:
    def __init__(self, answers, solutions, question_scores):
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
        if answers and solutions:
            self.update()

    def update(self):
        self.correct = 0
        self.incorrect = 0
        self.blank = 0
        self.answer_status = []
        question_scores = self.question_scores
        if question_scores is None:
            question_scores = [None] * len(self.answers)
            has_scores = False
        else:
            has_scores = True
        for answer, solution, q in zip(self.answers, self.solutions, question_scores):
            if q is not None and q.weight == 0:
                self.answer_status.append(QuestionScores.VOID)
            elif answer == 0:
                self.blank += 1
                self.answer_status.append(QuestionScores.BLANK)
            elif answer in solution:
                self.correct += 1
                self.answer_status.append(QuestionScores.CORRECT)
            else:
                self.incorrect += 1
                self.answer_status.append(QuestionScores.INCORRECT)
        if has_scores:
            self.score = float(
                sum(
                    [
                        q.score(status)
                        for q, status in zip(question_scores, self.answer_status)
                    ]
                )
            )
            self.max_score = float(
                sum([q.score(QuestionScores.CORRECT) for q in self.question_scores])
            )
        else:
            self.score = None
            self.max_score = None


class AutomaticScore:
    def __init__(self, max_score, penalize):
        if isinstance(max_score, str):
            self.max_score = parse_number(max_score)
        else:
            self.max_score = max_score
        self.penalize = penalize

    def compute(self, num_questions, num_choices):
        correct_score = self.max_score / num_questions
        if self.penalize:
            incorrect_score = self.max_score / (num_choices - 1) / num_questions
        else:
            incorrect_score = 0
        return QuestionScores(correct_score, incorrect_score, 0)


def format_number(number, short=False, no_fraction=False):
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
        return str(number)


# A score is a float number or a fraction, e.g.: '0.8' or '4/5'
_re_number = re.compile(r"^(-?)\s*((\d+(\.\d+)?)|((\d+)\s*\/\s*(\d+)))\s*$")
# score_re = re.compile(r'^(-?)((\d*(\.\d+))|((\d+)(\/(\d+))?))$')


def parse_number(score_str, force_float=False, allow_negatives=False):
    match = _re_number.match(score_str)
    if match is None:
        raise ValueError("Syntax error in score: " + score_str)
    groups = match.groups()
    sign = -1 if groups[0] else 1
    if sign == -1 and not allow_negatives:
        raise ValueError("The number cannot be negative: " + score_str)
    if groups[2] is not None:
        if groups[3] is not None:
            value = sign * float(groups[2])
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
