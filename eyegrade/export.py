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

import csv
import enum

import openpyxl

from . import utils


class FileFormat(enum.Enum):
    CSV_TABS = 1
    XLSX = 2


def create_writer(file_name, file_format):
    if file_format == FileFormat.CSV_TABS:
        writer = CSVWriter(file_name, utils.csv_tabs_dialect)
    elif file_format == FileFormat.XLSX:
        writer = XLSXWriter(file_name)
    else:
        raise ValueError("Unknown file format: {}".format(file_format))
    return writer


class XLSXWriter:
    def __init__(self, file_name):
        self.file_name = file_name

    def __enter__(self):
        self.workbook = openpyxl.Workbook()
        self.current_sheet = self.workbook.active
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if traceback is None:
            self.workbook.save(self.file_name)
        self.current_sheet = None
        self.workbook = None

    def append_row(self, data):
        self.current_sheet.append(data)

    def append_sheet(self):
        self.current_sheet = self.workbook.create_sheet()

    def set_sheet_title(self, title):
        self.current_sheet.title = title

    def __str__(self):
        return "XLSXWriter({})".format(self.file_name)


class CSVWriter:
    def __init__(self, file_name, csv_dialect):
        self.file_name = file_name
        self.csv_dialect = csv_dialect

    def __enter__(self):
        self.file = open(self.file_name, "w")
        self.writer = csv.writer(self.file, dialect=self.csv_dialect)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.close()

    def append_row(self, data):
        self.writer.writerow(data)

    def append_sheet(self):
        pass

    def set_sheet_title(self, title):
        pass

    def __str__(self):
        return "CSVWriter({})".format(self.file_name)


class GradesColumn:
    """Extract a field from a Student or Exam object, for exporting data"""

    STUDENT_KEYS = {
        "student_id": "Id",
        "name": "Name",
        "last_name": "Last name",
        "first_name": "First name",
    }
    EXAM_KEYS = {
        "exam_id": "Sequence number",
        "model": "Model",
        "correct": "Correct",
        "incorrect": "Incorrect",
        "score": "Score",
        "answers": None,
    }

    def __init__(self, column_key, num_questions=None):
        if column_key in GradesColumn.STUDENT_KEYS:
            self.extract = self._extract_from_student
            self.key = column_key
            self.headers = (GradesColumn.STUDENT_KEYS[column_key],)
        elif column_key in GradesColumn.EXAM_KEYS:
            self.extract = self._extract_from_exam
            self.key = column_key
            if column_key == "answers":
                if num_questions is not None:
                    self.headers = tuple(
                        "Q{}".format(i) for i in range(1, num_questions + 1)
                    )
                else:
                    raise ValueError("num_questions needs to be set")
            else:
                self.headers = (GradesColumn.EXAM_KEYS[column_key],)
        else:
            raise ValueError("Unknown column key: {}".format(column_key))

    def __str__(self):
        return "GradesColumn({})".format(self.key)

    def _extract_from_student(self, exam):
        return (getattr(exam["student"], self.key),)

    def _extract_from_exam(self, exam):
        if self.key == "answers":
            return exam["answers"]
        else:
            return (exam[self.key],)


class SortBy(enum.Enum):
    STUDENT_LIST = 1
    LAST_NAME = 2
    GRADING_SEQUENCE = 3


class GradesExportHelper:
    """Manage the options for exporting grades."""

    def __init__(self, exam_config, student_groups):
        self.student_groups = student_groups
        self.num_questions = exam_config.num_questions
        self.survey_mode = exam_config.survey_mode
        self.columns = []
        self.file_name = None
        self.file_format = None
        self.group = None
        self.one_sheet = None
        self.all_students = None
        self.sort_by = None
        self.add_column_headers = None
        self.export_by_exam = False

    def export_columns(self, keys):
        self.columns = [self._create_column(key) for key in keys]

    def export_group(self, index):
        self.group = self.student_groups[index]
        self.one_sheet = True
        self.export_by_exam = False

    def export_all_groups(self, one_sheet):
        self.group = None
        self.one_sheet = one_sheet
        self.export_by_exam = False

    def export_all_exams(self):
        self.group = None
        self.one_sheet = True
        self.export_by_exam = True

    def data(self, exam):
        data = []
        for column in self.columns:
            data.extend(column.extract(exam))
        return data

    def column_headers(self):
        data = []
        for column in self.columns:
            data.extend(column.headers)
        return data

    def iter_groups(self):
        if self.export_by_exam:
            yield (None, "Exams")
        elif self.group is None:
            if self.one_sheet:
                yield (None, "Group")
            else:
                for group in self.student_groups:
                    yield (group, group.name)
        else:
            yield (self.group, self.group.name)

    def create_writer(self):
        writer = create_writer(self.file_name, self.file_format)
        return writer

    def _create_column(self, key):
        return GradesColumn(key, num_questions=self.num_questions)
