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
import sqlite3
import os

from . import utils
from . import scoring
from . import exams
from . import students
from . import capture
from . import images
from . import export


class SessionDB:
    """Access to a session SQLite database.

    This class encapsulates access functions to the session database.

    """

    DB_SCHEMA_VERSION = 5
    COMPATIBLE_SCHEMAS = (1, 2, 3, 4, 5)

    GRADING_MODE_ONE_CORRECT = 1
    GRADING_MODE_MULTI_CORRECT = 2

    _table_session = """
        CREATE TABLE Session (
            db_schema_version INTEGER,
            eyegrade_version STRING,
            title TEXT,
            description TEXT,
            dimensions TEXT NOT NULL,
            grading_mode INTEGER NOT NULL,
            scores_mode INTEGER NOT NULL,
            base_score_correct TEXT,
            base_score_incorrect TEXT,
            base_score_blank TEXT,
            id_num_digits INTEGER NOT NULL,
            survey_mode INTEGER NOT NULL,
            left_to_right_numbering INTEGER NOT NULL,
            capture_pattern TEXT NOT NULL
        )"""

    _table_questions = """
        CREATE TABLE Questions (
            model INTEGER NOT NULL,
            question INTEGER NOT NULL,
            permutation TEXT,
            variation INTEGER,
            score_correct TEXT,
            score_incorrect TEXT,
            score_blank TEXT,
            score_weight TEXT
        )"""

    _table_solutions = """
        CREATE TABLE Solutions (
            model INTEGER NOT NULL,
            question INTEGER NOT NULL,
            solution INTEGER
        )"""

    _table_exams = """
        CREATE TABLE Exams (
            exam_id INTEGER PRIMARY KEY NOT NULL,
            student INTEGER,
            model INTEGER,
            correct INTEGER,
            incorrect INTEGER,
            blank INTEGER,
            score REAL,
            FOREIGN KEY(student) REFERENCES Students(db_id)
        )"""

    _table_students = """
        CREATE TABLE Students (
            db_id INTEGER PRIMARY KEY NOT NULL,
            student_id TEXT,
            full_name TEXT,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            group_id INTEGER NOT NULL,
            sequence_num INTEGER NOT NULL,
            FOREIGN KEY(group_id) REFERENCES StudentGroups(group_id)
        )"""

    _table_student_groups = """
        CREATE TABLE StudentGroups (
            group_id INTEGER PRIMARY KEY NOT NULL,
            group_name TEXT NOT NULL
        )"""

    _table_answers = """
        CREATE TABLE Answers (
            exam_id INTEGER NOT NULL,
            question INTEGER NOT NULL,
            answer INTEGER NOT NULL,
            FOREIGN KEY(exam_id) REFERENCES Exams(exam_id)
        )"""

    _table_answer_cells = """
        CREATE TABLE AnswerCells (
            exam_id INTEGER NOT NULL,
            question INTEGER NOT NULL,
            choice INTEGER NOT NULL,
            center_x INTEGER NOT NULL,
            center_y INTEGER NOT NULL,
            diagonal INTEGER NOT NULL,
            lux INTEGER,
            luy INTEGER,
            rux INTEGER,
            ruy INTEGER,
            ldx INTEGER,
            ldy INTEGER,
            rdx INTEGER,
            rdy INTEGER,
            FOREIGN KEY(exam_id) REFERENCES Exams(exam_id)
        )"""

    _table_id_cells = """
        CREATE TABLE IdCells (
            exam_id INTEGER NOT NULL,
            digit INTEGER NOT NULL,
            lux INTEGER NOT NULL,
            luy INTEGER NOT NULL,
            rux INTEGER NOT NULL,
            ruy INTEGER NOT NULL,
            ldx INTEGER NOT NULL,
            ldy INTEGER NOT NULL,
            rdx INTEGER NOT NULL,
            rdy INTEGER NOT NULL,
            FOREIGN KEY(exam_id) REFERENCES Exams(exam_id)
        )"""

    _index_student_id = """
        CREATE UNIQUE INDEX idx_student_id ON Students(student_id)"""

    def __init__(self, session_file):
        """Opens a session database.

        For opening an existing session, just pass as `session_file` the
        session DB file name or the sesion's directory name.

        """
        if os.path.isdir(session_file):
            db_file = os.path.join(session_file, "session.eyedb")
            self.session_dir = session_file
        else:
            db_file = session_file
            self.session_dir = os.path.dirname(db_file)
        self._check_session_directory()
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row
        self._enable_foreign_key_constrains()
        self.schema_version = self._check_schema()
        self.exam_config = self._load_exam_config()
        self._compute_num_questions_and_choices()
        self.capture_save_func = lambda name: None
        self._student_listings = None

    @property
    def student_listings(self):
        if self._student_listings is None:
            groups = self.get_student_groups(ignore_empty_groups=False)
            self._student_listings = StudentListingsFromDB(self)
            for group in groups:
                self._student_listings.add_listing(self.get_group_listing(group))
        return self._student_listings

    def close(self):
        self.conn.close()

    def store_exam(self, exam_id, exam_capture, decisions, score, store_captures=True):
        student_db_id = self._student_db_id(decisions.student)
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO Exams VALUES " "(?, ?, ?, ?, ?, ?, ?)",
            (
                exam_id,
                student_db_id,
                _Adapter.enc_model(decisions.model),
                score.correct,
                score.incorrect,
                score.blank,
                score.score,
            ),
        )
        if decisions.answers is not None:
            self._store_answers(exam_id, decisions.answers, commit=False)
            self._store_answer_cells(exam_id, exam_capture.answer_cells, commit=False)
        if exam_capture.id_cells:
            self._store_id_cells(exam_id, exam_capture.id_cells, commit=False)
        self.conn.commit()
        if store_captures:
            self.save_raw_capture(exam_id, exam_capture)
            self.save_drawn_capture(exam_id, exam_capture, decisions.student)

    def remove_exam(self, exam_id):
        cursor = self.conn.cursor()
        student = self._read_student_by_exam(exam_id)
        cursor.execute("DELETE FROM Answers WHERE exam_id=?", (exam_id,))
        cursor.execute("DELETE FROM AnswerCells WHERE exam_id=?", (exam_id,))
        cursor.execute("DELETE FROM IdCells WHERE exam_id=?", (exam_id,))
        cursor.execute("DELETE FROM Exams WHERE exam_id=?", (exam_id,))
        self.conn.commit()
        self.remove_drawn_capture(exam_id, student)
        self.remove_raw_capture(exam_id)

    def update_answer(
        self, exam_id, question, exam_capture, decisions, score, store_captures=True
    ):
        new_answer = decisions.answers[question]
        self._update_answer(exam_id, question, new_answer, commit=False)
        self._update_score(exam_id, score, commit=False)
        self.conn.commit()
        if store_captures:
            self.save_drawn_capture(exam_id, exam_capture, decisions.student)

    def update_student(self, exam_id, exam_capture, decisions, store_captures=True):
        new_student_db_id = self._student_db_id(decisions.student)
        old_student = self._read_student_by_exam(exam_id)
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE Exams SET student = ? WHERE exam_id = ?",
            (new_student_db_id, exam_id),
        )
        self.conn.commit()
        self.remove_drawn_capture(exam_id, old_student)
        if store_captures:
            self.save_drawn_capture(exam_id, exam_capture, decisions.student)

    def _store_new_student(self, student):
        if student.group_id is None:
            student.group_id = 0
        listing = self.student_listings.listing_by_group_id(student.group_id)
        listing.add_students((student,))

    def store_students(self, student_list, commit=True):
        cursor = self.conn.cursor()
        data = []
        # Insert one by one with execute() instead of using executemany()
        # to get the autogenerated ids
        for student in student_list:
            if student.group_id is None:
                raise ValueError("Students must belong to a group")
            data = [
                student.student_id,
                student.full_name,
                student.first_name,
                student.last_name,
                student.email,
                student.group_id,
                student.sequence_num,
            ]
            if self.schema_version >= 2:
                cursor.execute(
                    "INSERT INTO Students "
                    "(student_id, full_name, first_name, "
                    " last_name, email, group_id, sequence_num) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    data,
                )
            else:
                del data[2:4]
                cursor.execute(
                    "INSERT INTO Students "
                    "(student_id, name, email, group_id, sequence_num) "
                    "VALUES (?, ?, ?, ?, ?)",
                    data,
                )
            student.db_id = cursor.lastrowid
            student.is_in_database = True
        if commit:
            self.conn.commit()

    def get_students(self, group_id=None):
        cursor = self.conn.cursor()
        if group_id is None:
            cursor.execute("SELECT * FROM Students ORDER BY sequence_num")
        else:
            cursor.execute(
                "SELECT * FROM Students WHERE group_id=? " "ORDER BY sequence_num",
                (group_id,),
            )
        return [self._student_from_row(row) for row in cursor]

    def get_student_groups(self, ignore_empty_groups=True):
        """Return the list of student groups.

        If `ignore_empty_groups` is set, only the groups with at least one
        student are returned.

        The groups are returned as a list of students.StudentGroup objects.

        """
        groups = []
        cursor = self.conn.cursor()
        if ignore_empty_groups:
            query = (
                "SELECT StudentGroups.group_id, group_name "
                "FROM StudentGroups "
                "INNER JOIN Students "
                "ON Students.group_id=StudentGroups.group_id "
                "GROUP BY Students.group_id"
            )
        else:
            query = "SELECT group_id, group_name " "FROM StudentGroups"
        for row in cursor.execute(query):
            # Use index instead of name because of incompatibilities
            # in the keys between older and newer versions of python/sql:
            groups.append(students.StudentGroup(row[0], row[1]))
        return groups

    def get_group_listing(self, group):
        """Return a `student.GroupListing` object."""
        return GroupListingFromDB(
            self, group, self.get_students(group_id=group.identifier)
        )

    def num_exams_from_group(self, group):
        """Get the number of exams of students in the given group."""
        cursor = self.conn.cursor()
        cursor.execute(
            (
                "SELECT COUNT(*) "
                "FROM Exams "
                "INNER JOIN Students ON student=db_id "
                "INNER JOIN StudentGroups "
                "    ON Students.group_id=StudentGroups.group_id "
                "WHERE Students.group_id=?"
            ),
            (group.identifier,),
        )
        return cursor.fetchone()[0]

    def remove_group(self, group):
        """Removes a group and all its students."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM Students WHERE group_id=?", (group.identifier,))
        cursor.execute(
            "DELETE FROM StudentGroups WHERE group_id=?", (group.identifier,)
        )
        self.conn.commit()

    def create_student_group(self, group_name):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO StudentGroups (group_name) VALUES (?)", (group_name,)
        )
        group_id = cursor.lastrowid
        self.conn.commit()
        return students.StudentGroup(group_id, group_name)

    def rename_student_group(self, group):
        """The new name is taken from the group input parameter."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE StudentGroups SET group_name=? WHERE group_id=?",
            (group.name, group.identifier),
        )
        self.conn.commit()

    def next_exam_id(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(exam_id) FROM Exams")
        result = cursor.fetchone()[0]
        if result is not None:
            return int(result) + 1
        else:
            return 1

    def save_legacy_answers(self):
        file_name = os.path.join(self.session_dir, "eyegrade-answers.csv")
        file_format = export.FileFormat.CSV_TABS
        with export.create_writer(file_name, file_format) as writer:
            for exam in self.exams_iterator():
                data = [
                    exam["exam_id"],
                    exam["student_id"] if exam["student_id"] else -1,
                    exam["model"],
                    exam["correct"],
                    exam["incorrect"],
                    exam["score"] if exam["score"] is not None else "?",
                    "/".join([str(answer) for answer in exam["answers"]]),
                ]
                writer.append_row(data)

    def export_grades(self, export_helper):
        if export_helper.add_column_headers:
            column_headers = export_helper.column_headers()
        with export_helper.create_writer() as writer:
            for i, (group, title) in enumerate(export_helper.iter_groups()):
                if i > 0:
                    writer.append_sheet()
                writer.set_sheet_title(title)
                if export_helper.add_column_headers:
                    writer.append_row(column_headers)
                if export_helper.export_by_exam:
                    iterator = self.exams_iterator()
                else:
                    iterator = self.grades_iterator(
                        all_students=export_helper.all_students,
                        sort_key=export_helper.sort_by,
                        student_group=group,
                    )
                for exam in iterator:
                    writer.append_row(export_helper.data(exam))

    def exams_iterator(self):
        cursor = self.conn.cursor()
        for row in cursor.execute(
            "SELECT "
            "exam_id, student_id, model, "
            "correct, incorrect, score "
            "FROM Exams "
            "LEFT JOIN Students ON student = db_id "
            "ORDER BY exam_id"
        ):
            exam = dict(row)
            exam["model"] = _Adapter.dec_model(exam["model"])
            exam["answers"] = self.read_answers(exam["exam_id"])
            yield exam

    def _grades_iterator_query(self, all_students, sort_key, student_group):
        if all_students:
            join_type = "LEFT"
        else:
            join_type = "INNER"
        if sort_key == export.SortBy.STUDENT_LIST:
            sort_clause = "ORDER BY group_id, sequence_num"
        elif sort_key == export.SortBy.LAST_NAME:
            if self.schema_version >= 2:
                sort_clause = "ORDER BY last_name, group_id, sequence_num"
            else:
                sort_clause = "ORDER BY name, group_id, sequence_num"
        elif sort_key == export.SortBy.GRADING_SEQUENCE:
            sort_clause = "ORDER BY exam_id"
        if student_group is not None:
            where_clause = "WHERE group_id = {0.identifier} ".format(student_group)
        else:
            where_clause = ""
        return (
            "SELECT "
            "* "
            "FROM Students "
            "{0} JOIN Exams ON student = db_id "
            "{1}"
            "{2}"
        ).format(join_type, where_clause, sort_clause)

    def grades_iterator(
        self,
        all_students=True,
        sort_key=export.SortBy.STUDENT_LIST,
        student_group=None,
        by_exams=False,
    ):
        if by_exams:
            query = (
                "SELECT "
                "* "
                "FROM Exams "
                "LEFT JOIN Students ON student = db_id "
                "ORDER BY exam_id"
            )
        else:
            query = self._grades_iterator_query(all_students, sort_key, student_group)
        cursor = self.conn.cursor()
        for row in cursor.execute(query):
            student = self._student_from_row(row)
            exam = {"student": student}
            for key in ("exam_id", "model", "correct", "incorrect", "score"):
                exam[key] = row[key]
            exam["model"] = _Adapter.dec_model(exam["model"])
            exam["answers"] = self.read_answers(exam["exam_id"])
            for key, value in exam.items():
                if value is None:
                    exam[key] = ""
            yield exam

    def read_answers(self, exam_id):
        answers = [0] * self.exam_config.num_questions
        cursor = self.conn.cursor()
        for row in cursor.execute(
            "SELECT question, answer FROM Answers " "WHERE exam_id = ?", (exam_id,)
        ):
            answers[row["question"]] = row["answer"]
        return answers

    def read_exams(self):
        cursor = self.conn.cursor()
        exam_list = []
        students_rank = self.student_listings.sorted_students()
        for row in cursor.execute(
            "SELECT "
            "exam_id, student_id, model, "
            "correct, incorrect, blank, score "
            "FROM Exams "
            "LEFT JOIN Students ON student = db_id"
        ):
            exam = ExamFromDB(row, students_rank, self)
            exam_list.append(exam)
        return exam_list

    def read_capture(self, exam_id):
        image = self.load_raw_capture(exam_id)
        answer_cells = self._read_answer_cells(exam_id)
        id_cells = self._read_id_cells(exam_id)
        return capture.ExamCapture(image, answer_cells, id_cells)

    def _read_answer_cells(self, exam_id):
        all_cells = []
        question_cells = []
        last_question_num = None
        cursor = self.conn.cursor()
        for row in cursor.execute(
            "SELECT * FROM AnswerCells WHERE exam_id=? " "ORDER BY question, choice",
            (exam_id,),
        ):
            cell = _create_cell_from_row(row, is_id_cell=False)
            if last_question_num is None:
                last_question_num = row["question"]
            elif last_question_num != row["question"]:
                all_cells.append(question_cells)
                last_question_num = row["question"]
                question_cells = []
            question_cells.append(cell)
        all_cells.append(question_cells)
        return all_cells

    def _read_id_cells(self, exam_id):
        cells = []
        cursor = self.conn.cursor()
        for row in cursor.execute(
            "SELECT * FROM IdCells WHERE exam_id=? " "ORDER BY digit", (exam_id,)
        ):
            cells.append(_create_cell_from_row(row, is_id_cell=True))
        return cells

    def save_drawn_capture(self, exam_id, exam_capture, student):
        name = utils.capture_name(self.exam_config.capture_pattern, exam_id, student)
        drawn_name = os.path.join(self.session_dir, "captures", name)
        if self.capture_save_func:
            self.capture_save_func(drawn_name)
        else:
            exam_capture.save_image_drawn(drawn_name)

    def save_raw_capture(self, exam_id, exam_capture):
        raw_name = os.path.join(
            self.session_dir, "internal", "raw-{0}.png".format(exam_id)
        )
        exam_capture.save_image_raw(raw_name)

    def load_raw_capture(self, exam_id):
        return images.load_image(self.get_raw_capture_path(exam_id))

    def get_raw_capture_path(self, exam_id):
        path = os.path.join(self.session_dir, "internal", "raw-{0}.png".format(exam_id))
        if not os.path.isfile(path):
            path = utils.resource_path("not_found.png")
        return path

    def remove_drawn_capture(self, exam_id, student):
        name = utils.capture_name(self.exam_config.capture_pattern, exam_id, student)
        drawn_name = os.path.join(self.session_dir, "captures", name)
        if os.path.exists(drawn_name):
            os.remove(drawn_name)

    def remove_raw_capture(self, exam_id):
        raw_name = os.path.join(
            self.session_dir, "internal", "raw-{0}.png".format(exam_id)
        )
        if os.path.exists(raw_name):
            os.remove(raw_name)

    def _check_schema(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT db_schema_version, eyegrade_version " "FROM Session")
        row = cursor.fetchone()
        schema = row["db_schema_version"]
        version = row["eyegrade_version"]
        if schema not in SessionDB.COMPATIBLE_SCHEMAS:
            raise utils.EyegradeException(
                "",
                key="incompatible_schema",
                format_params=(utils.program_name, utils.version, version),
            )
        return schema

    def _check_session_directory(self):
        db_file = os.path.join(self.session_dir, "session.eyedb")
        if not os.path.exists(db_file):
            raise utils.EyegradeException("", key="no_session_db")
        if not check_file_is_sqlite(db_file):
            raise utils.EyegradeException("", key="session_invalid")
        if not os.path.exists(
            os.path.join(self.session_dir, "captures")
        ) or not os.path.exists(os.path.join(self.session_dir, "internal")):
            raise utils.EyegradeException("", key="corrupt_session_dir")

    def _student_db_id(self, student):
        if student is not None:
            if not student.is_in_database:
                self._store_new_student(student)
            student_db_id = student.db_id
        else:
            student_db_id = None
        return student_db_id

    def _read_student_by_exam(self, exam_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM Students "
            "INNER JOIN Exams ON Students.db_id = Exams.student "
            "WHERE exam_id = ?",
            (exam_id,),
        )
        row = cursor.fetchone()
        if row is not None:
            return self._student_from_row(row)
        else:
            return None

    def _read_cell_geometries(self, exam_id, load_corners=False):
        if not load_corners:
            query = (
                "SELECT question, choice, center_x, center_y, diagonal "
                "FROM CellGeometries WHERE exam_id = ?"
            )
        else:
            query = "SELECT * FROM CellGeometries WHERE exam_id = ?"
        cursor = self.conn.cursor()
        return [row for row in cursor.execute(query, exam_id)]

    def _compute_num_questions_and_choices(self):
        self.num_choices = []
        self.num_questions = 0
        dimensions = self.exam_config.dimensions
        for table in dimensions:
            self.num_choices.extend([table[0]] * table[1])
            self.num_questions += table[1]

    def _load_exam_config(self):
        self.exam_config = exams.ExamConfig()
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM Session")
        row = cursor.fetchone()
        if row is None:
            raise utils.EyegradeException("", key="session_invalid")
        self.exam_config.set_dimensions(row["dimensions"])
        self.exam_config.id_num_digits = row["id_num_digits"]
        self.exam_config.survey_mode = True if row["survey_mode"] else False
        self.exam_config.left_to_right_numbering = (
            True if row["left_to_right_numbering"] else False
        )
        self.exam_config.capture_pattern = row["capture_pattern"]
        if self.schema_version >= 3:
            scores_mode = row["scores_mode"]
            self.exam_config.scores_mode = scores_mode
            if scores_mode == exams.ExamConfig.SCORES_MODE_WEIGHTS:
                if row["base_score_correct"] is not None:
                    base_scores = scoring.QuestionScores(
                        row["base_score_correct"],
                        row["base_score_incorrect"],
                        row["base_score_blank"],
                    )
                    self.exam_config.set_base_scores(base_scores)
                else:
                    raise utils.EyegradeException("", key="session_invalid")
            else:
                if row["base_score_correct"] is not None:
                    raise utils.EyegradeException("", key="session_invalid")
        else:
            # Schema version < 3
            if row["correct_weight"] is not None:
                base_scores = scoring.QuestionScores(
                    row["correct_weight"], row["incorrect_weight"], row["blank_weight"]
                )
            else:
                base_scores = None
        if self.schema_version >= 3:
            self._load_solutions_permutations_scores()
        else:
            # Schema version < 3
            for row in cursor.execute("SELECT * FROM Solutions"):
                self.exam_config.set_solutions(
                    _Adapter.dec_model(row["model"]), row["solutions"]
                )
            for row in cursor.execute("SELECT * FROM Permutations"):
                self.exam_config.set_permutations(
                    _Adapter.dec_model(row["model"]), row["permutations"]
                )
            if base_scores is not None:
                # This must be done after having set the solutions
                self.exam_config.set_base_scores(base_scores, same_weights=True)
        return self.exam_config

    def _load_solutions_permutations_scores(self):
        cursor = self.conn.cursor()
        scores_mode = self.exam_config.scores_mode
        solutions = {}
        permutations = {}
        variations = {}
        scores = {}
        if scores_mode == exams.ExamConfig.SCORES_MODE_WEIGHTS:
            weights = {}
        elif scores_mode == exams.ExamConfig.SCORES_MODE_INDIVIDUAL:
            scores = {}
        models = []
        model = None
        for row in cursor.execute("SELECT * FROM Questions ORDER BY model, question"):
            if row["model"] != model:
                model = row["model"]
                models.append(model)
                model_permutations = []
                permutations[model] = model_permutations
                if self.schema_version >= 5:
                    model_variations = []
                    variations[model] = model_variations
                if scores_mode == exams.ExamConfig.SCORES_MODE_WEIGHTS:
                    model_weights = []
                    weights[model] = model_weights
                elif scores_mode == exams.ExamConfig.SCORES_MODE_INDIVIDUAL:
                    model_scores = []
                    scores[model] = model_scores
            model_permutations.append(row["permutation"])
            if self.schema_version >= 5:
                model_variations.append(row["variation"])
            if scores_mode == exams.ExamConfig.SCORES_MODE_WEIGHTS:
                model_weights.append(row["score_weight"])
            elif scores_mode == exams.ExamConfig.SCORES_MODE_INDIVIDUAL:
                question_scores = scoring.QuestionScores(
                    row["score_correct"], row["score_incorrect"], row["score_blank"]
                )
                model_scores.append(question_scores)
        for m in models:
            model = _Adapter.dec_model(m)
            solutions = self._load_solutions(m)
            if solutions[0] is not None:
                self.exam_config.set_solutions(model, solutions)
            if permutations[m][0] is not None:
                self.exam_config.set_permutations(model, permutations[m])
            if m in variations:
                self.exam_config.set_variations(model, variations[m])
            if scores_mode == exams.ExamConfig.SCORES_MODE_WEIGHTS:
                self.exam_config.set_question_weights(model, weights[m])
            elif scores_mode == exams.ExamConfig.SCORES_MODE_INDIVIDUAL:
                self.exam_config.set_question_scores(model, scores[m])

    def _load_solutions(self, model):
        solutions = [set() for _ in range(self.exam_config.num_questions)]
        cursor = self.conn.cursor()
        if self.schema_version >= 5:
            query = (
                "SELECT question, solution "
                "FROM Solutions "
                "WHERE model=? ORDER BY question"
            )
        else:
            query = (
                "SELECT question, solution "
                "FROM Questions "
                "WHERE model=? ORDER BY question"
            )
        for row in cursor.execute(query, (model,)):
            solutions[row["question"]].add(row["solution"])
        # Swap empty solutions by None:
        solutions = [s if s else None for s in solutions]
        return solutions

    def _update_answer(self, exam_id, question, new_answer, commit=True):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE Answers SET answer = ?" "WHERE exam_id = ? AND question = ?",
            (new_answer, exam_id, question),
        )
        if commit:
            self.conn.commit()

    def _update_score(self, exam_id, score, commit=True):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE Exams SET correct = ?, incorrect = ?,"
            "                 blank = ?, score = ?"
            "WHERE exam_id = ?",
            (score.correct, score.incorrect, score.blank, score.score, exam_id),
        )
        if commit:
            self.conn.commit()

    def _group_max_seq(self, group_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT MAX(sequence_num) FROM Students " "WHERE group_id = ?", (group_id,)
        )
        result = cursor.fetchone()[0]
        if result is not None:
            return int(result)
        else:
            return 0

    def _store_answers(self, exam_id, answers, commit=True):
        data = []
        for i, answer in enumerate(answers):
            data.append((exam_id, i, answer))
        if data:
            cursor = self.conn.cursor()
            cursor.executemany("INSERT INTO Answers VALUES (?, ?, ?)", data)
            if commit:
                self.conn.commit()

    def _store_answer_cells(self, exam_id, answer_cells, commit=True):
        data = []
        for i, question_cells in enumerate(answer_cells):
            for j, cell in enumerate(question_cells):
                item = (
                    exam_id,
                    i,
                    j,
                    cell.center[0],
                    cell.center[1],
                    cell.diagonal,
                    cell.plu[0],
                    cell.plu[1],
                    cell.pru[0],
                    cell.pru[1],
                    cell.pld[0],
                    cell.pld[1],
                    cell.prd[0],
                    cell.prd[1],
                )
                data.append(item)
        if data:
            cursor = self.conn.cursor()
            cursor.executemany(
                "INSERT INTO AnswerCells VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                data,
            )
            if commit:
                self.conn.commit()

    def _store_id_cells(self, exam_id, id_cells, commit=True):
        if id_cells:
            data = []
            for i, cell in enumerate(id_cells):
                item = (
                    exam_id,
                    i,
                    cell.plu[0],
                    cell.plu[1],
                    cell.pru[0],
                    cell.pru[1],
                    cell.pld[0],
                    cell.pld[1],
                    cell.prd[0],
                    cell.prd[1],
                )
                data.append(item)
            cursor = self.conn.cursor()
            cursor.executemany(
                "INSERT INTO IdCells VALUES " "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", data
            )
            if commit:
                self.conn.commit()

    def _enable_foreign_key_constrains(self):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")

    def _student_from_row(self, row):
        if self.schema_version >= 2:
            student = students.Student(
                row["student_id"],
                row["full_name"],
                row["first_name"],
                row["last_name"],
                row["email"],
                db_id=row["db_id"],
                group_id=row["group_id"],
                sequence_num=row["sequence_num"],
                is_in_database=True,
            )
        else:
            student = students.Student(
                row["student_id"],
                row["name"],
                None,
                None,
                row["email"],
                db_id=row["db_id"],
                group_id=row["group_id"],
                sequence_num=row["sequence_num"],
                is_in_database=True,
            )
        return student


class ExamFromDB(exams.Exam):
    def __init__(self, db_dict, students_rank, sessiondb):
        """Creates a new ExamFromDB object.

        For efficiency reasons, the 'capture' is not loaded. Use
        'load_capture()' to load it if needed.

        """
        self.sessiondb = sessiondb
        self.capture = None
        self.student_listings = sessiondb.student_listings
        self.exam_id = db_dict["exam_id"]
        self.model = db_dict["model"]
        if db_dict["student_id"]:
            student = sessiondb.student_listings.student(db_dict["student_id"])
        else:
            student = None
        answers = sessiondb.read_answers(self.exam_id)
        self.decisions = ExamDecisionsFromDB(
            answers, student, students_rank, _Adapter.dec_model(db_dict["model"])
        )
        solutions = sessiondb.exam_config.get_solutions(self.decisions.model)
        if (
            self.decisions.model
            and self.decisions.model in sessiondb.exam_config.scores
        ):
            question_scores = sessiondb.exam_config.scores[self.decisions.model]
        else:
            question_scores = None
        self.score = scoring.Score(answers, solutions, question_scores)


class ExamDecisionsFromDB(capture.ExamDecisions):
    def __init__(self, answers, student, students_rank, model):
        self.answers = answers
        self.student = student
        self.model = model
        self.detected_id = None
        self.id_scores = None
        self.students_rank = students_rank


class GroupListingFromDB(students.GroupListing):
    def __init__(self, sessiondb, group, student_list):
        super().__init__(group, student_list)
        self.sessiondb = sessiondb

    def add_students(self, student_list):
        super().add_students(student_list)
        self.sessiondb.store_students(student_list)

    def rename(self, new_name):
        super().rename(new_name)
        self.sessiondb.rename_student_group(self.group)


class StudentListingsFromDB(students.StudentListings):
    def __init__(self, sessiondb):
        super().__init__()
        self.sessiondb = sessiondb

    def create_listing(self, group):
        created_group = self.sessiondb.create_student_group(group.name)
        group.identifier = created_group.identifier
        listing = GroupListingFromDB(self.sessiondb, group, [])
        self.add_listing(listing)
        return listing

    def remove_at(self, index):
        group = self.listings[index].group
        num_exams = self.sessiondb.num_exams_from_group(group)
        if num_exams == 0:
            super().remove_at(index)
            self.sessiondb.remove_group(group)
        else:
            raise students.CantRemoveGroupException(
                "Some exams ({}) belong to the group".format(num_exams)
            )


class _Adapter:
    @staticmethod
    def enc_model(model_letter):
        if model_letter == "0":
            return 0
        elif model_letter is None or model_letter == "?":
            return -1
        else:
            return ord(model_letter) - 64

    @staticmethod
    def dec_model(model_number):
        if model_number == 0:
            return "0"
        elif model_number == -1 or model_number is None:
            return None
        else:
            return chr(64 + model_number)


def check_file_is_sqlite(filename):
    try:
        with open(filename, "rb") as f:
            data = f.read(16)
        if data == b"SQLite format 3\x00":
            is_sqlite = True
        else:
            is_sqlite = False
    except IOError:
        is_sqlite = False
    return is_sqlite


def create_session_directory(dir_name, exam_data, student_listings):
    """Create the session database and directory layout.

    `dir_name` must be an empty directory that already exists. If
    it does not exist, it is created here.

    """
    if not os.path.isdir(dir_name):
        os.mkdir(dir_name)
    os.mkdir(os.path.join(dir_name, "captures"))
    os.mkdir(os.path.join(dir_name, "internal"))
    db_file = os.path.join(dir_name, "session.eyedb")
    _create_session_db(db_file, exam_data, student_listings)


def _create_session_db(db_file, exam_data, student_listings):
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    _create_tables(conn)
    _save_exam_config(conn, exam_data)
    _save_student_listings(conn, student_listings)
    conn.commit()


def _create_tables(conn):
    cursor = conn.cursor()
    cursor.execute(SessionDB._table_session)
    cursor.execute(SessionDB._table_questions)
    cursor.execute(SessionDB._table_solutions)
    cursor.execute(SessionDB._table_exams)
    cursor.execute(SessionDB._table_students)
    cursor.execute(SessionDB._table_student_groups)
    cursor.execute(SessionDB._table_answers)
    cursor.execute(SessionDB._table_answer_cells)
    cursor.execute(SessionDB._table_id_cells)
    cursor.execute(SessionDB._index_student_id)


def _save_exam_config(conn, exam_data):
    if exam_data.base_scores is None:
        base_scores = (None, None, None)
    else:
        base_scores = (
            exam_data.base_scores.format_correct_score(),
            exam_data.base_scores.format_incorrect_score(),
            exam_data.base_scores.format_blank_score(),
        )
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Session "
        "VALUES (?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            SessionDB.DB_SCHEMA_VERSION,
            utils.version,
            exam_data.format_dimensions(),
            SessionDB.GRADING_MODE_ONE_CORRECT,
            exam_data.scores_mode,
            base_scores[0],
            base_scores[1],
            base_scores[2],
            exam_data.id_num_digits,
            1 if exam_data.survey_mode else 0,
            1 if exam_data.left_to_right_numbering else 0,
            exam_data.capture_pattern,
        ),
    )
    # Store the question permutations and scores
    data = []
    for model in exam_data.models:
        all_model = exam_data.num_questions * [_Adapter.enc_model(model)]
        all_none = exam_data.num_questions * [None]
        permutations = exam_data.get_permutations(model)
        if permutations:
            permutations = [exam_data.format_permutation(p) for p in permutations]
        else:
            permutations = all_none
        variations = exam_data.get_variations(model)
        if exam_data.scores_mode == exams.ExamConfig.SCORES_MODE_INDIVIDUAL:
            weights = all_none
            scores_c = [s.format_correct_score() for s in exam_data.scores[model]]
            scores_i = [s.format_incorrect_score() for s in exam_data.scores[model]]
            scores_b = [s.format_blank_score() for s in exam_data.scores[model]]
        else:
            if exam_data.scores_mode == exams.ExamConfig.SCORES_MODE_WEIGHTS:
                weights = exam_data.get_question_weights(model, formatted=True)
            else:
                weights = all_none
            scores_c = all_none
            scores_i = all_none
            scores_b = all_none
        data.extend(
            zip(
                all_model,
                range(exam_data.num_questions),
                permutations,
                variations,
                scores_c,
                scores_i,
                scores_b,
                weights,
            )
        )
    cursor.executemany("INSERT INTO Questions VALUES (?, ?, ?, ?, ?, ?, ?, ?)", data)
    # Store question solutions
    data = []
    for model in exam_data.models:
        encoded_model = _Adapter.enc_model(model)
        solutions = exam_data.get_solutions(model)
        if solutions:
            for question, question_solutions in enumerate(solutions):
                for solution in question_solutions:
                    data.append((encoded_model, question, solution))
    cursor.executemany("INSERT INTO Solutions VALUES (?, ?, ?)", data)


def _save_student_listings(conn, student_listings):
    for group_listing in student_listings:
        _save_group_listing(conn, group_listing)


def _save_group_listing(conn, group_listing):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO StudentGroups (group_id, group_name) VALUES (?, ?)",
        (group_listing.group.identifier, group_listing.group.name),
    )
    if len(group_listing) > 0:
        internal_list = []
        for student in group_listing.students:
            internal_list.append(
                (
                    student.student_id,
                    student.full_name,
                    student.first_name,
                    student.last_name,
                    student.email,
                    student.group_id,
                    student.sequence_num,
                )
            )
        cursor.executemany(
            "INSERT INTO Students "
            "(student_id, full_name, "
            " first_name, last_name, email, group_id, "
            " sequence_num) VALUES "
            "(?, ?, ?, ?, ?, ?, ?)",
            internal_list,
        )


def _create_cell_from_row(row, is_id_cell=False):
    plu = (row["lux"], row["luy"])
    pru = (row["rux"], row["ruy"])
    pld = (row["ldx"], row["ldy"])
    prd = (row["rdx"], row["rdy"])
    if not is_id_cell:
        center = (row["center_x"], row["center_y"])
        diagonal = row["diagonal"]
    else:
        center = None
        diagonal = None
    return capture.CellGeometry(plu, pru, pld, prd, center, diagonal)
