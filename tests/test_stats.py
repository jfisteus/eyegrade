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

import unittest

import eyegrade.stats.core as core


class TestQuestionStats(unittest.TestCase):
    def testQuestionStatsWithPermutations(self):
        permutations = core.ChoicePermutations(
            num_choices=4,
            reference_model="0",
            choice_permutations={
                "A": [1, 4, 2, 3],
                "B": [3, 2, 4, 1],
            },
        )
        answers = [
            ("A", 1),
            ("B", 3),
            ("A", 0),
            ("B", 3),
            ("B", 2),
            ("A", 2),
        ]
        correct_choices = {
            "0": [4],
        }
        stats = core.QuestionStats(4, correct_choices, permutations)
        for model, answer in answers:
            stats.count_answer(answer, model)
        self.assertEqual(stats.get_answer_counts("0"), [1, 1, 1, 0, 3])
        self.assertEqual(stats.get_answer_counts("A"), [1, 1, 3, 1, 0])
        self.assertEqual(stats.get_answer_counts("B"), [1, 0, 1, 3, 1])

    def testQuestionStatsWithoutPermutations(self):
        answers = [
            ("A", 1),
            ("B", 3),
            ("A", 0),
            ("B", 3),
            ("B", 2),
            ("A", 2),
        ]
        correct_choices = {
            "A": [3],
            "B": [2],
        }
        stats = core.QuestionStats(4, correct_choices, None)
        for model, answer in answers:
            stats.count_answer(answer, model)
        self.assertEqual(stats.get_answer_counts("A"), [1, 1, 1, 0, 0])
        self.assertEqual(stats.get_answer_counts("B"), [0, 0, 1, 2, 0])


class TestExamStats(unittest.TestCase):
    def testExamStatsWithPermutations(self):
        permutations = core.ExamPermutations(
            num_questions=4,
            num_choices=3,
            reference_model="0",
            exam_permutations={
                "A": [
                    (1, [1, 2, 3]),
                    (4, [3, 2, 1]),
                    (3, [2, 1, 3]),
                    (2, [3, 1, 2]),
                ],
                "B": [
                    (2, [1, 3, 2]),
                    (3, [2, 3, 1]),
                    (4, [1, 2, 3]),
                    (1, [3, 2, 1]),
                ],
            },
        )
        answers = [
            ("A", [1, 3, 2, 0]),
            ("B", [1, 2, 1, 3]),
            ("A", [2, 2, 2, 1]),
            ("B", [3, 0, 1, 1]),
            ("B", [1, 2, 1, 1]),
            ("A", [1, 3, 2, 3]),
        ]
        correct_choices = {
            "0": [[1], [3], [2], [3]],
        }
        stats = core.ExamStats(4, 3, correct_choices, permutations)
        for model, answers in answers:
            stats.count_answers(answers, model)
        self.assertEqual(
            stats.get_answer_counts("0"),
            [
                [0, 3, 1, 2],
                [1, 2, 2, 1],
                [1, 3, 0, 2],
                [0, 5, 1, 0],
            ],
        )

    def testExamStatsWithoutPermutations(self):
        answers = [
            ("A", [1, 3, 2, 0]),
            ("B", [1, 2, 1, 3]),
            ("A", [2, 2, 2, 1]),
            ("B", [3, 0, 1, 1]),
            ("B", [1, 2, 1, 1]),
            ("A", [1, 3, 2, 3]),
        ]
        correct_choices = {
            "A": [[1], [3], [2], [3]],
            "B": [[2], [1], [1], [3]],
        }
        stats = core.ExamStats(4, 3, correct_choices, None)
        for model, answers in answers:
            stats.count_answers(answers, model)
        self.assertEqual(
            stats.get_answer_counts("A"),
            [
                [0, 2, 1, 0],
                [0, 0, 1, 2],
                [0, 0, 3, 0],
                [1, 1, 0, 1],
            ],
        )
        self.assertEqual(
            stats.get_answer_counts("B"),
            [
                [0, 2, 0, 1],
                [1, 0, 2, 0],
                [0, 3, 0, 0],
                [0, 2, 0, 1],
            ],
        )
