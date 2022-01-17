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

import eyegrade.students as students
import eyegrade.exams as exams


class TestRankStudentIds(unittest.TestCase):
    def test_different_id_len(self):
        # Test for issue #155
        student_list = [
            students.Student("101010101", "Donald Duck", "", "", ""),
            students.Student("202020202", "Marty McFly", "", "", ""),
            students.Student("313131313", "Peter Pan", "", "", ""),
            students.Student("12345678", "Shorter ID", "", "", ""),
            students.Student("1234567890", "Longer ID", "", "", ""),
        ]
        listing = students.GroupListing(students.StudentGroup(1, "G"), [])
        listing.add_students(student_list)
        listings = students.StudentListings()
        listings.add_listing(listing)
        scores = []
        for i in range(10):
            scores.append([])
            for _ in range(10):
                scores[i].append(0.1)
        for i, digit in enumerate(student_list[1].student_id):
            scores[i][int(digit)] = 1.0
        exam = _MockExamForScores(student_list[1].student_id, scores, listings)
        rank = exam.rank_students()


class _MockExamForScores(exams.Exam):
    def __init__(self, detected_id, id_scores, student_listings):
        self.decisions = _MockExamDecisions(detected_id, id_scores)
        self.student_listings = student_listings


class _MockExamDecisions:
    def __init__(self, detected_id, id_scores):
        self.detected_id = detected_id
        self.id_scores = id_scores
