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

import re
import csv

import openpyxl

from . import utils


_re_email = re.compile(r'^[a-zA-Z0-9._%-\+]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,6}$')


class Student:
    def __init__(self, student_id, full_name,
                 first_name, last_name, email,
                 db_id=None,
                 group_id=None, sequence_num=None, is_in_database=False):
        if full_name and (first_name or last_name):
            raise ValueError('Full name incompatible with first / last name')
        self.db_id = db_id
        self.student_id = student_id
        self.full_name = full_name
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.group_id = group_id
        self.sequence_num = sequence_num
        self.is_in_database = is_in_database

    @property
    def name(self):
        if self.full_name:
            return self.full_name
        elif self.last_name:
            if self.first_name:
                return '{0} {1}'.format(self.first_name, self.last_name)
            else:
                return self.last_name
        elif self.first_name:
            return self.first_name
        else:
            return ''

    @property
    def last_comma_first_name(self):
        if self.last_name:
            if self.first_name:
                return '{0}, {1}'.format(self.last_name, self.first_name)
            else:
                return self.last_name
        else:
            return self.name

    @property
    def id_and_name(self):
        if self.name:
            return ' '.join((self.student_id, self.name))
        else:
            return self.student_id

    @property
    def name_or_id(self):
        if self.name:
            return self.name
        elif self.student_id:
            return self.student_id
        else:
            return ''

    def __str__(self):
        return 'student: ' + self.id_and_name


class StudentGroup:
    def __init__(self, identifier, name):
        self.identifier = identifier
        self.name = name

    def __str__(self):
        return 'Group #{0.identifier} ({0.name})'.format(self)


def read_student_ids(filename):
    """Reads the list of student IDs from a file.

    Formats allowed: CSV-formatted file (tab-separated) and Excel 2010 (.xslx)

    Returns the results as a list of Student objects.

    """
    if filename.endswith('.xlsx'):
        return _read_from_xlsx(filename)
    else:
        return _read_from_csv(filename)

def _student_from_row(row):
    name1 = ''
    name2 = ''
    email = ''
    if len(row) == 0:
        raise utils.EyegradeException('Empty line in student list',
                                      key='error_student_list')
    student_id = row[0]
    _check_student_id(student_id)
    if len(row) > 1:
        name1 = row[1]
    if len(row) > 2:
        item = row[2]
        if _check_email(item):
            email = item
        else:
            name2 = item
    if len(row) > 3:
        item = row[3]
        if _check_email(item):
            email = item
    if not name2:
        full_name = name1
        first_name = ''
        last_name = ''
    else:
        full_name = ''
        first_name = name1
        last_name = name2
    return Student(student_id, full_name, first_name, last_name, email)

def _check_student_id(student_id):
    """Checks the student id.

    Raises the appropriate exception in case of error.

    """
    try:
        int(student_id)
    except:
        raise utils.EyegradeException( \
                            'Wrong id in student list: ' + student_id,
                            key='error_student_id')

def _check_email(email):
    """Checks syntactically an email address.

    Returns True if correct, False if incorrect.

    """
    if _re_email.match(email):
        return True
    else:
        return False

def _read_from_csv(filename):
    """Reads the list of student IDs from a CSV-formatted file (tab-separated).

    Returns the results as a list of Student objects.

    """
    with open(filename, newline='') as csvfile:
        try:
            dialect = csv.Sniffer().sniff(csvfile.read(1024))
        except csv.Error:
            dialect = csv.excel_tab
        csvfile.seek(0)
        reader = csv.reader(csvfile, dialect=dialect)
        student_ids = []
        for row in reader:
            if not _row_is_empty(row):
                student_ids.append(_student_from_row(row))
    return student_ids

def _read_from_xlsx(filename):
    wb = openpyxl.load_workbook(filename)
    ws = wb.active
    student_ids = []
    for row in ws.iter_rows():
        data = tuple(cell.value for cell in row)
        if not _row_is_empty(data):
            student_ids.append(_student_from_row(data))
    return student_ids

def _row_is_empty(row):
    for element in row:
        if element is not None and element != '':
            return False
    return True
