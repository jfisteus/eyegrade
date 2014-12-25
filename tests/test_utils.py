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
import unittest

from eyegrade.utils import Student

class TestStudent(unittest.TestCase):

    def test_full_name(self):
        student = Student(1, '0000', 'John Doe', None, None,
                          'john@example.com', 2, 3)
        self.assertEqual(student.name, 'John Doe')
        self.assertEqual(student.id_and_name, '0000 John Doe')
        self.assertEqual(student.name_or_id, 'John Doe')

    def test_first_and_last_name(self):
        student = Student(1, '0000', None, 'John', 'Doe',
                          'john@example.com', 2, 3)
        self.assertEqual(student.name, 'John Doe')
        self.assertEqual(student.id_and_name, '0000 John Doe')
        self.assertEqual(student.name_or_id, 'John Doe')
        self.assertEqual(student.last_comma_first_name, 'Doe, John')

    def test_last_name(self):
        student = Student(1, '0000', None, None, 'Doe',
                          'doe@example.com', 2, 3)
        self.assertEqual(student.name, 'Doe')
        self.assertEqual(student.id_and_name, '0000 Doe')
        self.assertEqual(student.name_or_id, 'Doe')
        self.assertEqual(student.last_comma_first_name, 'Doe')

    def test_first_name(self):
        student = Student(1, '0000', None, 'John', '',
                          'john@example.com', 2, 3)
        self.assertEqual(student.name, 'John')
        self.assertEqual(student.id_and_name, '0000 John')
        self.assertEqual(student.name_or_id, 'John')
        self.assertEqual(student.last_comma_first_name, 'John')

    def test_no_name(self):
        student = Student(1, '0000', None, None, None,
                          'doe@example.com', 2, 3)
        self.assertEqual(student.name, '')
        self.assertEqual(student.id_and_name, '0000')
        self.assertEqual(student.name_or_id, '0000')
        self.assertEqual(student.last_comma_first_name, '')

    def test_name_errors(self):
        self.assertRaises(ValueError, Student,
                          1, '0000', 'John Doe', 'John', '',
                          'doe@example.com', 2, 3)
        self.assertRaises(ValueError, Student,
                          1, '0000', 'John Doe', '', 'Doe',
                          'doe@example.com', 2, 3)
        self.assertRaises(ValueError, Student,
                          1, '0000', 'John Doe', 'John', 'Doe',
                          'doe@example.com', 2, 3)
