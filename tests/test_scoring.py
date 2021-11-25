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
import fractions

import eyegrade.scoring as scoring
import eyegrade.exams as exams


class TestQuestionScores(unittest.TestCase):
    def testFloat(self):
        score = scoring.QuestionScores(1.0, 0.5, 0.0)
        key_1 = "1.0000000000000000"
        key_2 = "0.5000000000000000"
        key_3 = "0.0000000000000000"
        self.assertEqual(score.format_all(), ";".join((key_1, key_2, key_3)))
        self.assertEqual(score.format_score(scoring.QuestionScores.CORRECT), key_1)
        self.assertEqual(score.format_correct_score(), key_1)
        self.assertEqual(score.format_score(scoring.QuestionScores.INCORRECT), key_2)
        self.assertEqual(score.format_incorrect_score(), key_2)
        self.assertEqual(score.format_score(scoring.QuestionScores.BLANK), key_3)
        self.assertEqual(score.format_blank_score(), key_3)
        self.assertEqual(score.score(scoring.QuestionScores.CORRECT), 1.0)
        self.assertEqual(score.score(scoring.QuestionScores.INCORRECT), -0.5)
        self.assertEqual(score.score(scoring.QuestionScores.BLANK), 0.0)
        self.assertEqual(score.format_weight(), "1")

    def testFractionAndInt(self):
        score = scoring.QuestionScores("1", "1/3", "0")
        self.assertEqual(score.format_all(), "1;1/3;0")
        self.assertEqual(score.format_score(scoring.QuestionScores.CORRECT), "1")
        self.assertEqual(score.format_score(scoring.QuestionScores.INCORRECT), "1/3")
        self.assertEqual(score.format_score(scoring.QuestionScores.BLANK), "0")
        self.assertEqual(score.score(scoring.QuestionScores.CORRECT), 1)
        self.assertEqual(
            score.score(scoring.QuestionScores.INCORRECT), fractions.Fraction(-1, 3)
        )
        self.assertEqual(score.score(scoring.QuestionScores.BLANK), 0)
        self.assertEqual(score.format_weight(), "1")

    def testSignedFormat(self):
        score = scoring.QuestionScores("1", "1/3", "1/6")
        result = score.format_score(scoring.QuestionScores.CORRECT, signed=True)
        self.assertEqual(result, "1")
        result = score.format_score(scoring.QuestionScores.INCORRECT, signed=True)
        self.assertEqual(result, "-1/3")
        result = score.format_score(scoring.QuestionScores.BLANK, signed=True)
        self.assertEqual(result, "-1/6")
        result = score.format_correct_score(signed=True)
        self.assertEqual(result, "1")
        result = score.format_incorrect_score(signed=True)
        self.assertEqual(result, "-1/3")
        result = score.format_blank_score(signed=True)
        self.assertEqual(result, "-1/6")
        score = scoring.QuestionScores("1.0", "0.5", "0.25")
        result = score.format_score(scoring.QuestionScores.CORRECT, signed=True)
        self.assertEqual(result, "1.0000000000000000")
        result = score.format_score(scoring.QuestionScores.INCORRECT, signed=True)
        self.assertEqual(result, "-0.5000000000000000")
        result = score.format_score(scoring.QuestionScores.BLANK, signed=True)
        self.assertEqual(result, "-0.2500000000000000")

    def testWeight(self):
        score = scoring.QuestionScores("1", "1/3", "1/6", weight="3/2")
        self.assertEqual(score.format_all(), "1;1/3;1/6")
        self.assertEqual(score.format_score(scoring.QuestionScores.CORRECT), "1")
        self.assertEqual(score.format_score(scoring.QuestionScores.INCORRECT), "1/3")
        self.assertEqual(score.format_score(scoring.QuestionScores.BLANK), "1/6")
        self.assertEqual(
            score.score(scoring.QuestionScores.CORRECT), fractions.Fraction(3, 2)
        )
        self.assertEqual(
            score.score(scoring.QuestionScores.INCORRECT), fractions.Fraction(-1, 2)
        )
        self.assertEqual(
            score.score(scoring.QuestionScores.BLANK), fractions.Fraction(-1, 4)
        )
        self.assertEqual(score.format_weight(), "3/2")

    def testNegativeScores(self):
        self.assertRaises(ValueError, scoring.QuestionScores, "-1/3", "1/6", "0")
        score = scoring.QuestionScores("1", "-1/3", "1/6")
        self.assertEqual(
            score.score(scoring.QuestionScores.CORRECT), fractions.Fraction(1, 1)
        )
        self.assertEqual(
            score.score(scoring.QuestionScores.INCORRECT), fractions.Fraction(-1, 3)
        )
        self.assertEqual(
            score.score(scoring.QuestionScores.BLANK), fractions.Fraction(-1, 6)
        )
        score = scoring.QuestionScores("1", "1/3", "-1/6")
        self.assertEqual(
            score.score(scoring.QuestionScores.CORRECT), fractions.Fraction(1, 1)
        )
        self.assertEqual(
            score.score(scoring.QuestionScores.INCORRECT), fractions.Fraction(-1, 3)
        )
        self.assertEqual(
            score.score(scoring.QuestionScores.BLANK), fractions.Fraction(-1, 6)
        )

    def testNegativeWeights(self):
        self.assertRaises(
            ValueError, scoring.QuestionScores, "1/3", "1/6", "0", weight="-1/2"
        )
        self.assertRaises(
            ValueError, scoring.QuestionScores, "1/3", "1/6", "0", weight="-1"
        )
        self.assertRaises(
            ValueError, scoring.QuestionScores, "1/3", "1/6", "0", weight="-0.5"
        )

    def testBadValues(self):
        self.assertRaises(ValueError, scoring.QuestionScores, "1//3", "1/6", "0")
        self.assertRaises(ValueError, scoring.QuestionScores, "1", "1a", "0")
        self.assertRaises(ValueError, scoring.QuestionScores, "1", "2", "0.z3")

    def testClone(self):
        score1 = scoring.QuestionScores("1", "1/3", "1/6", weight="3/2")
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
            scoring.QuestionScores("1", "1/3", "0"),
            scoring.QuestionScores("2", "2/3", "1/2"),
            scoring.QuestionScores("1", "1/3", "0"),
            scoring.QuestionScores("2", "2/3", "0"),
            scoring.QuestionScores("1/2", "1/6", "0"),
        ]
        sorted_scores = [scores[4], scores[0], scores[2], scores[3], scores[1]]
        self.assertEqual(sorted(scores), sorted_scores)


class TestExamConfigScores(unittest.TestCase):
    def testSetQuestionScores(self):
        exam = exams.ExamConfig()
        exam.num_questions = 5
        scores = [
            scoring.QuestionScores("1", "1/3", "0"),
            scoring.QuestionScores("2", "2/3", "0"),
            scoring.QuestionScores("1", "1/3", "0"),
            scoring.QuestionScores("2", "2/3", "0"),
            scoring.QuestionScores("1/2", "1/6", "0"),
        ]
        exam.set_question_scores("A", scores)
        exam.set_question_scores(
            "B", [scores[1], scores[2], scores[4], scores[0], scores[3]]
        )

    def testSetQuestionScoresError(self):
        exam = exams.ExamConfig()
        scores = [
            scoring.QuestionScores("1", "1/3", "0"),
            scoring.QuestionScores("2", "2/3", "0"),
            scoring.QuestionScores("1", "1/3", "0"),
            scoring.QuestionScores("2", "2/3", "0"),
            scoring.QuestionScores("1/2", "1/6", "0"),
        ]
        self.assertRaises(ValueError, exam.set_question_scores, "A", scores)
        exam.num_questions = 5
        exam.set_question_scores("A", scores)
        self.assertRaises(
            ValueError,
            exam.set_question_scores,
            "B",
            [scores[1], scores[1], scores[4], scores[0], scores[3]],
        )

    def testSetEqualScores1(self):
        exam = exams.ExamConfig()
        exam.num_questions = 5
        exam.set_base_scores(scoring.QuestionScores("1", "1/2", "0"))
        exam.set_equal_scores("A")
        exam.set_equal_scores("B")
        for scores in exam.scores["A"] + exam.scores["B"]:
            self.assertEqual(scores, exam.base_scores)

    def testSetEqualScores2(self):
        exam = exams.ExamConfig()
        exam.num_questions = 5
        exam.models = ["A", "B"]
        exam.set_base_scores(scoring.QuestionScores("1", "1/2", "0"), same_weights=True)
        for scores in exam.scores["A"] + exam.scores["B"]:
            self.assertEqual(scores, exam.base_scores)

    def testSetEqualScores3(self):
        """Test for issue #96.

        An exception because of different weights was raised because
        of the issue.

        """
        exam = exams.ExamConfig()
        exam.num_questions = 5
        exam.set_base_scores(scoring.QuestionScores("1", "1/2", "0"), same_weights=True)
        exam.set_equal_scores("A")
        exam.set_equal_scores("B")
        for scores in exam.scores["A"] + exam.scores["B"]:
            self.assertEqual(scores, exam.base_scores)
        exam.set_base_scores(scoring.QuestionScores("2", "1", "0"), same_weights=True)
        for scores in exam.scores["A"] + exam.scores["B"]:
            self.assertEqual(scores, exam.base_scores)

    def testSetBaseScoresError(self):
        exam = exams.ExamConfig()
        scores = scoring.QuestionScores("1", "1/2", "0", weight="2")
        self.assertRaises(ValueError, exam.set_base_scores, scores)

    def testSetQuestionWeights(self):
        exam = exams.ExamConfig()
        exam.num_questions = 5
        scores = [
            scoring.QuestionScores("1", "1/2", "0", weight="1"),
            scoring.QuestionScores("1", "1/2", "0", weight="2"),
            scoring.QuestionScores("1", "1/2", "0", weight="1"),
            scoring.QuestionScores("1", "1/2", "0", weight="2"),
            scoring.QuestionScores("1", "1/2", "0", weight="1/2"),
            scoring.QuestionScores("1", "1/2", "0", weight="1"),
            scoring.QuestionScores("1", "1/2", "0", weight="1"),
            scoring.QuestionScores("1", "1/2", "0", weight="1/2"),
            scoring.QuestionScores("1", "1/2", "0", weight="2"),
            scoring.QuestionScores("1", "1/2", "0", weight="2"),
        ]
        exam.set_base_scores(scoring.QuestionScores("1", "1/2", "0"))
        exam.set_question_weights("A", [1, 2, 1, 2, "1/2"])
        exam.set_question_weights("B", ["1", "1", "1/2", "2", "2"])
        for value, key in zip(exam.scores["A"] + exam.scores["B"], scores):
            self.assertEqual(value, key)

    def testSetQuestionWeightsError(self):
        exam = exams.ExamConfig()
        self.assertRaises(ValueError, exam.set_question_weights, "A", [1, 2, 2])
        exam.num_questions = 3
        self.assertRaises(ValueError, exam.set_question_weights, "A", [1, 2, 2])
        exam.set_base_scores(scoring.QuestionScores("1", "1/3", "0"))
        exam.set_question_weights("A", [1, 2, 2])
        self.assertRaises(ValueError, exam.set_question_weights, "B", [2, 1, 1])

    def testGetQuestionWeights(self):
        exam = exams.ExamConfig()
        exam.num_questions = 3
        self.assertEqual(exam.get_question_weights("A"), None)
        exam.set_base_scores(scoring.QuestionScores("1", "1/2", "0"))
        self.assertEqual(exam.get_question_weights("A"), None)
        exam.set_question_weights("A", [1, 2, "1/2"])
        exam.set_question_weights("B", ["1/2", "1", "2"])
        self.assertEqual(
            exam.get_question_weights("A"), [1, 2, fractions.Fraction(1, 2)]
        )
        self.assertEqual(
            exam.get_question_weights("B"), [fractions.Fraction(1, 2), 1, 2]
        )
        self.assertEqual(
            exam.get_question_weights("A", formatted=True), ["1", "2", "1/2"]
        )
        self.assertEqual(
            exam.get_question_weights("B", formatted=True), ["1/2", "1", "2"]
        )

    def testAllWeightsAreOneWeights(self):
        exam = exams.ExamConfig()
        exam.num_questions = 5
        self.assertFalse(exam.all_weights_are_one())
        exam.models = ["A", "B"]
        self.assertFalse(exam.all_weights_are_one())
        exam.set_base_scores(scoring.QuestionScores("1", "1/2", "0"), same_weights=True)
        self.assertTrue(exam.all_weights_are_one())

    def testAllWeightsAreOneWeightsNegative(self):
        exam = exams.ExamConfig()
        exam.num_questions = 5
        exam.set_base_scores(scoring.QuestionScores("1", "1/2", "0"))
        exam.set_question_weights("A", [1, 2, 1, "1/2", 1])
        exam.set_question_weights("B", [2, 1, 1, 1, "1/2"])
        self.assertFalse(exam.all_weights_are_one())


class TestScore(unittest.TestCase):
    def testScoreNoScores(self):
        answers = [0, 1, 2, 3, 0, 1]
        solutions = [{1}, {1}, {3}, {3}, {4}, {1}]
        question_scores = None
        score = scoring.Score(answers, solutions, question_scores)
        self.assertEqual(score.correct, 3)
        self.assertEqual(score.incorrect, 1)
        self.assertEqual(score.blank, 2)
        self.assertEqual(score.score, None)
        self.assertEqual(score.max_score, None)

    def testScoreEqualScores(self):
        answers = [0, 1, 2, 3, 0, 1]
        solutions = [{1}, {1}, {3}, {3}, {4}, {1}]
        base_score = scoring.QuestionScores("1", "1/2", "0")
        question_scores = 6 * [base_score]
        score = scoring.Score(answers, solutions, question_scores)
        self.assertEqual(score.correct, 3)
        self.assertEqual(score.incorrect, 1)
        self.assertEqual(score.blank, 2)
        self.assertEqual(score.score, 2.5)
        self.assertEqual(score.max_score, 6.0)

    def testScoreDifferentScores(self):
        answers = [0, 1, 2, 3, 0, 1]
        solutions = [{1}, {1}, {3}, {3}, {4}, {1}]
        base_score = scoring.QuestionScores("1", "1/2", "0")
        question_scores = [
            base_score,
            base_score.clone(new_weight=2),
            base_score.clone(new_weight=2),
            base_score,
            base_score,
            base_score.clone(new_weight=3),
        ]
        score = scoring.Score(answers, solutions, question_scores)
        self.assertEqual(score.correct, 3)
        self.assertEqual(score.incorrect, 1)
        self.assertEqual(score.blank, 2)
        self.assertEqual(score.score, 5.0)
        self.assertEqual(score.max_score, 10.0)

    def testScoreError(self):
        answers = [0, 1, 2, 3, 0, 1]
        solutions = [{1}, {1}, {3}, {3}, {4}, {1}]
        base_score = scoring.QuestionScores("1", "1/2", "0")
        question_scores = [
            base_score,
            base_score.clone(new_weight=2),
            base_score.clone(new_weight=2),
            base_score,
            base_score,
        ]
        self.assertRaises(
            ValueError, scoring.Score, answers, solutions, question_scores
        )

    def testScoreMultipleCorrect(self):
        answers = [1, 1, 2, 3, 2, 1]
        solutions = [{1}, {1}, {2, 3}, {3}, {4}, {1}]
        base_score = scoring.QuestionScores("1", "0", "0")
        question_scores = 6 * [base_score]
        score = scoring.Score(answers, solutions, question_scores)
        self.assertEqual(score.correct, 5)
        self.assertEqual(score.incorrect, 1)
        self.assertEqual(score.blank, 0)
        self.assertEqual(score.score, 5.0)
        self.assertEqual(score.max_score, 6.0)


if __name__ == "__main__":
    unittest.main()
