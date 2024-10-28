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

import pathlib

from .. import exams
from .. import sessiondb
from . import core


def compute_stats(
    exam_config: exams.ExamConfig, exams: list[exams.Exam]
) -> core.ExamStats:
    import pdb

    pdb.set_trace()
    num_choices = max(exam_config.num_options)
    if exam_config.permutations:
        permutations = core.ExamPermutations(
            exam_config.num_questions,
            num_choices,
            "0",
            exam_config.permutations,
        )
    else:
        permutations = None
    stats = core.ExamStats(
        exam_config.num_questions,
        num_choices,
        exam_config.solutions,
        permutations,
    )
    for exam in exams:
        stats.count_answers(exam.decisions.answers, exam.decisions.model)
    return stats


def compute_stats_from_session(session_path: pathlib.Path) -> core.ExamStats:
    with sessiondb.SessionDB(session_path, open=False) as session:
        return compute_stats(session.exam_config, session.read_exams())
