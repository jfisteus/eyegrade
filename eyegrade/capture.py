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

import cv2

from . import geometry
from . import utils
from . import scoring
from . import images

_color_blue = (255, 0, 0)
_color_good = (0, 210, 0)
_color_bad = (0, 0, 255)
_color_dot_bad = (255, 0, 0)
_color_dot_blank = (192, 0, 192)


class CellGeometry:
    def __init__(self, plu, pru, pld, prd, center, diagonal):
        """Receives the four corners of the cell, center point and diagonal.

        If center or diagonal are None, they are automatically computed
        from the values of the corners.

        """
        self.plu = plu
        self.pru = pru
        self.pld = pld
        self.prd = prd
        if center is not None:
            self.center = center
        else:
            self.center = geometry.rect_center(plu, pru, pld, prd)
        if diagonal is not None:
            self.diagonal = diagonal
        else:
            self.diagonal = geometry.distance(plu, prd)

    def corners(self):
        """Returns a tuple (plu, pru, pld, prd) with the cell corners."""
        return (self.plu, self.pru, self.pld, self.prd)


class ExamDecisions:
    def __init__(
        self, success, answers, detected_id, id_scores, model=None, infobits=None
    ):
        self.success = success
        self.answers = answers
        self.detected_id = detected_id
        self.id_scores = id_scores
        if model is not None:
            self.model = model
        elif infobits:
            self.model = utils.decode_model(infobits)
        else:
            self.model = None
        self.student = None
        self.students_rank = []

    def change_answer(self, question, answer):
        self.answers[question] = answer

    def set_students_rank(self, students_rank):
        self.students_rank = students_rank

    def set_student(self, student):
        self.student = student


class ExamCapture:
    """Capture of an exam, including the image, cell geometry and drawing."""

    def __init__(self, image, answer_cells, id_cells, progress=1.0):
        """Creates a new ExamCapture object.

        `image`: original capture of the exam (as captured by opencv);
        `answer_cells`: bi-dimensional list of num_questions x num_choices
                        CellGeometry objects. Each one represents an
                        answer cell.
        `id_cells`: list of num_digits CellGeometry objects. Each one
                    represents a digit cell for the student id (from
                    left to right).
        `progress`: progress ratio of the capture. Set 1.0 for exams in which
                    all the features have been detected.

        """
        self.image_raw = image
        self.image_drawn = None
        self.answer_cells = answer_cells
        self.id_cells = id_cells
        self.progress = progress
        self.reset_image()

    def has_answer_cells(self):
        return self.answer_cells is not None and len(self.answer_cells) > 0

    def has_id_cells(self):
        return self.id_cells is not None and len(self.id_cells) > 0

    def get_cell_clicked(self, point):
        """Determines the cell to which the given point corresponds.

        Returns (num_question, num_choice) or None if no cell corresponds.

        """
        min_dst = float("inf")
        num_question = None
        num_choice = None
        closest_cell = None
        for i, cells in enumerate(self.answer_cells):
            for j, cell in enumerate(cells):
                dst = geometry.distance(point, cell.center)
                if dst < min_dst:
                    min_dst = dst
                    num_question = i
                    num_choice = j + 1
                    closest_cell = cell
        if closest_cell is not None and min_dst <= closest_cell.diagonal / 2:
            return (num_question, num_choice)
        else:
            return (None, None)

    def reset_image(self):
        """Resets the drawn image by cloning the original image.

        All the drawings are lost.

        """
        if self.image_raw is not None:
            self.image_drawn = self.image_raw.copy()

    def save_image_drawn(self, filename):
        assert self.image_drawn is not None
        save_image(filename, self.image_drawn)

    def save_image_raw(self, filename):
        save_image(filename, self.image_raw)

    def draw_status(self):
        assert self.image_drawn is not None
        self._draw_status_bar()

    def draw_corner(self, point):
        assert self.image_drawn is not None
        cv2.circle(self.image_drawn, point, 4, _color_blue, thickness=1)

    def draw_answers(self, score):
        assert self.image_drawn is not None
        if score.answers:
            if score.solutions:
                self._draw_answers_solutions(score)
            else:
                self._draw_answers_no_solutions(score)

    def _draw_status_bar(self):
        x0 = images.get_width(self.image_drawn) - 60
        y0 = 10
        width = 50
        height = 20
        p0 = (x0, y0)
        p1 = geometry.round_point((x0 + self.progress * width, y0 + height))
        p2 = (x0 + width, y0 + height)
        cv2.rectangle(self.image_drawn, p0, p2, _color_blue)
        cv2.rectangle(self.image_drawn, p0, p1, _color_blue, thickness=-1)

    def _draw_answers_solutions(self, score):
        for answer, question_solutions, status, cells in zip(
            score.answers, score.solutions, score.answer_status, self.answer_cells
        ):
            if status == scoring.QuestionScores.CORRECT:
                self._draw_cell_circle(cells[answer - 1], _color_good)
            elif status == scoring.QuestionScores.INCORRECT:
                self._draw_cell_circle(cells[answer - 1], _color_bad)
                for solution in question_solutions:
                    self._draw_cell_center(cells[solution - 1], _color_dot_bad)
            elif status == scoring.QuestionScores.BLANK:
                for solution in question_solutions:
                    self._draw_cell_center(cells[solution - 1], _color_dot_blank)
            elif status == scoring.QuestionScores.VOID:
                self._draw_void_question(cells)

    def _draw_answers_no_solutions(self, score):
        for answer, cells in zip(score.answers, self.answer_cells):
            if answer > 0:
                self._draw_cell_circle(cells[answer - 1], _color_blue)

    def _draw_cell_circle(self, cell, color):
        radius = int(round(cell.diagonal / 3.5))
        cv2.circle(self.image_drawn, cell.center, radius, color, thickness=2)

    def _draw_cell_center(self, cell, color):
        cv2.circle(self.image_drawn, cell.center, 4, color, thickness=-1)

    def _draw_void_question(self, cells):
        cv2.line(
            self.image_drawn, cells[0].center, cells[-1].center, _color_bad, thickness=3
        )


def save_image(filename, image):
    cv2.imwrite(filename, image)
