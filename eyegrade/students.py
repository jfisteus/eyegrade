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

import abc
import re
import csv
import itertools
import enum
import io
from typing import Iterator, Optional, Iterable, Union

import openpyxl

from . import utils

re_email = r"^[a-zA-Z0-9._%-\+]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,6}$"
_re_email = re.compile(re_email)
_re_student_id = re.compile(r"^[0-9]+$")


class Student:
    student_id: str
    full_name: str
    first_name: str
    last_name: str
    email: str
    db_id: Optional[int]
    group_id: Optional[int]
    sequence_num: Optional[int]
    is_in_database: bool

    def __init__(
        self,
        student_id: str,
        full_name: str,
        first_name: str,
        last_name: str,
        email: str,
        db_id: Optional[int] = None,
        group_id: Optional[int] = None,
        sequence_num: Optional[int] = None,
        is_in_database: bool = False,
    ) -> None:
        if full_name and (first_name or last_name):
            raise ValueError("Full name incompatible with first / last name")
        self.db_id = db_id
        self.student_id = student_id
        self.full_name = full_name
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.group_id = group_id
        self.sequence_num = sequence_num
        self.is_in_database = is_in_database
        self.is_duplicate = False

    @property
    def name(self) -> str:
        if self.full_name:
            return self.full_name
        elif self.last_name:
            if self.first_name:
                return "{0} {1}".format(self.first_name, self.last_name)
            else:
                return self.last_name
        elif self.first_name:
            return self.first_name
        else:
            return ""

    @property
    def last_comma_first_name(self) -> str:
        if self.last_name:
            if self.first_name:
                return "{0}, {1}".format(self.last_name, self.first_name)
            else:
                return self.last_name
        else:
            return self.name

    @property
    def id_and_name(self) -> str:
        if self.name:
            return " ".join((self.student_id, self.name))
        else:
            return self.student_id

    @property
    def name_or_id(self) -> str:
        if self.name:
            return self.name
        elif self.student_id:
            return self.student_id
        else:
            return ""

    def __lt__(self, other: "Student") -> bool:
        return self.student_id < other.student_id

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Student):
            return self.student_id == other.student_id
        else:
            return False

    def __str__(self) -> str:
        return "student: " + self.id_and_name


class StudentGroup:
    identifier: int
    name: str

    def __init__(self, identifier: int, name: str) -> None:
        self.identifier = identifier
        self.name = name

    def __str__(self) -> str:
        return "Group #{0.identifier} ({0.name})".format(self)


class GroupListing:
    group: StudentGroup
    students: list[Student]
    parent: Optional["StudentListings"]
    _students_dict: dict[str, Student]

    def __init__(self, group: StudentGroup, students: Iterable[Student]) -> None:
        self.group = group
        self.students = list(students)
        self.parent = None
        self._students_dict = {s.student_id: s for s in students}

    def student(self, student_id: str) -> Optional[Student]:
        return self._students_dict.get(student_id, None)

    def add_students(self, student_list: list[Student]) -> None:
        if student_list:
            if self.parent is not None:
                duplicates = self.parent.find_duplicates(student_list)
            else:
                duplicates = self.find_duplicates(student_list)
            if not duplicates:
                if student_list[0].sequence_num is None:
                    self._update_sequence_num(student_list)
                self.students.extend(student_list)
                for student in student_list:
                    student.group_id = self.group.identifier
                self._students_dict.update({s.student_id: s for s in student_list})
            else:
                raise DuplicateStudentIdException(duplicates)

    def remove_students(self, students: Iterable[Student]) -> None:
        for student in students:
            if student.student_id in self._students_dict:
                del self._students_dict[student.student_id]
                self.students.remove(student)

    def rename(self, new_name: str) -> None:
        self.group.name = new_name

    def find_duplicates(self, students: Iterable[Student]) -> list[Student]:
        non_duplicates, duplicates = _duplicate_student_ids(students)
        duplicates.extend([s for s in non_duplicates if s.student_id in self])
        return duplicates

    def __len__(self) -> int:
        return len(self.students)

    def __getitem__(self, key: str) -> Student:
        return self._students_dict[key]

    def __iter__(self) -> Iterator[Student]:
        return iter(self.students)

    def __contains__(self, student_id: str) -> bool:
        return student_id in self._students_dict

    def __str__(self) -> str:
        return "GroupListing({}, {} students)".format(self.group, len(self.students))

    def _update_sequence_num(self, students: list[Student]) -> None:
        if self.students:
            highest_sequence_num = max(
                s.sequence_num for s in self.students if s.sequence_num is not None
            )
            first_num = highest_sequence_num + 1
        else:
            first_num = 1
        for i, student in enumerate(students):
            student.sequence_num = first_num + i


class StudentListings:
    listings: list[GroupListing]
    max_group_id: int

    def __init__(self):
        self.listings = []
        self.max_group_id = -1

    def add_listing(self, listing: GroupListing) -> None:
        duplicates = self.find_duplicates(listing.students)
        if not duplicates:
            listing.parent = self
            self.listings.append(listing)
            group_id = listing.group.identifier
            if group_id > self.max_group_id:
                self.max_group_id = group_id
        else:
            raise DuplicateStudentIdException(duplicates)

    def create_listing(self, group: StudentGroup) -> GroupListing:
        if group.identifier is None:
            group.identifier = self.max_group_id + 1
        listing = GroupListing(group, [])
        self.add_listing(listing)
        return listing

    def remove_at(self, index: int) -> None:
        del self.listings[index]

    def iter_students(self) -> Iterator[Student]:
        return itertools.chain(*self.listings)

    def sorted_students(self, key=lambda x: x.student_id) -> list[Student]:
        return sorted([student for student in self.iter_students()], key=key)

    def student(self, student_id: str) -> Optional[Student]:
        student = None
        for listing in self.listings:
            student = listing.student(student_id)
            if student is not None:
                break
        return student

    def listing_by_group_id(self, group_id: int) -> GroupListing:
        for listing in self.listings:
            if listing.group.identifier == group_id:
                return listing
        raise KeyError(group_id)

    def find_duplicates(self, students: Iterable[Student]) -> list[Student]:
        non_duplicates, duplicates = _duplicate_student_ids(students)
        duplicates.extend([s for s in non_duplicates if s.student_id in self])
        return duplicates

    def __len__(self) -> int:
        return len(self.listings)

    def __getitem__(self, key: int) -> GroupListing:
        return self.listings[key]

    def __contains__(self, student_id: str) -> bool:
        for listing in self.listings:
            if student_id in listing:
                return True
        return False

    def __str__(self) -> str:
        return "StudentListings({} groups: {})".format(
            len(self.listings), [len(listing) for listing in self.listings]
        )


def _duplicate_student_ids(
    students: Iterable[Student],
) -> tuple[list[Student], list[Student]]:
    non_duplicates = []
    duplicates = []
    student_ids_set = set()
    for student in students:
        if student.student_id not in student_ids_set:
            student_ids_set.add(student.student_id)
            non_duplicates.append(student)
        else:
            duplicates.append(student)
    return non_duplicates, duplicates


class CantRemoveGroupException(utils.EyegradeException):
    def __init__(self, message: str):
        super().__init__(message)


class DuplicateStudentIdException(utils.EyegradeException):
    def __init__(self, duplicates: Iterable[Student]):
        super().__init__("Some ids are already in the student listings")
        self.duplicates = duplicates


class StudentReader:
    file_name: str
    column_map: Optional["StudentColumnMap"]
    iterator: Iterator[Union[tuple[str], list[str]]]

    def __init__(
        self, file_name: str, column_map: Optional["StudentColumnMap"] = None
    ) -> None:
        self.file_name = file_name
        self.column_map = column_map
        # To be overwritten by subclasses:
        self.iterator = iter([])

    @staticmethod
    def create(file_name: str) -> "StudentReader":
        if file_name.endswith(".xlsx"):
            return XLSXStudentReader(file_name)
        else:
            return CSVStudentReader(file_name)

    @abc.abstractmethod
    def __enter__(self) -> "StudentReader": ...

    @abc.abstractmethod
    def __exit__(self, exception_type, exception_value, traceback) -> None: ...

    def students(self) -> Iterator[Student]:
        first_line = True
        for row in self.iterator:
            if not StudentReader._row_is_empty(row):
                if self.column_map is None:
                    self.column_map = StudentColumnMap.guess_map(row)
                    if not self.column_map.is_valid():
                        if first_line:
                            first_line = False
                            self.column_map = None
                            continue
                        else:
                            raise utils.EyegradeException("", key="error_student_list")
                try:
                    student = self.column_map.student(row)
                    yield student
                except utils.EyegradeException:
                    if not first_line:
                        raise
                first_line = False

    @staticmethod
    def _row_is_empty(row: Iterable[Optional[str]]) -> bool:
        for element in row:
            if element is not None and element != "":
                return False
        return True


class CSVStudentReader(StudentReader):
    file: Optional[io.TextIOWrapper]

    def __init__(self, file_name: str) -> None:
        super().__init__(file_name)
        self.file = None

    def __enter__(self) -> StudentReader:
        dialect: type[csv.Dialect]
        self.file = open(self.file_name, newline="")
        file_sample = self.file.read(1024)
        if "\t" in file_sample:
            # The sniffer doesn't guess correctly when a TSV file
            # contains names with commas
            dialect = csv.excel_tab
        else:
            try:
                dialect = csv.Sniffer().sniff(file_sample)
            except csv.Error:
                dialect = csv.excel_tab
        self.file.seek(0)
        self.iterator = csv.reader(self.file, dialect=dialect)
        return self

    def __exit__(self, exception_type, exception_value, traceback) -> None:
        if self.file is not None:
            self.file.close()


class XLSXStudentReader(StudentReader):
    workbook: openpyxl.Workbook

    def __init__(self, file_name: str) -> None:
        super().__init__(file_name)
        self.workbook = None
        self.iterator = None

    def __enter__(self) -> StudentReader:
        self.workbook = openpyxl.load_workbook(self.file_name, read_only=True)
        self.iterator = self.iter_rows(self.workbook.active)
        return self

    def __exit__(self, exception_type, exception_value, traceback) -> None:
        self.workbook.close()

    def iter_rows(
        self, work_sheet: openpyxl.worksheet.worksheet.Worksheet
    ) -> Iterator[tuple]:
        for row in work_sheet.iter_rows():
            yield tuple(cell.value for cell in row)


def read_students(file_name: str) -> list[Student]:
    """Reads the list of students from a file.

    Formats allowed: CSV-formatted file (tab-separated) and Excel 2010 (.xslx)

    Returns the results as a list of Student objects.

    """
    with StudentReader.create(file_name) as reader:
        return list(reader.students())


class StudentColumn(enum.Enum):
    ID = 1
    FULL_NAME = 2
    FIRST_NAME = 3
    LAST_NAME = 4
    NAME = 5
    EMAIL = 6
    SEQUENCE_NUM = 7
    UNKNOWN = 8


ATTR_NAME = {
    StudentColumn.ID: "student_id",
    StudentColumn.FULL_NAME: "full_name",
    StudentColumn.FIRST_NAME: "first_name",
    StudentColumn.LAST_NAME: "last_name",
    StudentColumn.NAME: "name",
    StudentColumn.EMAIL: "email",
    StudentColumn.SEQUENCE_NUM: "sequence_num",
    StudentColumn.UNKNOWN: "-",
}


class StudentColumnMap:
    student_column: list[StudentColumn]

    def __init__(self, num_columns=None, columns=None):
        if not ((num_columns is None) ^ (columns is None)):
            raise ValueError("num_columns or columns required, but not both")
        if num_columns is not None:
            self.columns = [StudentColumn.UNKNOWN] * num_columns
        else:
            self.columns = list(columns)

    def set_column(self, index: int, column: StudentColumn) -> bool:
        if column not in self.columns:
            self.columns[index] = column
            return True
        else:
            return False

    def resolve(self) -> None:
        # Identify first name / last name / full name columns
        # They are marked as unknown until now
        num_columns = len(self.columns)
        for i in range(num_columns):
            if self.columns[i] == StudentColumn.UNKNOWN:
                if i == num_columns - 1 or self.columns[i + 1] != StudentColumn.UNKNOWN:
                    self.columns[i] = StudentColumn.FULL_NAME
                else:
                    self.columns[i] = StudentColumn.FIRST_NAME
                    self.columns[i + 1] = StudentColumn.LAST_NAME
                break
        for i, col in reversed(list(enumerate(self.columns))):
            if col != StudentColumn.UNKNOWN:
                break
        self.columns = self.columns[: i + 1]

    def is_valid(self) -> bool:
        return StudentColumn.ID in self.columns

    def student(self, row: Union[tuple[str], list[str]]) -> Student:
        num_columns = len(self.columns)
        if len(row) < num_columns:
            raise utils.EyegradeException(
                "Row with not enough columns", key="error_student_list"
            )
        student = Student("", "", "", "", "")
        for i, item in enumerate(row[:num_columns]):
            if self.columns[i] != StudentColumn.UNKNOWN:
                value = str(item)
                self._check_value(self.columns[i], value)
                attr_name = ATTR_NAME[self.columns[i]]
                setattr(student, attr_name, value)
        return student

    def data(self, index: int, student: Student) -> str:
        column = self.columns[index]
        if column != StudentColumn.UNKNOWN:
            attr_name = ATTR_NAME[column]
            return getattr(student, attr_name)
        else:
            return ""

    def normalize(self) -> "StudentColumnMap":
        normal_order = [
            StudentColumn.ID,
            StudentColumn.FIRST_NAME,
            StudentColumn.LAST_NAME,
            StudentColumn.FULL_NAME,
            StudentColumn.EMAIL,
        ]
        reordered_columns = [
            column for column in normal_order if column in self.columns
        ]
        return StudentColumnMap(columns=reordered_columns)

    def to_full_name(self) -> "StudentColumnMap":
        # It will raise ValueError if first or last name aren't present
        index_first = self.columns.index(StudentColumn.FIRST_NAME)
        index_last = self.columns.index(StudentColumn.LAST_NAME)
        new_columns = list(self.columns)
        if index_first < index_last:
            new_columns[index_first] = StudentColumn.FULL_NAME
            del new_columns[index_last]
        else:
            new_columns[index_last] = StudentColumn.FULL_NAME
            del new_columns[index_first]
        return StudentColumnMap(columns=new_columns)

    def __str__(self) -> str:
        return (
            "StudentColumnMap <"
            + ", ".join(ATTR_NAME[column] for column in self.columns)
            + ">"
        )

    def __len__(self) -> int:
        return len(self.columns)

    def __getitem__(self, index: int) -> StudentColumn:
        return self.columns[index]

    def __contains__(self, column: StudentColumn) -> bool:
        return column in self.columns

    @staticmethod
    def guess_map(row: Union[tuple[str], list[str]]) -> "StudentColumnMap":
        column_map = StudentColumnMap(num_columns=len(row))
        for i, item in enumerate(row):
            value = str(item)
            if _re_student_id.match(value):
                column = StudentColumn.ID
            elif _re_email.match(value):
                column = StudentColumn.EMAIL
            else:
                column = StudentColumn.UNKNOWN
            column_map.set_column(i, column)
        column_map.resolve()
        return column_map

    def _check_value(self, column: StudentColumn, value: str) -> None:
        if column == StudentColumn.ID:
            if not _re_student_id.match(value):
                raise utils.EyegradeException(
                    "Wrong id in student list: " + value, key="error_student_list"
                )
        elif column == StudentColumn.EMAIL:
            if not _re_email.match(value):
                raise utils.EyegradeException(
                    "Wrong email in student list: " + value, key="error_student_list"
                )


utils.EyegradeException.register_error(
    "error_student_list", "The syntax of the student list isn't correct."
)
