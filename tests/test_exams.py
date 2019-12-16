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
# <http://www.gnu.org/licenses/>.
#

import unittest
import random

import eyegrade.create.questions as questions


class TestQuestionsContainer(unittest.TestCase):
    def test_dunder_methods(self):
        container = questions.QuestionsContainer()
        container.append("A")
        container.append(questions.QuestionsGroup(["B", "C"]))
        container.append(questions.QuestionsGroup(["D", "E", "F"]))
        container.append("G")
        self.assertEqual(len(container), 7)
        self.assertEqual(list(iter(container)), ["A", "B", "C", "D", "E", "F", "G"])
        self.assertEqual(
            [container[i] for i in range(7)], ["A", "B", "C", "D", "E", "F", "G"]
        )

    def test_shuffle(self):
        random.seed(1)
        # the first four calls to random.random() with this seed
        # should return 0.13, 0.85, 0.76, 0.26
        container = questions.QuestionsContainer()
        container.append("A")
        container.append(questions.QuestionsGroup(["B", "C"]))
        container.append(questions.QuestionsGroup(["D", "E", "F"]))
        container.append("G")
        question_list, permutations = container.shuffle()
        self.assertEqual(question_list, ["A", "G", "D", "E", "F", "B", "C"])
        self.assertEqual(permutations, [0, 6, 3, 4, 5, 1, 2])

    def test_positions(self):
        container = questions.QuestionsContainer()
        container.append("A")
        container.append(questions.QuestionsGroup(["B", "C"]))
        container.append(questions.QuestionsGroup(["D", "E", "F"]))
        container.append("G")
        self.assertEqual(container._positions(container.groups[0]), [0])
        self.assertEqual(container._positions(container.groups[1]), [1, 2])
        self.assertEqual(container._positions(container.groups[2]), [3, 4, 5])
        self.assertEqual(container._positions(container.groups[3]), [6])
