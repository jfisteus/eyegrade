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
import os.path
import tempfile

import eyegrade.sessiondb as sessiondb
import eyegrade.exams as exams
import eyegrade.students as students


class TestSessionDB(unittest.TestCase):
    def setUp(self):
        self.students = [
            students.Student("101010101", "Donald Duck", "", "", ""),
            students.Student("202020202", "Marty McFly", "", "", ""),
            students.Student("313131313", "Peter Pan", "", "", ""),
        ]
        self.more_students = [
            students.Student("909090909", "Donkey Kong", "", "", ""),
            students.Student("818181818", "Pinoccio", "", "", ""),
            students.Student("555555555", "Gump", "", "", ""),
        ]

    def _get_test_file_path(self, filename):
        dirname = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirname, filename)

    def test_exam_data(self):
        exam_config = exams.ExamConfig(filename=self._get_test_file_path("test.eye"))
        exam_config.capture_pattern = "exam-{student-id}-{seq-number}.png"
        listing = students.GroupListing(students.StudentGroup(1, "G"), [])
        listing.add_students(self.students)
        listings = students.StudentListings()
        listings.add_listing(listing)
        with tempfile.TemporaryDirectory() as dir_name:
            session_dir = os.path.join(dir_name, "test_session")
            sessiondb.create_session_directory(session_dir, exam_config, listings)
            session = sessiondb.SessionDB(session_dir)
            # Loading a session always sets variations to a list of zeroes
            # instead of the default empty dictionary.
            # Comparison would fail:
            session.exam_config.variations = {}
            self.assertEqual(session.exam_config, exam_config)

    def test_exam_data_weights(self):
        exam_config = exams.ExamConfig(
            filename=self._get_test_file_path("test-weights.eye")
        )
        exam_config.capture_pattern = "exam-{student-id}-{seq-number}.png"
        listing = students.GroupListing(students.StudentGroup(1, "G"), [])
        listing.add_students(self.students)
        listings = students.StudentListings()
        listings.add_listing(listing)
        with tempfile.TemporaryDirectory() as dir_name:
            session_dir = os.path.join(dir_name, "test_session")
            sessiondb.create_session_directory(session_dir, exam_config, listings)
            session = sessiondb.SessionDB(session_dir)
            # Loading a session always sets variations to a list of zeroes
            # instead of the default empty dictionary.
            # Comparison would fail:
            session.exam_config.variations = {}
            self.assertEqual(session.exam_config, exam_config)

    def test_student_list(self):
        exam_config = exams.ExamConfig(filename=self._get_test_file_path("test.eye"))
        exam_config.capture_pattern = "exam-{student-id}-{seq-number}.png"
        listing = students.GroupListing(students.StudentGroup(1, "G"), [])
        listing.add_students(self.students)
        listings = students.StudentListings()
        listings.add_listing(listing)
        with tempfile.TemporaryDirectory() as dir_name:
            session_dir = os.path.join(dir_name, "test_session")
            sessiondb.create_session_directory(session_dir, exam_config, listings)
            session = sessiondb.SessionDB(session_dir)
            session.student_listings[0].add_students(self.more_students)
            session.close()
            session = sessiondb.SessionDB(session_dir)
            student_list = list(session.student_listings[0])
            self.assertEqual(
                len(student_list), len(self.students) + len(self.more_students)
            )
            for student_1, student_2 in zip(self.students, student_list):
                self.assertEqual(student_1.name, student_2.name)
                self.assertEqual(student_1.student_id, student_2.student_id)
            for student_1, student_2 in zip(
                self.more_students, student_list[len(self.students) :]
            ):
                self.assertEqual(student_1.name, student_2.name)
                self.assertEqual(student_1.student_id, student_2.student_id)
