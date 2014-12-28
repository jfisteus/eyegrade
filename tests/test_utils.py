# -*- coding: utf-8 -*-

# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2014 Jesus Arias Fisteus
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
from __future__ import unicode_literals

import unittest
import StringIO
import fractions

import eyegrade.utils as utils

class TestStudent(unittest.TestCase):

    def test_full_name(self):
        student = utils.Student(1, '0000', 'John Doe', None, None,
                                'john@example.com', 2, 3)
        self.assertEqual(student.name, 'John Doe')
        self.assertEqual(student.id_and_name, '0000 John Doe')
        self.assertEqual(student.name_or_id, 'John Doe')

    def test_first_and_last_name(self):
        student = utils.Student(1, '0000', None, 'John', 'Doe',
                                'john@example.com', 2, 3)
        self.assertEqual(student.name, 'John Doe')
        self.assertEqual(student.id_and_name, '0000 John Doe')
        self.assertEqual(student.name_or_id, 'John Doe')
        self.assertEqual(student.last_comma_first_name, 'Doe, John')

    def test_last_name(self):
        student = utils.Student(1, '0000', None, None, 'Doe',
                                'doe@example.com', 2, 3)
        self.assertEqual(student.name, 'Doe')
        self.assertEqual(student.id_and_name, '0000 Doe')
        self.assertEqual(student.name_or_id, 'Doe')
        self.assertEqual(student.last_comma_first_name, 'Doe')

    def test_first_name(self):
        student = utils.Student(1, '0000', None, 'John', '',
                                'john@example.com', 2, 3)
        self.assertEqual(student.name, 'John')
        self.assertEqual(student.id_and_name, '0000 John')
        self.assertEqual(student.name_or_id, 'John')
        self.assertEqual(student.last_comma_first_name, 'John')

    def test_no_name(self):
        student = utils.Student(1, '0000', None, None, None,
                                'doe@example.com', 2, 3)
        self.assertEqual(student.name, '')
        self.assertEqual(student.id_and_name, '0000')
        self.assertEqual(student.name_or_id, '0000')
        self.assertEqual(student.last_comma_first_name, '')

    def test_name_errors(self):
        self.assertRaises(ValueError, utils.Student,
                          1, '0000', 'John Doe', 'John', '',
                          'doe@example.com', 2, 3)
        self.assertRaises(ValueError, utils.Student,
                          1, '0000', 'John Doe', '', 'Doe',
                          'doe@example.com', 2, 3)
        self.assertRaises(ValueError, utils.Student,
                          1, '0000', 'John Doe', 'John', 'Doe',
                          'doe@example.com', 2, 3)


class TestReadStudentsFromFile(unittest.TestCase):

    def setUp(self):
        self.students = [
            ('101010101', 'Donald Duck', 'Donald', 'Duck', 'duck@d.com'),
            ('202020202', 'Marty McFly', 'Marty', 'McFly', 'fly@d.com'),
            ('313131313', 'Peter Pan', 'Peter', 'Pan', 'pan@pan.com'),
        ]
        self.bad_students = [
            ('1010a0101', 'Bad Boy', 'Bad', 'Boy', 'boy@bad.com'),
        ]
        self.non_ascii_students = [
            ('404040404', 'Rey León', 'Rey', 'León', 'lion@jungle.com'),
        ]

    def test_empty(self):
        text = ''
        f = StringIO.StringIO(text.encode('utf-8'))
        data = utils.read_student_ids_same_order(file_=f)
        self.assertEqual(data, [])

    def test_read_id(self):
        text = '\n'.join([s[0] for s in self.students])
        f = StringIO.StringIO(text.encode('utf-8'))
        data = utils.read_student_ids_same_order(file_=f)
        key = [(s[0], '', '', '', '') for s in self.students]
        self.assertEqual(data, key)

    def test_read_id_full_name(self):
        text = '\n'.join(['\t'.join((s[0], s[1])) \
                          for s in self.students])
        f = StringIO.StringIO(text.encode('utf-8'))
        data = utils.read_student_ids_same_order(file_=f)
        key = [(s[0], s[1], '', '', '') for s in self.students]
        self.assertEqual(data, key)

    def test_read_id_full_name_email(self):
        text = '\n'.join(['\t'.join((s[0], s[1], s[4])) \
                          for s in self.students])
        f = StringIO.StringIO(text.encode('utf-8'))
        data = utils.read_student_ids_same_order(file_=f)
        key = [(s[0], s[1], '', '', s[4]) for s in self.students]
        self.assertEqual(data, key)

    def test_read_id_name_surname(self):
        text = '\n'.join(['\t'.join((s[0], s[2], s[3])) \
                          for s in self.students])
        f = StringIO.StringIO(text.encode('utf-8'))
        data = utils.read_student_ids_same_order(file_=f)
        key = [(s[0], '', s[2], s[3], '') for s in self.students]
        self.assertEqual(data, key)

    def test_read_id_name_surname_email(self):
        text = '\n'.join(['\t'.join((s[0], s[2], s[3], s[4])) \
                          for s in self.students])
        f = StringIO.StringIO(text.encode('utf-8'))
        data = utils.read_student_ids_same_order(file_=f)
        key = [(s[0], '', s[2], s[3], s[4]) for s in self.students]
        self.assertEqual(data, key)

    def test_errors(self):
        text = '\n'
        f = StringIO.StringIO(text.encode('utf-8'))
        self.assertRaises(utils.EyegradeException,
                          utils.read_student_ids_same_order,
                          file_=f)
        text = '\n'.join(['\t'.join((s[0], s[1], s[4])) \
                          for s in self.students + self.bad_students])
        f = StringIO.StringIO(text)
        self.assertRaises(utils.EyegradeException,
                          utils.read_student_ids_same_order,
                          file_=f)

    def test_non_ascii(self):
        text = '\n'.join(['\t'.join((s[0], s[2], s[3], s[4])) \
                          for s in self.students + self.non_ascii_students])
        f = StringIO.StringIO(text.encode('utf-8'))
        data = utils.read_student_ids_same_order(file_=f)
        key = [(s[0], '', s[2], s[3], s[4]) \
               for s in self.students + self.non_ascii_students]
        self.assertEqual(data, key)


class TestQuestionScores(unittest.TestCase):

    def testFloat(self):
        score = utils.QuestionScores(1.0, 0.5, 0.0)
        key_1 = '1.0000000000000000'
        key_2 = '0.5000000000000000'
        key_3 = '0.0000000000000000'
        self.assertEqual(score.format_all(), ';'.join((key_1, key_2, key_3)))
        self.assertEqual(score.format_score(utils.QuestionScores.CORRECT),
                         key_1)
        self.assertEqual(score.format_score(utils.QuestionScores.INCORRECT),
                         key_2)
        self.assertEqual(score.format_score(utils.QuestionScores.BLANK),
                         key_3)
        self.assertEqual(score.score(utils.QuestionScores.CORRECT), 1.0)
        self.assertEqual(score.score(utils.QuestionScores.INCORRECT), -0.5)
        self.assertEqual(score.score(utils.QuestionScores.BLANK), 0.0)
        self.assertEqual(score.format_weight(), '1')

    def testFractionAndInt(self):
        score = utils.QuestionScores('1', '1/3', '0')
        self.assertEqual(score.format_all(), '1;1/3;0')
        self.assertEqual(score.format_score(utils.QuestionScores.CORRECT),
                         '1')
        self.assertEqual(score.format_score(utils.QuestionScores.INCORRECT),
                         '1/3')
        self.assertEqual(score.format_score(utils.QuestionScores.BLANK),
                         '0')
        self.assertEqual(score.score(utils.QuestionScores.CORRECT), 1)
        self.assertEqual(score.score(utils.QuestionScores.INCORRECT),
                         fractions.Fraction(-1, 3))
        self.assertEqual(score.score(utils.QuestionScores.BLANK), 0)
        self.assertEqual(score.format_weight(), '1')

    def testSignedFormat(self):
        score = utils.QuestionScores('1', '1/3', '1/6')
        result = score.format_score(utils.QuestionScores.CORRECT, signed=True)
        self.assertEqual(result, '1')
        result = score.format_score(utils.QuestionScores.INCORRECT, signed=True)
        self.assertEqual(result, '-1/3')
        result = score.format_score(utils.QuestionScores.BLANK, signed=True)
        self.assertEqual(result, '-1/6')
        score = utils.QuestionScores('1.0', '0.5', '0.25')
        result = score.format_score(utils.QuestionScores.CORRECT, signed=True)
        self.assertEqual(result, '1.0000000000000000')
        result = score.format_score(utils.QuestionScores.INCORRECT, signed=True)
        self.assertEqual(result, '-0.5000000000000000')
        result = score.format_score(utils.QuestionScores.BLANK, signed=True)
        self.assertEqual(result, '-0.2500000000000000')

    def testWeight(self):
        score = utils.QuestionScores('1', '1/3', '1/6', weight='3/2')
        self.assertEqual(score.format_all(), '3/2;1/2;1/4')
        self.assertEqual(score.format_score(utils.QuestionScores.CORRECT),
                         '1')
        self.assertEqual(score.format_score(utils.QuestionScores.INCORRECT),
                         '1/3')
        self.assertEqual(score.format_score(utils.QuestionScores.BLANK),
                         '1/6')
        self.assertEqual(score.score(utils.QuestionScores.CORRECT),
                         fractions.Fraction(3, 2))
        self.assertEqual(score.score(utils.QuestionScores.INCORRECT),
                         fractions.Fraction(-1, 2))
        self.assertEqual(score.score(utils.QuestionScores.BLANK),
                         fractions.Fraction(-1, 4))
        self.assertEqual(score.format_weight(), '3/2')

    def testBadValues(self):
        self.assertRaises(ValueError, utils.QuestionScores, '1/3', '-1/6', '0')
        self.assertRaises(ValueError, utils.QuestionScores, '1//3', '1/6', '0')
        self.assertRaises(ValueError, utils.QuestionScores, '1', '1a', '0')
        self.assertRaises(ValueError, utils.QuestionScores, '1', '2', '0.z3')

    def testClone(self):
        score1 = utils.QuestionScores('1', '1/3', '1/6', weight='3/2')
        score2 = score1.clone()
        self.assertEqual(score2.correct_score, score1.correct_score)
        self.assertEqual(score2.incorrect_score, score1.incorrect_score)
        self.assertEqual(score2.blank_score, score1.blank_score)
        self.assertEqual(score2.weight, score1.weight)
        score3 = score1.clone(new_weight=2)
        self.assertEqual(score3.correct_score, score1.correct_score)
        self.assertEqual(score3.incorrect_score, score1.incorrect_score)
        self.assertEqual(score3.blank_score, score1.blank_score)
        self.assertEqual(score3.weight, 2)

    def testSort(self):
        scores = [
            utils.QuestionScores('1', '1/3', '0'),
            utils.QuestionScores('2', '2/3', '1/2'),
            utils.QuestionScores('1', '1/3', '0'),
            utils.QuestionScores('2', '2/3', '0'),
            utils.QuestionScores('1/2', '1/6', '0'),
        ]
        sorted_scores = [scores[4], scores[0], scores[2], scores[3], scores[1]]
        self.assertEqual(sorted(scores), sorted_scores)


class TestExamConfigScores(unittest.TestCase):

    def testSetQuestionScores(self):
        exam = utils.ExamConfig()
        exam.num_questions = 5
        scores = [
            utils.QuestionScores('1', '1/3', '0'),
            utils.QuestionScores('2', '2/3', '0'),
            utils.QuestionScores('1', '1/3', '0'),
            utils.QuestionScores('2', '2/3', '0'),
            utils.QuestionScores('1/2', '1/6', '0'),
        ]
        exam.set_question_scores('A', scores)
        exam.set_question_scores('B', [scores[1], scores[2], scores[4],
                                       scores[0], scores[3]])

    def testSetQuestionScoresError(self):
        exam = utils.ExamConfig()
        scores = [
            utils.QuestionScores('1', '1/3', '0'),
            utils.QuestionScores('2', '2/3', '0'),
            utils.QuestionScores('1', '1/3', '0'),
            utils.QuestionScores('2', '2/3', '0'),
            utils.QuestionScores('1/2', '1/6', '0'),
        ]
        self.assertRaises(ValueError, exam.set_question_scores, 'A', scores)
        exam.num_questions = 5
        exam.set_question_scores('A', scores)
        self.assertRaises(ValueError, exam.set_question_scores,
                          'B', [scores[1], scores[1], scores[4],
                                scores[0], scores[3]])

    def testSetEqualScores1(self):
        exam = utils.ExamConfig()
        exam.num_questions = 5
        exam.set_base_scores(utils.QuestionScores('1', '1/2', '0'))
        exam.set_equal_scores('A')
        exam.set_equal_scores('B')
        for scores in exam.scores['A'] + exam.scores['B']:
            self.assertEqual(scores, exam.base_scores)

    def testSetEqualScores2(self):
        exam = utils.ExamConfig()
        exam.num_questions = 5
        exam.models = ['A', 'B']
        exam.set_base_scores(utils.QuestionScores('1', '1/2', '0'),
                             same_weights=True)
        for scores in exam.scores['A'] + exam.scores['B']:
            self.assertEqual(scores, exam.base_scores)

    def testSetBaseScoresError(self):
        exam = utils.ExamConfig()
        scores = utils.QuestionScores('1', '1/2', '0', weight='2')
        self.assertRaises(ValueError, exam.set_base_scores, scores)

    def testSetQuestionWeights(self):
        exam = utils.ExamConfig()
        exam.num_questions = 5
        scores = [
            utils.QuestionScores('1', '1/2', '0', weight='1'),
            utils.QuestionScores('1', '1/2', '0', weight='2'),
            utils.QuestionScores('1', '1/2', '0', weight='1'),
            utils.QuestionScores('1', '1/2', '0', weight='2'),
            utils.QuestionScores('1', '1/2', '0', weight='1/2'),
            utils.QuestionScores('1', '1/2', '0', weight='1'),
            utils.QuestionScores('1', '1/2', '0', weight='1'),
            utils.QuestionScores('1', '1/2', '0', weight='1/2'),
            utils.QuestionScores('1', '1/2', '0', weight='2'),
            utils.QuestionScores('1', '1/2', '0', weight='2'),
        ]
        exam.set_base_scores(utils.QuestionScores('1', '1/2', '0'))
        exam.set_question_weights('A', [1, 2, 1, 2, '1/2'])
        exam.set_question_weights('B', ['1', '1', '1/2', '2', '2'])
        for value, key in zip(exam.scores['A'] + exam.scores['B'], scores):
            self.assertEqual(value, key)

    def testSetQuestionWeightsError(self):
        exam = utils.ExamConfig()
        self.assertRaises(ValueError, exam.set_question_weights, 'A', [1, 2, 2])
        exam.num_questions = 3
        self.assertRaises(ValueError, exam.set_question_weights, 'A', [1, 2, 2])
        exam.set_base_scores(utils.QuestionScores('1', '1/3', '0'))
        exam.set_question_weights('A', [1, 2, 2])
        self.assertRaises(ValueError, exam.set_question_weights, 'B', [2, 1, 1])


class TestScore(unittest.TestCase):

    def testScoreNoScores(self):
        answers = [0, 1, 2, 3, 0, 1]
        solutions = [1, 1, 3, 3, 4, 1]
        question_scores = None
        score = utils.Score(answers, solutions, question_scores)
        self.assertEqual(score.correct, 3)
        self.assertEqual(score.incorrect, 1)
        self.assertEqual(score.blank, 2)
        self.assertEqual(score.score, None)
        self.assertEqual(score.max_score, None)

    def testScoreEqualScores(self):
        answers = [0, 1, 2, 3, 0, 1]
        solutions = [1, 1, 3, 3, 4, 1]
        base_score = utils.QuestionScores('1', '1/2', '0')
        question_scores = 6 * [base_score]
        score = utils.Score(answers, solutions, question_scores)
        self.assertEqual(score.correct, 3)
        self.assertEqual(score.incorrect, 1)
        self.assertEqual(score.blank, 2)
        self.assertEqual(score.score, 2.5)
        self.assertEqual(score.max_score, 6.0)

    def testScoreDifferentScores(self):
        answers = [0, 1, 2, 3, 0, 1]
        solutions = [1, 1, 3, 3, 4, 1]
        base_score = utils.QuestionScores('1', '1/2', '0')
        question_scores = [
            base_score,
            base_score.clone(new_weight=2),
            base_score.clone(new_weight=2),
            base_score,
            base_score,
            base_score.clone(new_weight=3),
        ]
        score = utils.Score(answers, solutions, question_scores)
        self.assertEqual(score.correct, 3)
        self.assertEqual(score.incorrect, 1)
        self.assertEqual(score.blank, 2)
        self.assertEqual(score.score, 5.0)
        self.assertEqual(score.max_score, 10.0)

    def testScoreError(self):
        answers = [0, 1, 2, 3, 0, 1]
        solutions = [1, 1, 3, 3, 4, 1]
        base_score = utils.QuestionScores('1', '1/2', '0')
        question_scores = [
            base_score,
            base_score.clone(new_weight=2),
            base_score.clone(new_weight=2),
            base_score,
            base_score,
        ]
        self.assertRaises(ValueError, utils.Score,
                          answers, solutions, question_scores)
