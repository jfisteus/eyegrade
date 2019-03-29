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
# <https://www.gnu.org/licenses/>.
#

import random
import io
import os
import re
import configparser

from . import utils
from . import scoring
from . import students


class Exam:
    def __init__(self, capture_, decisions, solutions, student_listings,
                 exam_id, question_scores, sessiondb=None):
        self.capture = capture_
        self.decisions = decisions
        self.student_listings = student_listings
        self.exam_id = exam_id
        self.score = scoring.Score(decisions.answers, solutions,
                                   question_scores)
        rank = self.rank_students()
        self.decisions.set_students_rank(rank)
        if len(rank) > 0:
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
            rank = [(self._id_rank(s, self.decisions.id_scores), s)
                    for s in self.student_listings.iter_students()
                    if s.group_id > 0]
            students_rank = [student
                             for score, student in sorted(rank, reverse=True)]
            if not students_rank:
                students_rank = [students.Student( \
                                        self.decisions.detected_id,
                                        None,
                                        None,
                                        None,
                                        None)]
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
        if (len(self.decisions.students_rank) > 0
            and self.decisions.students_rank[0] != self.decisions.student):
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
        image_name = utils.capture_name( \
                                self.sessiondb.exam_config.capture_pattern,
                                self.exam_id, self.decisions.student)
        path = os.path.join(self.sessiondb.session_dir, 'captures', image_name)
        if not os.path.isfile(path):
            path = utils.resource_path('not_found.png')
        return path

    def _id_rank(self, student, scores):
        rank = 0.0
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

    re_model = re.compile('model-[0a-zA-Z]')

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
            self.permutations = {}
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

    def add_model(self, model):
        if not model in self.models:
            self.models.append(model)

    def set_solutions(self, model, solutions):
        if not isinstance(solutions, list):
            solutions = self._parse_solutions(solutions)
        if len(solutions) != self.num_questions:
            raise ValueError('Solutions with incorrect number of questions')
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
        elif len(permutations) > 0 and isinstance(permutations[0], str):
            permutations = [self._parse_permutation(p, i) \
                            for i, p in enumerate(permutations)]
        if len(permutations) != self.num_questions:
            raise ValueError('Permutations with incorrect number of questions')
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
            raise ValueError('The base score must have weigth 1')
        if self.scores_mode == ExamConfig.SCORES_MODE_NONE:
            self.scores_mode = ExamConfig.SCORES_MODE_WEIGHTS
        elif self.scores_mode != ExamConfig.SCORES_MODE_WEIGHTS:
            raise ValueError('The score mode does not allow base scores')
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
        if (self.scores_mode != ExamConfig.SCORES_MODE_WEIGHTS
            or self.base_scores is None):
            raise ValueError('Invalid scores mode for set_equal_scores')
        scores = [self.base_scores.clone(new_weight=1)
                  for i in range(self.num_questions)]
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
            raise ValueError('Not in scores weight mode.')
        if isinstance(weights, str):
            weights = self._parse_weights(weights)
        scores = [self.base_scores.clone(new_weight=weight) \
                  for weight in weights]
        self._set_question_scores_internal(model, scores)

    def get_question_weights(self, model, formatted=False):
        """Return the list of question weights for a given model.

        Returns None if scores are not set by means of a base score,
        or there are no scores for this model.

        """
        if (self.scores_mode != ExamConfig.SCORES_MODE_WEIGHTS
            or self.base_scores is None or not model in self.scores):
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
        if len(self.scores) > 0:
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
            raise ValueError('Invalid scores mode at set_question_scores')
        for s in scores:
            if s.weight != 1:
                raise ValueError('Only weight 1 scores allowed')
        self._set_question_scores_internal(model, scores)

    def _set_question_scores_internal(self, model, scores):
        """Set the scores for a given model from question weights.

        Internal method that does not check the current mode.

        The `scores` parameter must be a list of QuestionScores objects.
        The scores must be the same as in the scores for the rest of
        the models, possibly in a different order.

        """
        if len(scores) != self.num_questions:
            raise ValueError('Scores with an incorrect number of questions')
        if (self.scores
            and sorted(scores) != sorted(next(iter(self.scores.values())))):
#        if self.scores and sorted(scores) != sorted(self.scores.values()[0]):
            raise ValueError('Scores for all models must be equal '
                             'but their order')
        self.scores[model] = scores
        self.add_model(model)

    def get_num_choices(self):
        """Returns the number of choices per question.

        If not all the questions have the same number of choices, it returns
        the maximum number of choices. If there are no questions, it returns
        None.

        """
        choices = [dim[0] for dim in self.dimensions]
        if len(choices) > 0:
            return max(choices)
        else:
            return None

    def read(self, filename=None, file_=None, data=None):
        """Reads exam configuration.

           Either 'filename', 'file_' or 'data' must be provided.
           'filename' specifies the name of a file to read.  'file_' is
           a file object instead of a file name.  'data' must be a
           string that contains the actual content of the config file
           to be parsed. Only one of them should not be None, although
           this restriction is not enforced: the first one not to be
           None, in the same order they are specified in the function,
           is used.

        """
        assert((filename is not None) or (file_ is not None)
               or (data is not None))
        exam_data = configparser.ConfigParser()
        if filename is not None:
            files_read = exam_data.read([filename])
            if len(files_read) != 1:
                raise IOError('Exam config file not found: ' + filename)
        elif file_ is not None:
            exam_data.readfp(file_)
        elif data is not None:
            exam_data.readfp(io.BytesIO(data))
        try:
            self.id_num_digits = exam_data.getint('exam', 'id-num-digits')
        except:
            self.id_num_digits = 0
        self.set_dimensions(exam_data.get('exam', 'dimensions'))
        has_solutions = exam_data.has_section('solutions')
        has_permutations = exam_data.has_section('permutations')
        self.solutions = {}
        self.permutations = {}
        self.models = []
        if has_solutions:
            for key, value in exam_data.items('solutions'):
                if not self.re_model.match(key):
                    raise Exception('Incorrect key in exam config: ' + key)
                model = key[-1].upper()
                self.set_solutions(model, value)
                if has_permutations:
                    key = 'permutations-' + model
                    value = exam_data.get('permutations', key)
                    self.set_permutations(model, value)
        has_correct_weight = exam_data.has_option('exam', 'correct-weight')
        has_incorrect_weight = exam_data.has_option('exam', 'incorrect-weight')
        has_blank_weight = exam_data.has_option('exam', 'blank-weight')
        self.scores = {}
        if has_correct_weight and has_incorrect_weight:
            cw = exam_data.get('exam', 'correct-weight')
            iw = exam_data.get('exam', 'incorrect-weight')
            if has_blank_weight:
                bw = exam_data.get('exam', 'blank-weight')
            else:
                bw = 0
            self.scores_mode = ExamConfig.SCORES_MODE_WEIGHTS
            base_scores = scoring.QuestionScores(cw, iw, bw)
            if not exam_data.has_section('question-score-weights'):
                self.set_base_scores(base_scores, same_weights=True)
            else:
                self.set_base_scores(base_scores)
                for model in self.models:
                    key = 'weights-' + model
                    value = exam_data.get('question-score-weights', key)
                    self.set_question_weights(model, value)
        elif not has_correct_weight and not has_incorrect_weight:
            self.base_scores = None
            self.scores_mode = ExamConfig.SCORES_MODE_NONE
        else:
            raise Exception('Exam config must contain correct and incorrect '
                            'weight or none')
        if exam_data.has_option('exam', 'left-to-right-numbering'):
            self.left_to_right_numbering = \
                       exam_data.getboolean('exam', 'left-to-right-numbering')
        else:
            self.left_to_right_numbering = False
        if exam_data.has_option('exam', 'survey-mode'):
            self.survey_mode = exam_data.getboolean('exam', 'survey-mode')
        else:
            self.survey_mode = False
        self.models.sort()

    def save(self, filename):
        data = []
        data.append('[exam]')
        data.append('dimensions: %s'%self.format_dimensions())
        data.append('id-num-digits: %d'%self.id_num_digits)
        if self.left_to_right_numbering:
            data.append('left-to-right-numbering: yes')
        if self.survey_mode:
            data.append('survey-mode: yes')
        if self.base_scores is not None:
            data.append('correct-weight: {0}'\
              .format(self.base_scores.format_correct_score()))
            data.append('incorrect-weight: {0}'\
              .format(self.base_scores.format_incorrect_score()))
            data.append('blank-weight: {0}'\
              .format(self.base_scores.format_blank_score()))
        if len(self.solutions) > 0:
            data.append('')
            data.append('[solutions]')
            for model in sorted(self.models):
                data.append('model-{0}: {1}'\
                            .format(model, self.format_solutions(model)))
        if len(self.permutations) > 0:
            data.append('')
            data.append('[permutations]')
            for model in sorted(self.models):
                data.append('permutations-{0}: {1}'\
                            .format(model, self.format_permutations(model)))
        if (self.scores_mode == ExamConfig.SCORES_MODE_WEIGHTS
            and len(self.scores)
            and not self.all_weights_are_one()):
            # If all the scores are equal, there is no need to specify weights
            data.append('')
            data.append('[question-score-weights]')
            for model in sorted(self.models):
                data.append('weights-{0}: {1}'\
                            .format(model, self.format_weights(model)))
        data.append('')
        with open(filename, 'w') as file_:
            file_.write('\n'.join(data))

    def format_dimensions(self):
        return ';'.join(['%d,%d'%(cols, rows) \
                             for cols, rows in self.dimensions])

    def format_solutions(self, model):
        return '/'.join([str(n) for n in self.solutions[model]])

    def format_permutations(self, model):
        return '/'.join([self.format_permutation(p) \
                         for p in self.permutations[model]])

    def format_permutation(self, permutation):
        num_question, options = permutation
        return '%d{%s}'%(num_question, ','.join([str(n) for n in options]))

    def format_weights(self, model):
        return ','.join([s.format_weight() for s in self.scores[model]])

    def _parse_solutions(self, s):
        pieces = s.split('/')
        if len(pieces) != self.num_questions:
            raise Exception('Wrong number of solutions')
        return [int(num) for num in pieces]

    def _parse_permutations(self, s):
        permutations = []
        pieces = s.split('/')
        if len(pieces) != self.num_questions:
            raise Exception('Wrong number of permutations')
        for i, piece in enumerate(pieces):
            permutations.append(self._parse_permutation(piece, i))
        return permutations

    def _parse_permutation(self, str_value, question_number):
        splitted = str_value.split('{')
        num_question = int(splitted[0])
        options = [int(p) for p in splitted[1][:-1].split(',')]
        if len(options) > self.num_options[question_number]:
            raise Exception('Wrong number of options in permutation')
        return (num_question, options)

    def _parse_weights(self, s):
        pieces = s.split(',')
        if len(pieces) != self.num_questions:
            raise Exception('Wrong number of weight items')
        return [p for p in pieces]


class ExamQuestions:
    def __init__(self):
        self.questions = []
        self.subject = None
        self.degree = None
        self.date = None
        self.duration = None
        self.student_id_label = None
        self._student_id_length = None
        self.scores = None
        self.shuffled_questions = {}
        self.permutations = {}

    @property
    def student_id_length(self):
        return self._student_id_length

    @student_id_length.setter
    def student_id_length(self, length):
        if length >= 0 and length <= 16:
            self._student_id_length = length
        else:
            raise utils.EyegradeException('Student id length must be bewteen '
                                          '0 and 16 (both included)')

    def num_questions(self):
        """Returns the number of questions of the exam."""
        return len(self.questions)

    def num_choices(self):
        """Returns the number of choices of the questions.

           If not all the questions have the same number of choices,
           it returns the maximum. If there are no exams, it returns None.

        """
        num = [len(q.correct_choices) + len(q.incorrect_choices) \
                   for q in self.questions]
        if len(num) > 0:
            return max(num)
        else:
            return None

    def homogeneous_num_choices(self):
        """Returns True if all the questions have the same number of choices.

        Returns None if the list of questions is empty.

        """
        num = [len(q.correct_choices) + len(q.incorrect_choices) \
                   for q in self.questions]
        if len(num) > 0:
            return min(num) == max(num)
        else:
            return None

    def shuffle(self, model):
        """Shuffles questions and options within questions for the given model.

        """
        shuffled, permutations = shuffle(self.questions)
        self.shuffled_questions[model] = shuffled
        self.permutations[model] = permutations
        for question in self.questions:
            question.shuffle(model)

    def set_permutation(self, model, permutation):
        self.permutations[model] = [p[0] - 1 for p in permutation]
        self.shuffled_questions[model] = \
            [self.questions[i] for i in self.permutations[model]]
        for q, p in zip(self.shuffled_questions[model], permutation):
            choices = q.correct_choices + q.incorrect_choices
            q.permutations[model] = [i - 1 for i in p[1]]
            q.shuffled_choices[model] = [choices[i - 1] for i in p[1]]

    def solutions_and_permutations(self, model):
        solutions = []
        permutations = []
        for qid in self.permutations[model]:
            answers_perm = self.questions[qid].permutations[model]
            solutions.append(1 + answers_perm.index(0))
            permutations.append((qid + 1, utils.increment_list(answers_perm)))
        return solutions, permutations


class Question:
    def __init__(self):
        self.text = None
        self.correct_choices = []
        self.incorrect_choices = []
        self.shuffled_choices = {}
        self.permutations = {}

    def shuffle(self, model):
        shuffled, permutations = \
            shuffle(self.correct_choices + self.incorrect_choices)
        self.shuffled_choices[model] = shuffled
        self.permutations[model] = permutations


class QuestionComponent:
    """A piece of text and optional figure or code.

       Represents both the text of a question and its choices.

    """
    def __init__(self, in_choice):
        self.in_choice = in_choice
        self.text = None
        self.code = None
        self.figure = None
        self.annex_width = None
        self.annex_pos = None

    def check_is_valid(self):
        if self.code is not None and self.figure is not None:
            raise Exception('Code and figure cannot be in the same block')
        if (self.in_choice and self.annex_pos != 'center' and
            (self.code is not None or self.figure is not None)):
            raise Exception('Figures and code in answers must be centered')
        if (self.code is not None and self.annex_pos == 'center' and
            self.annex_width != None):
            raise Exception('Centered code cannot have width')
        if not self.in_choice and self.text is None:
            raise Exception('Questions must have a text')


def read_exam_questions(exam_filename):
    import xml.dom.minidom
    from . import examparser
    dom_tree = xml.dom.minidom.parse(exam_filename)
    # By now, only one parser exists. In the future multiple parsers can
    # be called from here, to allow multiple data formats.
    return examparser.parse_exam(dom_tree)


def shuffle(data):
    """Returns a tuple (list, permutations) with data shuffled.

       Permutations is another list with the original position of each
       term. That is, shuffled[i] was in the original list in
       permutations[i] position.

    """
    to_sort = [(random.random(), item, pos) for pos, item in enumerate(data)]
    shuffled_data = []
    permutations = []
    for val, item, pos in sorted(to_sort):
        shuffled_data.append(item)
        permutations.append(pos)
    return shuffled_data, permutations
