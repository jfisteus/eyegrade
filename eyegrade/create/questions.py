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

from .. import utils


class ExamQuestions:
    def __init__(self):
        self.questions = QuestionsContainer()
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
            raise utils.EyegradeException(
                "Student id length must be bewteen " "0 and 16 (both included)"
            )

    def num_questions(self):
        """Returns the number of questions of the exam."""
        return len(self.questions)

    def num_choices(self):
        """Returns the number of choices of the questions.

           If not all the questions have the same number of choices,
           it returns the maximum. If there are no exams, it returns None.

        """
        num = [
            len(q.correct_choices) + len(q.incorrect_choices) for q in self.questions
        ]
        if len(num) > 0:
            return max(num)
        else:
            return None

    def homogeneous_num_choices(self):
        """Returns True if all the questions have the same number of choices.

        Returns None if the list of questions is empty.

        """
        num = [
            len(q.correct_choices) + len(q.incorrect_choices) for q in self.questions
        ]
        if len(num) > 0:
            return min(num) == max(num)
        else:
            return None

    def shuffle(self, model):
        """Shuffles questions and options within questions for the given model.

        """
        shuffled, permutations = self.questions.shuffle()
        self.shuffled_questions[model] = shuffled
        self.permutations[model] = permutations
        for question in self.questions:
            question.shuffle(model)

    def set_permutation(self, model, permutation):
        self.permutations[model] = [p[0] - 1 for p in permutation]
        self.shuffled_questions[model] = [
            self.questions[i] for i in self.permutations[model]
        ]
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


class QuestionsContainer:
    def __init__(self):
        self.groups = []

    def __len__(self):
        return sum(len(group) for group in self.groups)

    def __iter__(self):
        return self._iterate_questions()

    def __getitem__(self, index):
        if index < 0:
            pos = len(self) - index
        else:
            pos = index
        i = 0
        for group in self.groups:
            if i + len(group) > pos:
                return group[pos - i]
            i += len(group)
        raise IndexError("QuestionsContainer index out of range: {}".format(index))

    def append(self, element):
        if isinstance(element, QuestionsGroup):
            self.groups.append(element)
        else:
            self.groups.append(QuestionsGroup([element]))

    def shuffle(self):
        """Returns a tuple (list of questions, permutations) with data shuffled.

        Permutations is another list with the original position of each
        question. That is, question shuffled[i] was in the original list in
        permutations[i] position.

        It returns just a list of questions, without groupings.

        """
        to_sort = [(random.random(), item) for item in self.groups]
        questions = []
        permutations = []
        for _, group in sorted(to_sort):
            questions.extend(group.questions)
            permutations.extend(self._positions(group))
        return questions, permutations

    def _iterate_questions(self):
        for group in self.groups:
            for question in group:
                yield question

    def _positions(self, group):
        pos = 0
        for g in self.groups:
            if g is group:
                return list(range(pos, pos + len(g)))
            else:
                pos += len(g)
        raise ValueError("Group not in group container")


class QuestionsGroup:
    def __init__(self, questions):
        self.questions = questions

    def __len__(self):
        return len(self.questions)

    def __iter__(self):
        return iter(self.questions)

    def __getitem__(self, index):
        return self.questions[index]


class Question:
    def __init__(self):
        self.text = None
        self.correct_choices = []
        self.incorrect_choices = []
        self.shuffled_choices = {}
        self.permutations = {}

    def shuffle(self, model):
        shuffled, permutations = shuffle(self.correct_choices + self.incorrect_choices)
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
            raise Exception("Code and figure cannot be in the same block")
        if (
            self.in_choice
            and self.annex_pos != "center"
            and (self.code is not None or self.figure is not None)
        ):
            raise Exception("Figures and code in answers must be centered")
        if (
            self.code is not None
            and self.annex_pos == "center"
            and self.annex_width is not None
        ):
            raise Exception("Centered code cannot have width")
        if not self.in_choice and self.text is None:
            raise Exception("Questions must have a text")


def shuffle(data):
    """Returns a tuple (list, permutations) with data shuffled.

       Permutations is another list with the original position of each
       term. That is, shuffled[i] was in the original list in
       permutations[i] position.

    """
    to_sort = [(random.random(), item, pos) for pos, item in enumerate(data)]
    shuffled_data = []
    permutations = []
    for _, item, pos in sorted(to_sort):
        shuffled_data.append(item)
        permutations.append(pos)
    return shuffled_data, permutations
