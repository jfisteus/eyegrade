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

import os
import re
import configparser

from typing import Union

from . import utils
from . import scoring
from . import students


utils.EyegradeException.register_error(
    "exam-config-parse-error",
    "A parsing error occurred in the exam configuration file.",
)


class Exam:
    def __init__(
        self,
        capture_,
        decisions,
        solutions,
        student_listings,
        exam_id,
        question_scores,
        sessiondb=None,
    ):
        self.capture = capture_
        self.decisions = decisions
        self.student_listings = student_listings
        self.exam_id = exam_id
        self.score = scoring.Score(decisions.answers, solutions, question_scores)
        rank = self.rank_students()
        self.decisions.set_students_rank(rank)
        if rank:
            self.decisions.set_student(rank[0])
        self.sessiondb = sessiondb

    def update_grade(self):
        self.score.update()

    def reset_image(self):
        self.capture.reset_image()

    def draw_answers(self):
        self.capture.draw_answers(self.score)

    def draw_status(self):
        self.capture.draw_status()

    def draw_corner(self, point):
        self.capture.draw_corner(point)

    def get_image_drawn(self):
        return self.capture.image_drawn

    def toggle_answer(self, question, answer):
        if self.decisions.answers[question] == answer:
            self.decisions.change_answer(question, 0)
        else:
            self.decisions.change_answer(question, answer)
        self.score.update()
        self.capture.reset_image()
        self.draw_answers()

    def rank_students(self):
        if self.decisions.detected_id is not None:
            rank = [
                (self._id_rank(s, self.decisions.id_scores), s)
                for s in self.student_listings.iter_students()
                if s.group_id > 0
            ]
            students_rank = [student for score, student in sorted(rank, reverse=True)]
            if not students_rank:
                students_rank = [
                    students.Student(self.decisions.detected_id, None, None, None, None)
                ]
        else:
            students_rank = list(self.student_listings.iter_students())
        return students_rank

    def get_student_id_and_name(self):
        if self.decisions.student is not None:
            return self.decisions.student.id_and_name
        else:
            return None

    def ranked_student_ids(self):
        """Returns the ranked list of students as taken from the decision.

        Each entry is a student object. They are ranked according to
        their probability to be the actual student id. The most probable
        is the first in the list.

        """
        if (
            self.decisions.students_rank
            and self.decisions.student is not None
            and self.decisions.students_rank[0] != self.decisions.student
        ):
            rank = list(self.decisions.students_rank)
            if self.decisions.student in rank:
                rank.remove(self.decisions.student)
            rank.insert(0, self.decisions.student)
        else:
            rank = self.decisions.students_rank
        return rank

    def update_student_id(self, student):
        """Updates the student id of the current exam.

        Receives the Student object of the new identity
        (or None for clearing the student identity).

        """
        self.decisions.set_student(student)

    def load_capture(self):
        if self.capture is None:
            self.capture = self.sessiondb.read_capture(self.exam_id)

    def clear_capture(self):
        if self.capture is not None:
            self.capture = None

    def image_drawn_path(self):
        image_name = utils.capture_name(
            self.sessiondb.exam_config.capture_pattern,
            self.exam_id,
            self.decisions.student,
        )
        path = os.path.join(self.sessiondb.session_dir, "captures", image_name)
        if not os.path.isfile(path):
            path = utils.resource_path("not_found.png")
        return path

    def _id_rank(self, student, scores):
        rank = 0.0
        if len(scores) == len(student.student_id):
            for i, digit in enumerate(student.student_id):
                rank += scores[i][int(digit)]
        return rank


class ExamConfig:
    """Class for representing exam configuration. Once an instance has
       been created and data loaded, access directly to the attributes
       to get the data. The constructor reads data from a file. See
       doc/exam-data.sample for an example of such a file."""

    SCORES_MODE_NONE = 1
    SCORES_MODE_WEIGHTS = 2
    SCORES_MODE_INDIVIDUAL = 3

    re_model = re.compile("model-[0a-zA-Z]")

    def __init__(self, filename=None, capture_pattern=None):
        """Loads data from file if 'filename' is not None. Otherwise,
           default values are assigned to the attributes."""
        if filename is not None:
            self.read(filename=filename)
        else:
            self.num_questions = 0
            self.solutions = {}
            self.id_num_digits = 0
            self.dimensions = []
            self.num_options = []
            self.permutations = {}
            self.variations = {}
            self.models = []
            self.scores = {}
            self.base_scores = None
            self.left_to_right_numbering = False
            self.survey_mode = None
            self.scores_mode = ExamConfig.SCORES_MODE_NONE
        if capture_pattern is not None:
            self.capture_pattern = capture_pattern
        else:
            self.capture_pattern = utils.default_capture_pattern

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            equal = self.as_tuple() == other.as_tuple()
        else:
            equal = False
        return equal

    def as_tuple(self):
        return (
            self.num_questions,
            self.solutions,
            self.id_num_digits,
            self.dimensions,
            self.permutations,
            self.get_all_variations(),
            self.models,
            self.scores,
            self.base_scores,
            self.left_to_right_numbering,
            self.survey_mode,
            self.scores_mode,
        )

    def add_model(self, model):
        if model not in self.models:
            self.models.append(model)

    def set_solutions(self, model, solutions):
        if not isinstance(solutions, list):
            solutions = self._parse_solutions(solutions)
        if len(solutions) != self.num_questions:
            raise utils.EyegradeException(
                "Incorrect number of solutions (got {}, expected {}) for model {}.".format(
                    len(solutions), self.num_questions, model
                ),
                key="exam-config-parse-error",
            )
        for solution_set, num_options in zip(solutions, self.num_options):
            for solution in solution_set:
                if solution < 1 or solution > num_options:
                    raise utils.EyegradeException(
                        "Solution out of range for model {} (got {}, expected between 1 and {}).".format(
                            model, solution, num_options
                        ),
                        key="exam-config-parse-error",
                    )
            self.solutions[model] = solutions
        self.add_model(model)

    def get_solutions(self, model):
        """Returns the solutions for the given model.

        If in survey mode it returns []. If there are no solutions for
        this model, it returns None.

        """
        if not self.survey_mode:
            if model in self.solutions:
                return self.solutions[model]
            else:
                return None
        else:
            return []

    def set_permutations(self, model, permutations):
        if not isinstance(permutations, list):
            permutations = self._parse_permutations(permutations)
        elif permutations and isinstance(permutations[0], str):
            permutations = [
                self._parse_permutation(p, i) for i, p in enumerate(permutations)
            ]
        if len(permutations) != self.num_questions:
            raise ValueError("Permutations with incorrect number of questions")
        self.permutations[model] = permutations
        self.add_model(model)

    def get_permutations(self, model):
        """Returns the permutations for the given model.

        If there are no permutations for this model, it returns None.

        """
        if model in self.permutations:
            return self.permutations[model]
        else:
            return None

    def set_variations(self, model, variations):
        if not isinstance(variations, list):
            variations = self._parse_variations(variations)
        if len(variations) != self.num_questions:
            raise ValueError("Variations with incorrect number of questions")
        self.variations[model] = variations
        self.add_model(model)

    def get_variations(self, model):
        """Returns the variations for the given model.

        If there are no variations for this model, it returns the default
        ones instead of None.

        """
        if model in self.variations:
            return self.variations[model]
        else:
            return [0] * self.num_questions

    def get_all_variations(self):
        """Returns variations for all the registered models.

        The difference with respect to just accessing the variations attribute
        is that, when no variations are declared at all or for some models,
        the default variations are returned instead of None.

        """
        variations = {}
        for model in self.models:
            variations[model] = self.get_variations(model)
        return variations

    def set_dimensions(self, dimensions):
        self.dimensions, self.num_options = utils.parse_dimensions(dimensions)
        self.num_questions = sum(dim[1] for dim in self.dimensions)

    def enter_score_mode_none(self):
        """Resets the object to no scores."""
        self.scores_mode = ExamConfig.SCORES_MODE_NONE
        self.base_scores = None
        self.scores = {}

    def set_base_scores(self, scores, same_weights=False):
        """Set the base scores for the questions of this exam.

        The `scores` parameter must be an instance of QuestionScores.
        It must be done before setting the weights of each question.

        """
        if scores.weight != 1:
            raise ValueError("The base score must have weigth 1")
        if self.scores_mode == ExamConfig.SCORES_MODE_NONE:
            self.scores_mode = ExamConfig.SCORES_MODE_WEIGHTS
        elif self.scores_mode != ExamConfig.SCORES_MODE_WEIGHTS:
            raise ValueError("The score mode does not allow base scores")
        self.base_scores = scores
        if same_weights:
            self.reset_question_weights()
            for model in self.models:
                self.set_equal_scores(model)

    def set_equal_scores(self, model):
        """Set the base scores for the questions of this exam.

        The `scores` parameter must be an instance of QuestionScores.
        It must be done before setting the weights of each question.

        """
        if (
            self.scores_mode != ExamConfig.SCORES_MODE_WEIGHTS
            or self.base_scores is None
        ):
            raise ValueError("Invalid scores mode for set_equal_scores")
        scores = [
            self.base_scores.clone(new_weight=1) for i in range(self.num_questions)
        ]
        self._set_question_scores_internal(model, scores)

    def set_question_weights(self, model, weights):
        """Set the scores for a given model from question weights.

        The `weights` parameter can be a list with the weight of each
        question of that model.
        The final scores must be the same as in the scores for the rest of
        the models, possibly in a different order.

        A base score must have already been set.

        """
        if self.scores_mode != ExamConfig.SCORES_MODE_WEIGHTS:
            raise ValueError("Not in scores weight mode.")
        if isinstance(weights, str):
            weights = self._parse_weights(weights)
        scores = [self.base_scores.clone(new_weight=weight) for weight in weights]
        self._set_question_scores_internal(model, scores)

    def get_question_weights(self, model, formatted=False):
        """Return the list of question weights for a given model.

        Returns None if scores are not set by means of a base score,
        or there are no scores for this model.

        """
        if (
            self.scores_mode != ExamConfig.SCORES_MODE_WEIGHTS
            or self.base_scores is None
            or model not in self.scores
        ):
            return None
        elif not formatted:
            return [s.weight for s in self.scores[model]]
        else:
            return [s.format_weight() for s in self.scores[model]]

    def reset_question_weights(self):
        self.scores = {}

    def all_weights_are_one(self):
        """Return True if all the score weights are 1.

        It returns False if there are no scores set for at least one model.

        """
        if self.scores:
            # We only need to check one list of scores
            return all(s.weight == 1 for s in next(iter(self.scores.values())))
        else:
            return False

    def set_question_scores(self, model, scores):
        """Set the scores for a given model from question weights.

        The `scores` parameter must be a list of QuestionScores objects.
        The scores must be the same as in the scores for the rest of
        the models, possibly in a different order.

        A base score cannot have already been set.

        """
        if self.scores_mode == ExamConfig.SCORES_MODE_NONE:
            self.scores_mode = ExamConfig.SCORES_MODE_INDIVIDUAL
        elif self.scores_mode != ExamConfig.SCORES_MODE_INDIVIDUAL:
            raise ValueError("Invalid scores mode at set_question_scores")
        for score in scores:
            if score.weight != 1:
                raise ValueError("Only weight 1 scores allowed")
        self._set_question_scores_internal(model, scores)

    def _set_question_scores_internal(self, model, scores):
        """Set the scores for a given model from question weights.

        Internal method that does not check the current mode.

        The `scores` parameter must be a list of QuestionScores objects.
        The scores must be the same as in the scores for the rest of
        the models, possibly in a different order.

        """
        if len(scores) != self.num_questions:
            raise ValueError("Scores with an incorrect number of questions")
        if self.scores and sorted(scores) != sorted(next(iter(self.scores.values()))):
            #        if self.scores and sorted(scores) != sorted(self.scores.values()[0]):
            raise ValueError("Scores for all models must be equal but their order")
        self.scores[model] = scores
        self.add_model(model)

    def get_num_choices(self):
        """Returns the number of choices per question.

        If not all the questions have the same number of choices, it returns
        the maximum number of choices. If there are no questions, it returns
        None.

        """
        choices = [dim[0] for dim in self.dimensions]
        if choices:
            return max(choices)
        else:
            return None

    def read(self, filename):
        exam_data = configparser.ConfigParser()
        files_read = exam_data.read([filename])
        if len(files_read) != 1:
            raise IOError("Exam config file not found: " + filename)
        self._read_config_parser(exam_data)

    def _read_config_parser(self, exam_data: configparser.ConfigParser):
        """Reads exam configuration."""
        try:
            self.id_num_digits = exam_data.getint("exam", "id-num-digits")
        except ValueError:
            self.id_num_digits = 0
        self.set_dimensions(exam_data.get("exam", "dimensions"))
        has_solutions = exam_data.has_section("solutions")
        has_permutations = exam_data.has_section("permutations")
        has_variations = exam_data.has_section("variations")
        self.solutions = {}
        self.permutations = {}
        self.variations = {}
        self.models = []
        if has_solutions:
            for key, value in exam_data.items("solutions"):
                if not self.re_model.match(key):
                    raise utils.EyegradeException(
                        "Incorrect key in exam config: " + key,
                        key="exam-config-parse-error",
                    )
                model = key[-1].upper()
                self.set_solutions(model, value)
                if has_permutations:
                    key = "permutations-" + model
                    value = exam_data.get("permutations", key)
                    self.set_permutations(model, value)
                if has_variations:
                    key = "variations-" + model
                    value = exam_data.get("variations", key)
                    self.set_variations(model, value)
        has_correct_weight = exam_data.has_option("exam", "correct-weight")
        has_incorrect_weight = exam_data.has_option("exam", "incorrect-weight")
        has_blank_weight = exam_data.has_option("exam", "blank-weight")
        self.scores = {}
        if has_correct_weight and has_incorrect_weight:
            correct_weight = exam_data.get("exam", "correct-weight")
            incorrect_weight = exam_data.get("exam", "incorrect-weight")
            blank_weight: Union[str, int]
            if has_blank_weight:
                blank_weight = exam_data.get("exam", "blank-weight")
            else:
                blank_weight = 0
            self.scores_mode = ExamConfig.SCORES_MODE_WEIGHTS
            base_scores = scoring.QuestionScores(
                correct_weight, incorrect_weight, blank_weight
            )
            if not exam_data.has_section("question-score-weights"):
                self.set_base_scores(base_scores, same_weights=True)
            else:
                self.set_base_scores(base_scores)
                for model in self.models:
                    key = "weights-" + model
                    value = exam_data.get("question-score-weights", key)
                    self.set_question_weights(model, value)
        elif not has_correct_weight and not has_incorrect_weight:
            self.base_scores = None
            self.scores_mode = ExamConfig.SCORES_MODE_NONE
        else:
            raise utils.EyegradeException(
                "Exam config must contain correct and incorrect weight or none.",
                key="exam-config-parse-error",
            )
        if exam_data.has_option("exam", "left-to-right-numbering"):
            self.left_to_right_numbering = exam_data.getboolean(
                "exam", "left-to-right-numbering"
            )
        else:
            self.left_to_right_numbering = False
        if exam_data.has_option("exam", "survey-mode"):
            self.survey_mode = exam_data.getboolean("exam", "survey-mode")
        else:
            self.survey_mode = False
        self.models.sort()

    def save(self, filename):
        data = []
        data.append("[exam]")
        data.append("dimensions: %s" % self.format_dimensions())
        data.append("id-num-digits: %d" % self.id_num_digits)
        if self.left_to_right_numbering:
            data.append("left-to-right-numbering: yes")
        if self.survey_mode:
            data.append("survey-mode: yes")
        if self.base_scores is not None:
            data.append(
                "correct-weight: {0}".format(self.base_scores.format_correct_score())
            )
            data.append(
                "incorrect-weight: {0}".format(
                    self.base_scores.format_incorrect_score()
                )
            )
            data.append(
                "blank-weight: {0}".format(self.base_scores.format_blank_score())
            )
        if self.solutions:
            data.append("")
            data.append("[solutions]")
            for model in sorted(self.models):
                data.append(
                    "model-{0}: {1}".format(model, self.format_solutions(model))
                )
        if self.permutations:
            data.append("")
            data.append("[permutations]")
            for model in sorted(self.models):
                data.append(
                    "permutations-{0}: {1}".format(
                        model, self.format_permutations(model)
                    )
                )
        if self.variations:
            data.append("")
            data.append("[variations]")
            for model in sorted(self.models):
                data.append(
                    "variations-{0}: {1}".format(model, self.format_variations(model))
                )
        if (
            self.scores_mode == ExamConfig.SCORES_MODE_WEIGHTS
            and self.scores
            and not self.all_weights_are_one()
        ):
            # If all the scores are equal, there is no need to specify weights
            data.append("")
            data.append("[question-score-weights]")
            for model in sorted(self.models):
                data.append(
                    "weights-{0}: {1}".format(model, self.format_weights(model))
                )
        data.append("")
        with open(filename, "w") as file_:
            file_.write("\n".join(data))

    def format_dimensions(self):
        return ";".join(["%d,%d" % (cols, rows) for cols, rows in self.dimensions])

    def format_solutions(self, model):
        return "/".join(
            [self._format_question_solutions(n) for n in self.solutions[model]]
        )

    def _format_question_solutions(self, question_solution):
        return ",".join(str(s) for s in question_solution)

    def format_permutations(self, model):
        return "/".join([self.format_permutation(p) for p in self.permutations[model]])

    def format_permutation(self, permutation):
        num_question, options = permutation
        return "%d{%s}" % (num_question, ",".join([str(n) for n in options]))

    def format_variations(self, model):
        return "/".join([str(variation) for variation in self.get_variations(model)])

    def format_weights(self, model):
        return ",".join([s.format_weight() for s in self.scores[model]])

    def _parse_solutions(self, solutions_str):
        pieces = solutions_str.split("/")
        if len(pieces) != self.num_questions:
            raise utils.EyegradeException(
                "Wrong number of solutions", key="exam-config-parse-error"
            )
        return [self._parse_question_solution(piece) for piece in pieces]

    def _parse_question_solution(self, text):
        pieces = text.split(",")
        if not pieces:
            raise utils.EyegradeException(
                "Wrong number of solutions to a question", key="exam-config-parse-error"
            )
        return set(int(p) for p in pieces)

    def _parse_permutations(self, permutations_str):
        permutations = []
        pieces = permutations_str.split("/")
        if len(pieces) != self.num_questions:
            raise utils.EyegradeException(
                "Wrong number of permutations", key="exam-config-parse-error"
            )
        for i, piece in enumerate(pieces):
            permutations.append(self._parse_permutation(piece, i))
        return permutations

    def _parse_permutation(self, str_value, question_number):
        splitted = str_value.split("{")
        num_question = int(splitted[0])
        options = [int(p) for p in splitted[1][:-1].split(",")]
        if len(options) > self.num_options[question_number]:
            raise utils.EyegradeException(
                "Wrong number of options in permutation", key="exam-config-parse-error"
            )
        return (num_question, options)

    def _parse_variations(self, variations_str):
        pieces = variations_str.split("/")
        if len(pieces) != self.num_questions:
            raise utils.EyegradeException(
                "Wrong number of variation items", key="exam-config-parse-error"
            )
        return [int(variation) for variation in pieces]

    def _parse_weights(self, weights_str):
        pieces = weights_str.split(",")
        if len(pieces) != self.num_questions:
            raise utils.EyegradeException(
                "Wrong number of weight items", key="exam-config-parse-error"
            )
        return [p for p in pieces]
