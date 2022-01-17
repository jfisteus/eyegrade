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
# <http://www.gnu.org/licenses/>.
#

import unittest
import random

import eyegrade.create.questions as questions


class _FixedQuestion(questions.FixedQuestion):
    def __init__(self, text):
        super().__init__(
            questions.QuestionVariation(
                questions.QuestionComponent(False, text=text), [], [], [], []
            )
        )


class TestQuestionsContainer(unittest.TestCase):
    def test_dunder_methods(self):
        container = questions.QuestionsContainer()
        container.append(_FixedQuestion("A"))
        container.append(
            questions.QuestionsGroup([_FixedQuestion("B"), _FixedQuestion("C")])
        )
        container.append(
            questions.QuestionsGroup(
                [_FixedQuestion("D"), _FixedQuestion("E"), _FixedQuestion("F")]
            )
        )
        container.append(_FixedQuestion("G"))
        self.assertEqual(len(container), 7)
        self.assertEqual(
            _extract_text(iter(container)), ["A", "B", "C", "D", "E", "F", "G"]
        )
        self.assertEqual(
            _extract_text(container[i] for i in range(7)),
            ["A", "B", "C", "D", "E", "F", "G"],
        )

    def test_shuffle(self):
        random.seed(1)
        # the first four calls to random.random() with this seed
        # should return 0.13, 0.85, 0.76, 0.26
        container = questions.QuestionsContainer()
        container.append(_FixedQuestion("A"))
        container.append(
            questions.QuestionsGroup([_FixedQuestion("B"), _FixedQuestion("C")])
        )
        container.append(
            questions.QuestionsGroup(
                [_FixedQuestion("D"), _FixedQuestion("E"), _FixedQuestion("F")]
            )
        )
        container.append(_FixedQuestion("G"))
        _, question_list, permutations = container.shuffle()
        self.assertEqual(
            _extract_text(question_list), ["A", "G", "D", "E", "F", "B", "C"]
        )
        self.assertEqual(permutations, [0, 6, 3, 4, 5, 1, 2])

    def test_positions(self):
        container = questions.QuestionsContainer()
        container.append(_FixedQuestion("A"))
        container.append(
            questions.QuestionsGroup([_FixedQuestion("B"), _FixedQuestion("C")])
        )
        container.append(
            questions.QuestionsGroup(
                [_FixedQuestion("D"), _FixedQuestion("E"), _FixedQuestion("F")]
            )
        )
        container.append(_FixedQuestion("G"))
        # pylint: disable=protected-access
        self.assertEqual(container._positions(container.groups[0]), [0])
        self.assertEqual(container._positions(container.groups[1]), [1, 2])
        self.assertEqual(container._positions(container.groups[2]), [3, 4, 5])
        self.assertEqual(container._positions(container.groups[3]), [6])


def _extract_text(question_list):
    return [question.text("").text for question in question_list]
