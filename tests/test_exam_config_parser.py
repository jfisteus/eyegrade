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
import configparser
import fractions

import eyegrade.exams as exams
import eyegrade.scoring as scoring
import eyegrade.utils as utils


class TestExamConfigParser(unittest.TestCase):
    def test_correct_file(self):
        config_text = """
            [exam]
                dimensions: 3,5
                id-num-digits: 9
                correct-weight: 1
                incorrect-weight: 1/2
                blank-weight: 0

                [solutions]
                model-A: 3/1/2/1/2
                model-B: 1/3/2/2/3
        """
        exam_data = configparser.ConfigParser()
        exam_data.read_string(config_text)
        exam_config = exams.ExamConfig()
        exam_config._read_config_parser(exam_data)
        self.assertEqual(exam_config.solutions["A"], [{3}, {1}, {2}, {1}, {2}])
        self.assertEqual(exam_config.solutions["B"], [{1}, {3}, {2}, {2}, {3}])
        self.assertEqual(exam_config.id_num_digits, 9)
        score = scoring.QuestionScores(1, fractions.Fraction(1, 2), 0)
        for model in ["A", "B"]:
            for i in range(5):
                self.assertEqual(exam_config.scores[model][i], score)
        self.assertEqual(exam_config.dimensions, [(3, 5)])

    def test_solutions_out_of_range(self):
        config_text = """
            [exam]
                dimensions: 3,5
                id-num-digits: 9
                correct-weight: 1
                incorrect-weight: 1/2
                blank-weight: 0

                [solutions]
                model-A: 3/1/4/1/2
                model-B: 1/3/2/2/3
        """
        exam_data = configparser.ConfigParser()
        exam_data.read_string(config_text)
        exam_config = exams.ExamConfig()
        with self.assertRaises(utils.EyegradeException):
            exam_config._read_config_parser(exam_data)
