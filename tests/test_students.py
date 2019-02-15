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
# <http://www.gnu.org/licenses/>.
#

import unittest
import os.path
import tempfile

import eyegrade.students as students
import eyegrade.utils as utils


class TestStudent(unittest.TestCase):

    def test_full_name(self):
        student = students.Student('0000', 'John Doe', None, None,
                                   'john@example.com')
        self.assertEqual(student.name, 'John Doe')
        self.assertEqual(student.id_and_name, '0000 John Doe')
        self.assertEqual(student.name_or_id, 'John Doe')

    def test_first_and_last_name(self):
        student = students.Student('0000', None, 'John', 'Doe',
                                   'john@example.com')
        self.assertEqual(student.name, 'John Doe')
        self.assertEqual(student.id_and_name, '0000 John Doe')
        self.assertEqual(student.name_or_id, 'John Doe')
        self.assertEqual(student.last_comma_first_name, 'Doe, John')

    def test_last_name(self):
        student = students.Student('0000', None, None, 'Doe',
                                   'doe@example.com')
        self.assertEqual(student.name, 'Doe')
        self.assertEqual(student.id_and_name, '0000 Doe')
        self.assertEqual(student.name_or_id, 'Doe')
        self.assertEqual(student.last_comma_first_name, 'Doe')

    def test_first_name(self):
        student = students.Student('0000', None, 'John', '',
                                   'john@example.com')
        self.assertEqual(student.name, 'John')
        self.assertEqual(student.id_and_name, '0000 John')
        self.assertEqual(student.name_or_id, 'John')
        self.assertEqual(student.last_comma_first_name, 'John')

    def test_no_name(self):
        student = students.Student('0000', None, None, None,
                                   'doe@example.com')
        self.assertEqual(student.name, '')
        self.assertEqual(student.id_and_name, '0000')
        self.assertEqual(student.name_or_id, '0000')
        self.assertEqual(student.last_comma_first_name, '')

    def test_name_errors(self):
        self.assertRaises(ValueError, students.Student,
                          '0000', 'John Doe', 'John', '',
                          'doe@example.com')
        self.assertRaises(ValueError, students.Student,
                          '0000', 'John Doe', '', 'Doe',
                          'doe@example.com')
        self.assertRaises(ValueError, students.Student,
                          '0000', 'John Doe', 'John', 'Doe',
                          'doe@example.com')


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
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, 'test_file')
            with open(test_file, mode='w') as f:
                f.write('')
            student_list = students.read_students(test_file)
        self.assertEqual(student_list, [])

    def test_empty_with_header(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, 'test_file')
            with open(test_file, mode='w') as f:
                f.write('header\n')
            student_list = students.read_students(test_file)
        self.assertEqual(student_list, [])

    def test_read_id(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, 'test_file')
            with open(test_file, mode='w') as f:
                f.write('\n'.join([s[0] for s in self.students]))
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], '', '', '', '') for s in self.students]
        self.assertEqual(data, key)

    def test_read_id_full_name(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, 'test_file')
            with open(test_file, mode='w') as f:
                f.write('\n'.join(['\t'.join((s[0], s[1]))
                                   for s in self.students]))
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], s[1], '', '', '') for s in self.students]
        self.assertEqual(data, key)

    def test_read_id_full_name_email(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, 'test_file')
            with open(test_file, mode='w') as f:
                f.write('\n'.join(['\t'.join((s[0], s[1], s[4]))
                                   for s in self.students]))
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], s[1], '', '', s[4]) for s in self.students]
        self.assertEqual(data, key)

    def test_read_id_name_surname(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, 'test_file')
            with open(test_file, mode='w') as f:
                f.write('\n'.join(['\t'.join((s[0], s[2], s[3]))
                                   for s in self.students]))
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], '', s[2], s[3], '') for s in self.students]
        self.assertEqual(data, key)

    def test_read_id_name_surname_email(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, 'test_file')
            with open(test_file, mode='w') as f:
                f.write('\n'.join(['\t'.join((s[0], s[2], s[3], s[4]))
                                   for s in self.students]))
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], '', s[2], s[3], s[4]) for s in self.students]
        self.assertEqual(data, key)

    def test_read_with_comma_separator(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, 'test_file')
            with open(test_file, mode='w') as f:
                f.write('\n'.join([','.join((s[0], s[2], s[3], s[4]))
                                   for s in self.students]))
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], '', s[2], s[3], s[4]) for s in self.students]
        self.assertEqual(data, key)

    def test_read_with_header(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, 'test_file')
            with open(test_file, mode='w') as f:
                f.write('id\tname\tsurname\temail\n')
                f.write('\n'.join(['\t'.join((s[0], s[2], s[3], s[4]))
                                   for s in self.students]))
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], '', s[2], s[3], s[4]) for s in self.students]
        self.assertEqual(data, key)

    def test_errors(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, 'test_file')
            with open(test_file, mode='w') as f:
                f.write('error\nerror\n')
            test_file_2 = os.path.join(dir_name, 'test_file_2')
            with open(test_file_2, mode='w') as f:
                f.write('\n'.join(['\t'.join((s[0], s[1], s[4]))
                                for s in self.students + self.bad_students]))
            self.assertRaises(utils.EyegradeException,
                              students.read_students,
                              test_file)
            self.assertRaises(utils.EyegradeException,
                              students.read_students,
                              test_file_2)

    def test_non_ascii(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, 'test_file')
            with open(test_file, mode='w') as f:
                f.write('\n'.join(['\t'.join((s[0], s[2], s[3], s[4]))
                        for s in self.students + self.non_ascii_students]))
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], '', s[2], s[3], s[4])
               for s in self.students + self.non_ascii_students]
        self.assertEqual(data, key)


def _student_tuple(student):
    return (
        student.student_id,
        student.full_name,
        student.first_name,
        student.last_name,
        student.email,
    )
