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
import copy

import eyegrade.students as students
import eyegrade.utils as utils


class TestStudent(unittest.TestCase):
    def test_full_name(self):
        student = students.Student("0000", "John Doe", None, None, "john@example.com")
        self.assertEqual(student.name, "John Doe")
        self.assertEqual(student.id_and_name, "0000 John Doe")
        self.assertEqual(student.name_or_id, "John Doe")

    def test_first_and_last_name(self):
        student = students.Student("0000", None, "John", "Doe", "john@example.com")
        self.assertEqual(student.name, "John Doe")
        self.assertEqual(student.id_and_name, "0000 John Doe")
        self.assertEqual(student.name_or_id, "John Doe")
        self.assertEqual(student.last_comma_first_name, "Doe, John")

    def test_last_name(self):
        student = students.Student("0000", None, None, "Doe", "doe@example.com")
        self.assertEqual(student.name, "Doe")
        self.assertEqual(student.id_and_name, "0000 Doe")
        self.assertEqual(student.name_or_id, "Doe")
        self.assertEqual(student.last_comma_first_name, "Doe")

    def test_first_name(self):
        student = students.Student("0000", None, "John", "", "john@example.com")
        self.assertEqual(student.name, "John")
        self.assertEqual(student.id_and_name, "0000 John")
        self.assertEqual(student.name_or_id, "John")
        self.assertEqual(student.last_comma_first_name, "John")

    def test_no_name(self):
        student = students.Student("0000", None, None, None, "doe@example.com")
        self.assertEqual(student.name, "")
        self.assertEqual(student.id_and_name, "0000")
        self.assertEqual(student.name_or_id, "0000")
        self.assertEqual(student.last_comma_first_name, "")

    def test_name_errors(self):
        self.assertRaises(
            ValueError,
            students.Student,
            "0000",
            "John Doe",
            "John",
            "",
            "doe@example.com",
        )
        self.assertRaises(
            ValueError,
            students.Student,
            "0000",
            "John Doe",
            "",
            "Doe",
            "doe@example.com",
        )
        self.assertRaises(
            ValueError,
            students.Student,
            "0000",
            "John Doe",
            "John",
            "Doe",
            "doe@example.com",
        )


class TestReadStudentsFromFile(unittest.TestCase):
    def setUp(self):
        self.students = [
            ("101010101", "Donald Duck", "Donald", "Duck", "duck@d.com"),
            ("202020202", "Marty McFly", "Marty", "McFly", "fly@d.com"),
            ("313131313", "Peter Pan", "Peter", "Pan", "pan@pan.com"),
        ]
        self.bad_students = [("1010a0101", "Bad Boy", "Bad", "Boy", "boy@bad.com")]
        self.non_ascii_students = [
            ("404040404", "Rey León", "Rey", "León", "lion@jungle.com")
        ]

    def _get_test_file_path(self, filename):
        dirname = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirname, filename)

    def test_empty(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, "test_file")
            with open(test_file, mode="w") as f:
                f.write("")
            student_list = students.read_students(test_file)
        self.assertEqual(student_list, [])

    def test_empty_with_header(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, "test_file")
            with open(test_file, mode="w") as f:
                f.write("header\n")
            student_list = students.read_students(test_file)
        self.assertEqual(student_list, [])

    def test_read_id(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, "test_file")
            with open(test_file, mode="w") as f:
                f.write("\n".join([s[0] for s in self.students]))
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], "", "", "", "") for s in self.students]
        self.assertEqual(data, key)

    def test_read_id_full_name(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, "test_file")
            with open(test_file, mode="w") as f:
                f.write("\n".join(["\t".join((s[0], s[1])) for s in self.students]))
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], s[1], "", "", "") for s in self.students]
        self.assertEqual(data, key)

    def test_read_id_full_name_email(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, "test_file")
            with open(test_file, mode="w") as f:
                f.write(
                    "\n".join(["\t".join((s[0], s[1], s[4])) for s in self.students])
                )
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], s[1], "", "", s[4]) for s in self.students]
        self.assertEqual(data, key)

    def test_read_id_name_surname(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, "test_file")
            with open(test_file, mode="w") as f:
                f.write(
                    "\n".join(["\t".join((s[0], s[2], s[3])) for s in self.students])
                )
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], "", s[2], s[3], "") for s in self.students]
        self.assertEqual(data, key)

    def test_read_id_name_surname_email(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, "test_file")
            with open(test_file, mode="w") as f:
                f.write(
                    "\n".join(
                        ["\t".join((s[0], s[2], s[3], s[4])) for s in self.students]
                    )
                )
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], "", s[2], s[3], s[4]) for s in self.students]
        self.assertEqual(data, key)

    def test_read_with_comma_separator(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, "test_file")
            with open(test_file, mode="w") as f:
                f.write(
                    "\n".join(
                        [",".join((s[0], s[2], s[3], s[4])) for s in self.students]
                    )
                )
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], "", s[2], s[3], s[4]) for s in self.students]
        self.assertEqual(data, key)

    def test_read_with_header(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, "test_file")
            with open(test_file, mode="w") as f:
                f.write("id\tname\tsurname\temail\n")
                f.write(
                    "\n".join(
                        ["\t".join((s[0], s[2], s[3], s[4])) for s in self.students]
                    )
                )
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [(s[0], "", s[2], s[3], s[4]) for s in self.students]
        self.assertEqual(data, key)

    def test_errors(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, "test_file")
            with open(test_file, mode="w") as f:
                f.write("error\nerror\n")
            test_file_2 = os.path.join(dir_name, "test_file_2")
            with open(test_file_2, mode="w") as f:
                f.write(
                    "\n".join(
                        [
                            "\t".join((s[0], s[1], s[4]))
                            for s in self.students + self.bad_students
                        ]
                    )
                )
            self.assertRaises(
                utils.EyegradeException, students.read_students, test_file
            )
            self.assertRaises(
                utils.EyegradeException, students.read_students, test_file_2
            )

    def test_non_ascii(self):
        with tempfile.TemporaryDirectory() as dir_name:
            test_file = os.path.join(dir_name, "test_file")
            with open(test_file, mode="w") as f:
                f.write(
                    "\n".join(
                        [
                            "\t".join((s[0], s[2], s[3], s[4]))
                            for s in self.students + self.non_ascii_students
                        ]
                    )
                )
            student_list = students.read_students(test_file)
        data = [_student_tuple(s) for s in student_list]
        key = [
            (s[0], "", s[2], s[3], s[4])
            for s in self.students + self.non_ascii_students
        ]
        self.assertEqual(data, key)

    def test_xlsx(self):
        test_file = self._get_test_file_path("student-list.xlsx")
        student_list = students.read_students(test_file)
        key = [
            students.Student("100000333", "", "Frodo", "Baggins", ""),
            students.Student("100777777", "", "Bugs", "Bunny", ""),
            students.Student("100999997", "", "Bastian B.", "Bux", ""),
            students.Student("100999991", "", "Harry", "Potter", ""),
            students.Student("100800003", "", "Lisa", "Simpson", ""),
        ]
        self.assertEqual(student_list, key)


class TestListings(unittest.TestCase):
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

    def test_listing_add(self):
        listing = students.GroupListing(students.StudentGroup(1, "G"), [])
        listing.add_students(self.students)
        self.assertEqual(listing.students, self.students)
        listing.add_students(self.more_students)
        self.assertEqual(listing.students, self.students + self.more_students)
        self.assertTrue(self.more_students[1].student_id in listing)

    def test_listing_find_duplicates(self):
        listing = students.GroupListing(None, list(self.students))
        new_students = [
            students.Student("313131313", "Peter", "", "", ""),
            self.more_students[0],
            self.more_students[1],
            students.Student("202020202", "Marty", "", "", ""),
        ]
        duplicates = listing.find_duplicates(new_students)
        key = [new_students[0], new_students[3]]
        self.assertEqual(duplicates, key)

    def test_listing_find_duplicates_2(self):
        listing = students.GroupListing(None, list(self.students))
        dup = copy.copy(self.more_students[0])
        dup.full_name = "Other Donkey"
        new_students = [
            self.more_students[0],
            self.more_students[1],
            dup,
            self.more_students[2],
        ]
        duplicates = listing.find_duplicates(new_students)
        key = [dup]
        self.assertEqual(duplicates, key)

    def test_listing_find_duplicates_3(self):
        listing = students.GroupListing(None, list(self.students))
        dup = copy.copy(self.students[1])
        dup.full_name = "Other Marty"
        new_students = [
            self.more_students[0],
            self.students[1],
            dup,
            self.more_students[1],
        ]
        duplicates = listing.find_duplicates(new_students)
        self.assertTrue(dup in duplicates)
        self.assertTrue(self.students[1] in duplicates)
        self.assertEqual(len(duplicates), 2)

    def test_listing_add_duplicates(self):
        listing = students.GroupListing(None, list(self.students))
        new_students = [
            students.Student("313131313", "Peter", "", "", ""),
            students.Student("909090909", "Donkey Kong", "", "", ""),
            students.Student("202020202", "Marty", "", "", ""),
        ]
        self.assertRaises(
            students.DuplicateStudentIdException, listing.add_students, new_students
        )

    def test_rank_students(self):
        # Test for issue #132
        listing = students.GroupListing(
            students.StudentGroup(1, "G"), list(self.students)
        )
        student_listings = students.StudentListings()
        student_listings.add_listing(listing)
        rank = zip([1.5, 1.5, 3], student_listings.iter_students())
        [student for score, student in sorted(rank, reverse=True)]


def _student_tuple(student):
    return (
        student.student_id,
        student.full_name,
        student.first_name,
        student.last_name,
        student.email,
    )
