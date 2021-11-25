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

import re
import copy
import sys
import subprocess
import os

from .. import utils
from .. import exams


PARAM_MIN_NUM_QUESTIONS = 1

# For formatting questions
PARAM_TABLE_SEP = 0.05
PARAM_TABLE_MARGIN = 0.1

# Numbers of questions in which the number of tables is changed
PARAM_TABLE_LMITS = [8, 24, 55]
RE_SPLIT_TEMPLATE = re.compile("{{([^{}]+)}}")

# Register user-friendly error messages
utils.EyegradeException.register_error(
    "incoherent_exam_config",
    "The exam you are attempting to create is not compatible\n"
    "with the already existing .eye exam configuration file.\n"
    "This happens, for example, when the configuration file\n"
    "contains more or less questions than the exam you are now\n"
    "creating. If you really want to discard the previous .eye file,\n"
    "use the --force option, or just remove the file manually.",
)
utils.EyegradeException.register_error(
    "incoherent_num_tables",
    "The specified number of tables and the exam dimensions are not\n"
    "compatible. The exam dimensions implicitly specify the number of tables.\n"
    "Therefore, there is no need to explicitly specify the number of tables.",
    "Incoherent number of tables.",
)
utils.EyegradeException.register_error(
    "bad_model_value",
    "A model must be represented by an uppercase English letter (A-Z).\n"
    "You can also create an unshuffled version of the exam with the\n"
    "special '0' model.",
    "Bad model value.",
)
utils.EyegradeException.register_error(
    "too_few_questions",
    short_message="At least %d question(s) needed" % PARAM_MIN_NUM_QUESTIONS,
)
utils.EyegradeException.register_error(
    "too_few_choices", short_message="At least 2 choices per question needed"
)
utils.EyegradeException.register_error(
    "too_many_tables",
    "There cannot be less than two questions per table.",
    "There are too many tables for such a few questions",
)
utils.EyegradeException.register_error(
    "latex_not_found",
    "Install LaTeX and make sure it is in your system's PATH variable.",
    "The command pdflatex was not found.",
)


class ExamMaker:
    def __init__(
        self,
        num_questions,
        num_choices,
        template_filename,
        output_file,
        variables,
        exam_config_filename,
        num_tables=0,
        dimensions=None,
        table_width=None,
        table_height=None,
        table_scale=1.0,
        id_box_width=None,
        force_config_overwrite=False,
        scores=None,
        left_to_right_numbering=False,
        survey_mode=False,
    ):
        """
           Class able to create exams. One object is enough for all models.

        """
        self.num_questions = num_questions
        self.num_choices = num_choices
        template = utils.read_file(template_filename)
        self.parts = RE_SPLIT_TEMPLATE.split(template)
        self.left_to_right_numbering = left_to_right_numbering
        self.survey_mode = survey_mode
        self.output_file = output_file
        self.exam_questions = None
        template_id_label, template_id_num_digits = id_num_digits(self.parts)
        if "student_id_label" in variables:
            id_label = variables["student_id_label"]
        else:
            id_label = template_id_label
        if "student_id_length" in variables:
            self.id_num_digits = variables["student_id_length"]
        else:
            self.id_num_digits = template_id_num_digits
        # The ID box is part of the answer table replacement
        # when it does not appear as a separate key in the template.
        # The latter is legacy behaviour kept for backwards compatibility.
        if template_id_label is None and self.id_num_digits > 0:
            self.id_box_with_answer_table = True
            if id_label is None:
                id_label = "ID"
        else:
            self.id_box_with_answer_table = False
        self.exam_config_filename = exam_config_filename
        if num_tables > 0 and dimensions is not None and len(dimensions) != num_tables:
            raise utils.EyegradeException("", key="incoherent_num_tables")
        if dimensions is not None:
            self.dimensions = dimensions
        else:
            self.dimensions = compute_table_dimensions(
                num_questions, num_choices, num_tables
            )
        self.table_scale = table_scale
        self.id_box_width = id_box_width
        if table_width is None and table_height is None:
            (
                self.table_width,
                self.table_height,
                self.id_box_width,
            ) = self._compute_table_size()
        else:
            self.table_width = table_width
            self.table_height = table_height
        if self.exam_config_filename is not None:
            if not force_config_overwrite:
                self._load_exam_config()
            else:
                self._new_exam_config()
        else:
            self.exam_config = None
        if scores is not None:
            variables["score_correct"] = scores.format_correct_score()
            variables["score_incorrect"] = scores.format_incorrect_score()
            if self.exam_config is not None:
                self.exam_config.set_base_scores(scores)
        self._load_replacements(variables, id_label)
        self.empty_variables = []

    def set_exam_questions(self, exam):
        if exam.num_questions() != self.num_questions:
            raise Exception("Incorrect number of questions")
        self.exam_questions = exam

    def create_exam(
        self, model, shuffle, variation=None, with_solution=False, produce_pdf=False
    ):
        """Creates a new exam.

           'shuffle' must be a boolean. If True, the exam is shuffled
           again even if it was previously shuffled. If False, it is
           only shuffled if it was not previously shuffled.

        """
        if not self.survey_mode:
            if (
                model is None
                or len(model) != 1
                or ((ord(model) < 65 or ord(model) > 90) and model != "0")
            ):
                raise utils.EyegradeException("", "bad_model_value")
        else:
            if model is None:
                model = "A"
        replacements = copy.copy(self.replacements)
        answer_table = create_answer_table(
            self.dimensions,
            model,
            self.survey_mode,
            self.table_width,
            self.table_height,
            self.left_to_right_numbering,
        )
        if self.id_box_with_answer_table:
            answer_table = replacements["id-box"] + answer_table
        if self.exam_config is not None:
            if self.exam_config.dimensions == []:
                self.exam_config.dimensions = self.dimensions
            if model != "0" and model not in self.exam_config.models:
                self.exam_config.models.append(model)
        if self.exam_questions is not None:
            if model != "0" and not self.survey_mode:
                if (
                    self.exam_config is None
                    or model not in self.exam_config.permutations
                    or (model in self.exam_config.permutations and shuffle)
                ):
                    self.exam_questions.shuffle(model, variation=variation)
                    if self.exam_config is not None:
                        (
                            solutions,
                            permutations,
                        ) = self.exam_questions.solutions_and_permutations(model)
                        self.exam_config.solutions[model] = solutions
                        self.exam_config.permutations[model] = permutations
                        self.exam_config.variations[
                            model
                        ] = self.exam_questions.selected_variations(model)
                else:
                    permutations = self.exam_config.permutations[model]
                    self.exam_questions.set_permutation(model, permutations)
                    if model in self.exam_config.variations:
                        variations = self.exam_config.variations[model]
                        self.exam_questions.select_variations(model, variations)
            replacements["questions"] = format_questions(
                self.exam_questions, model, with_solution
            )
        replacements["answer-table"] = answer_table
        replacements["model"] = model
        replacements["declarations"] = latex_declarations(with_solution)
        replacements["variation"] = "0"
        if model != "0":
            selected_variation = self.exam_questions.selected_variation(model)
            if selected_variation is not None:
                replacements["variation"] = str(selected_variation + 1)

        # Replacement keys are in odd positions of self.parts
        replaced = len(self.parts) * [None]
        replaced[::2] = self.parts[::2]
        replaced[1::2] = [self._replace(key, replacements) for key in self.parts[1::2]]
        exam_text = "".join(replaced)
        if self.output_file == sys.stdout:
            utils.write_to_stdout(exam_text)
            produced_filename = None
        else:
            if not self.survey_mode:
                produced_filename = self.output_file % model
            else:
                produced_filename = self.output_file
            utils.write_file(produced_filename, exam_text)
            if produce_pdf:
                success, output, produced_filename = compile_latex(
                    produced_filename, remove_tex=True
                )
                if not success:
                    raise utils.EyegradeException(output)
        return produced_filename

    def save_exam_config(self):
        if self.exam_config is not None:
            self.exam_config.save(self.exam_config_filename)

    def _load_exam_config(self):
        if self.exam_config_filename is not None:
            try:
                self.exam_config = exams.ExamConfig(self.exam_config_filename)
                if self.num_questions != self.exam_config.num_questions:
                    raise utils.EyegradeException(
                        "Incoherent number of questions", key="incoherent_exam_config"
                    )
                if self.id_num_digits != self.exam_config.id_num_digits:
                    raise utils.EyegradeException(
                        "Incoherent configuration of id box",
                        key="incoherent_exam_config",
                    )
                if self.dimensions != self.exam_config.dimensions:
                    raise utils.EyegradeException(
                        "Incoherent table dimensions", key="incoherent_exam_config"
                    )
                if (
                    self.left_to_right_numbering
                    != self.exam_config.left_to_right_numbering
                ):
                    raise utils.EyegradeException(
                        "Incoherent question numbering", key="incoherent_exam_config"
                    )
                if self.survey_mode != self.exam_config.survey_mode:
                    raise utils.EyegradeException(
                        "Incoherent survey mode value", key="incoherent_exam_config"
                    )
            except IOError:
                self._new_exam_config()

    def _new_exam_config(self):
        self.exam_config = exams.ExamConfig()
        self.exam_config.num_questions = self.num_questions
        self.exam_config.id_num_digits = self.id_num_digits
        self.exam_config.left_to_right_numbering = self.left_to_right_numbering
        self.exam_config.survey_mode = self.survey_mode

    def _compute_table_size(self):
        """Computes a size for the table such as it is more or less square.

        Some facts the function is based on:

        - In Latex, the proportion between the witdh and the height of a
        cell will be 1.55.

        - Each table has an extra column for the question number.

        - There are one extra row at the top, and two at the bottom.

        - The objective is making the lengths of the horizontal lines be
        close to the length of the vertical lines.

        - When resizing the table, with double width proportions are 1:1.

        """
        num_cols = self.dimensions[0][0] * len(self.dimensions)
        num_rows = max([d[1] for d in self.dimensions])
        extra_cols = len(self.dimensions)
        extra_rows = 3
        actual_ratio = 1.55 * num_cols / num_rows
        desired_ratio = (1 + 1.0 * extra_cols / num_cols) / (
            1 + 1.0 * extra_rows / num_rows
        )
        if actual_ratio > 1.35 * desired_ratio:
            ratio = 1.35 * desired_ratio
        elif actual_ratio < 0.74 * desired_ratio:
            ratio = 0.74 * desired_ratio
        else:
            ratio = actual_ratio
        height = 0.3 * num_rows
        if height < 3:
            height = 3.0
        elif height > 4.6:
            height = 4.6
        height = height * self.table_scale
        width = 2 * height * ratio
        if self.id_num_digits > 0 and self.id_box_width is None:
            actual_id_width = 0.75 * self.id_num_digits
            if actual_id_width < 0.66 * width:
                id_width = 0.66 * width
            elif actual_id_width > 1.5 * width:
                id_width = 1.5 * width
            else:
                id_width = None
        else:
            id_width = None
        return width, height, id_width

    def _load_replacements(self, variables, id_label):
        self.replacements = copy.copy(variables)
        self.replacements["id-box"] = create_id_box(
            id_label, self.id_num_digits, self.id_box_width
        )
        self.replacements["questions"] = ""

    def _replace(self, key, replacements):
        if key in replacements:
            if not replacements[key] and key not in self.empty_variables:
                self.empty_variables.append(key)
                return ""
            else:
                return replacements[key]
        elif key.startswith("id-box"):
            return replacements["id-box"]
        else:
            raise Exception("Unknown replacement key: " + key)


def check_latex():
    with open(os.devnull, "w") as devnull:
        try:
            subprocess.check_call(
                ["pdflatex", "-version"], stdout=devnull, stderr=devnull
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            success = False
        else:
            success = True
    return success


def compile_latex(latex_file, remove_tex=False):
    directory, name = os.path.split(latex_file)
    base_name = os.path.splitext(name)[0]
    with utils.change_dir(directory):
        try:
            output = subprocess.check_output(
                ["pdflatex", "-interaction=nonstopmode", name], stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as exc:
            output = exc.output
            success = False
            produced_filename = None
        except OSError:
            success = False
            raise utils.EyegradeException("", key="latex_not_found")
        else:
            success = True
            produced_filename = os.path.join(directory, base_name + ".pdf")
        finally:
            to_remove = [base_name + ".aux"]
            if success:
                to_remove.append(base_name + ".log")
                if remove_tex:
                    to_remove.append(name)
            for filename in to_remove:
                if os.path.isfile(filename):
                    os.remove(filename)
    return success, output, produced_filename


def latex_declarations(with_solution):
    """Returns the list of declarations to be set in the preamble
       of the LaTeX output.

    """
    data = [
        r"\usepackage{graphicx}",
        r"\usepackage{fancyvrb}",
        r"\usepackage{enumerate}",
        r"\usepackage{color}",
        r"\definecolor{lightgray}{rgb}{1, 1, 1}",
        r"\newcommand{\light}[1]{\textcolor{lightgray}{#1}}",
        r"\definecolor{hidden}{rgb}{1, 1, 1}",
        r"\newcommand{\hidden}[1]{\textcolor{hidden}{#1}}",
        r"\newif\ifsolutions",
    ]
    if with_solution:
        data.append(r"\solutionstrue")
    else:
        data.append(r"\solutionsfalse")
    return "\n".join(data)


def create_answer_table(
    dimensions,
    model,
    survey_mode,
    table_width=None,
    table_height=None,
    left_to_right_numbering=False,
):
    """Returns a string with the answer tables of the answer sheet.

       Tables are LaTeX-formatted. 'dimensions' specifies the geometry
       of the tables. 'model' is a one letter string with the name of
       the model, or '0' for the un-shuffled exam. 'table_width' is
       the desired width of the answer table, in cm. None for the
       default width. 'table_height' is the desired height in cm. None
       for the default. If only one of height and width is defined,
       the other will keep the aspect ratio. 'left_to_right_numbering'
       set to True makes cell numbers to grow from left to right
       instead of from up to bottom. The default is False (up to
       bottom).

    """
    if not dimensions:
        raise Exception("No tables defined in dimensions")
    compact = True
    num_choices = dimensions[0][0]
    num_tables = len(dimensions)
    for dimension in dimensions:
        if dimension[0] != num_choices:
            raise utils.EyegradeException("", "same_num_choices")
    if model != "0":
        bits = utils.encode_model(model, num_tables, num_choices)
    else:
        bits = [False] * num_tables * num_choices
    bits_rows = _create_infobits(bits, num_tables, num_choices, survey_mode)
    tables, question_numbers = table_geometry(dimensions)
    rows = _table_top(num_tables, num_choices, compact, table_width, table_height)
    for i, row_geometry in enumerate(tables):
        rows.append(_horizontal_line(row_geometry, num_choices, compact))
        rows.append(
            _build_row(
                i,
                row_geometry,
                question_numbers,
                num_choices,
                bits_rows,
                compact,
                left_to_right_numbering,
            )
        )
    rows.append(r"\end{tabular}")
    if table_width is not None or table_height is not None:
        rows.append("}")
    rows.append(r"\end{center}")
    return "\n".join(rows)


def create_id_box(label, num_digits, box_width=None):
    """Creates the ID box given a label to show and number of digits.

    """
    parts = [r"\begin{center}", r"\Large"]
    if box_width is not None:
        parts.append(r"\resizebox{%fcm}{!}{" % box_width)
    parts.append(r"\begin{tabular}{l|" + num_digits * "p{3mm}|" + "}")
    parts.append(r"\cline{2-%d}" % (1 + num_digits))
    parts.append(r"\textbf{%s}: " % label + num_digits * "& " + r"\\")
    parts.append(r"\cline{2-%d}" % (1 + num_digits))
    parts.append(r"\end{tabular}")
    if box_width is not None:
        parts.append("}")
    parts.append(r"\end{center}")
    return "\n".join(parts)


def id_num_digits(parts):
    """Returns the tuple (label, number of digits) for the ID box.

       Receives the splitted text of the template for the exam, which
       may contain a key like 'id-box(9,NIA)' in an odd position, in
       which NIA is the label and 9 the number of digits. If the key
       does not exist in the template, returns (0, None).

    """
    # Replacement keys are in odd positions of the list
    for part in parts[1::2]:
        if part.startswith("id-box"):
            data = part[7:-1].split(",")
            # data[0] is num_digits; data[1] is label
            return data[1], int(data[0])
    return None, 0


def compute_table_dimensions(num_questions, num_choices, num_tables):
    """Computes and returns dimensions for answer tables.

       The result is a list of tuples in which each element contains
       the pair (num_cols, num_rows) for each table.

    """
    if num_questions < PARAM_MIN_NUM_QUESTIONS:
        raise utils.EyegradeException("", key="too_few_questions")
    if num_choices < 2:
        raise utils.EyegradeException("", key="too_few_choices")
    if num_tables <= 0:
        num_tables = _choose_num_tables(num_questions)
    elif num_tables * 2 > num_questions:
        raise utils.EyegradeException("", key="too_many_tables")
    dimensions = []
    rows_per_table, extra_rows = divmod(num_questions, num_tables)
    for i in range(0, num_tables):
        if i < extra_rows:
            num_rows = rows_per_table + 1
        else:
            num_rows = rows_per_table
        dimensions.append((num_choices, num_rows))
    return dimensions


def table_geometry(dimensions):
    num_cols = [table[0] for table in dimensions]
    num_rows = 2 + max([table[1] for table in dimensions])
    tables = []
    for i in range(0, num_rows):
        row = []
        for j, num_choices in enumerate(num_cols):
            if i < dimensions[j][1]:
                row.append(num_choices)
            elif i == dimensions[j][1]:
                row.append(-1)
            elif i == dimensions[j][1] + 1:
                row.append(-2)
            else:
                row.append(0)
        tables.append(row)
    question_numbers = [1]
    for i in range(0, len(dimensions) - 1):
        question_numbers.append(question_numbers[-1] + dimensions[i][1])
    return tables, question_numbers


def _choose_num_tables(num_questions):
    """Returns a good number of tables for the given number of questions."""
    num_tables = 1
    for numq in PARAM_TABLE_LMITS:
        if numq >= num_questions:
            break
        else:
            num_tables += 1
    return num_tables


def _horizontal_line(row_geometry, num_choices, compact):
    parts = []
    num_empty_columns = 1 if not compact else 0
    first = 2
    extra_line = max(row_geometry) > 0 or -1 in row_geometry
    for geometry in row_geometry:
        if geometry > 0 or geometry == -1 or extra_line:
            parts.append(r"\cline{%d-%d}" % (first, first + num_choices - 1))
        first += 1 + num_empty_columns + num_choices
    return " ".join(parts)


def _table_top(num_tables, num_choices, compact, table_width=None, table_height=None):
    middle_sep_format = "p{3mm}" if not compact else ""
    middle_sep_header = " & & " if not compact else " & "
    lines = [r"\begin{center}", r"\large"]
    if table_width is not None and table_height is None:
        lines.append(r"\resizebox{%fcm}{!}{" % table_width)
    elif table_width is None and table_height is not None:
        lines.append(r"\resizebox{!}{%fcm}{" % table_height)
    elif table_width is not None and table_height is not None:
        lines.append(r"\resizebox{%fcm}{%fcm}{" % (table_width, table_height))
    column_flags = middle_sep_format.join(
        num_tables * ["|".join(["r"] + num_choices * ["c"] + [""])]
    )
    lines.append(r"\begin{tabular}{" + column_flags + "}")
    parts = []
    for __ in range(num_tables):
        parts_internal = []
        parts_internal.append(r"\multicolumn{1}{c}{}")
        for j in range(num_choices):
            parts_internal.append(r"\multicolumn{1}{c}{%s}" % chr(65 + j))
        parts.append(" & ".join(parts_internal))
    lines.append(middle_sep_header.join(parts) + r" \\")
    return lines


def _build_row(
    num_row,
    row_geometry,
    question_numbers,
    num_choices,
    infobits_row,
    compact,
    left_to_right_numbering=False,
):
    parts = []
    for i, geometry in enumerate(row_geometry):
        if geometry > 0:
            if not left_to_right_numbering:
                cell_number = num_row + question_numbers[i]
            else:
                cell_number = i + 1 + len(row_geometry) * num_row
            parts.append(_build_question_cell(cell_number, geometry))
        elif geometry == -1:
            parts.append(infobits_row[0][i])
        elif geometry == -2:
            parts.append(infobits_row[1][i])
        else:
            parts.append(r"\multicolumn{%d}{c}{}" % (1 + num_choices))
    row = " & & ".join(parts) if not compact else " & ".join(parts)
    return row + r" \\"


def _build_question_cell(num_question, num_choices):
    parts = [str(num_question)]
    for i in range(0, num_choices):
        parts.append(r"\light{%s}" % chr(65 + i))
    return " & ".join(parts)


def _create_infobits(bits, num_tables, num_choices, survey_mode):
    column_active = r"\multicolumn{1}{c}{$\blacksquare$}"
    column_inactive = r"\multicolumn{1}{c}{}"
    parts = [[], []]
    for i in range(0, num_tables):
        data = bits[i * num_choices : (i + 1) * num_choices]
        for j in (0, 1):
            val = j == 1
            components = [column_inactive]
            for bit in data:
                if not survey_mode and val ^ bit:
                    components.append(column_active)
                else:
                    components.append(column_inactive)
            parts[j].append(" & ".join(components))
    return parts


def format_questions(exam, model, with_solution=False):
    """Returns the questions of 'exam' formatted in LaTeX, as a string.

       'exam' is a create.questions.ExamQuestions object. It writes the questions
       in their 'shuffled' order. If 'with_solution', correct answers
       are marked in the text.

    """
    data = []
    if exam.num_questions() > 0:
        if model == "0":
            groups = exam.questions.groups
        else:
            groups = exam.shuffled_groups[model]
        counter = 0
        for group in groups:
            data.extend(
                format_group(group, model, counter, with_solution=with_solution)
            )
            counter += len(group)
        if model != "0":
            data.append("\n\n% solutions: ")
            solutions, _ = exam.solutions_and_permutations(model)
            data.append(" ".join([str(n) for n in solutions]))
            data.append("\n")
    return "".join(data)


def format_group(group, model, question_counter, with_solution=False):
    if model != "0":
        data = format_group_variation(
            group, model, question_counter, with_solution=with_solution
        )
    else:
        # Model 0: present all the variations
        data = []
        for variation in range(group.num_variations):
            group.select_variation(model, variation)
            if group.num_variations > 1:
                data.extend(
                    f"\\vspace{{0.8cm}}\\noindent\\emph{{[var. {variation + 1}]}}\n"
                )
            data.extend(
                format_group_variation(
                    group, model, question_counter, with_solution=with_solution
                )
            )
    return data


def format_group_variation(group, model, question_counter, with_solution=False):
    data = []
    if group.common_text is not None:
        common_component = group.common_text.component(model)
    else:
        common_component = None
    if len(group) > 1:
        data.append("\n\\vspace{0.1cm}\n")
        data.append("\\[ \\overbrace{\\hspace{0.8\\textwidth}} \\]\n")
        if common_component is None:
            data.append("\n\\vspace{-0.5cm}\n")
    if common_component is not None:
        right_block = _right_block_selected(common_component)
        if right_block:
            data.append(_start_right_block(common_component))
        data.extend(format_question_component(common_component))
        if right_block:
            data.extend(_end_right_block(common_component))
    data.append("\\begin{enumerate}[1.-]\n")
    data.append("\\setcounter{enumi}{" + str(question_counter) + "}")
    for question in group:
        data.append("\\vspace{2mm}\n")
        data.extend(format_question(question, model, with_solution))
        data.append("\n")
    data.append("\\end{enumerate}\n")
    if len(group) > 1:
        data.append("\n\\vspace{-0.8cm}\n")
        data.append("\\[ \\underbrace{\\hspace{0.8\\textwidth}} \\]\n")
        data.append("\n\\vspace{0.1cm}\n")
    return data


def format_question(question, model, with_solution=False):
    """Returns a latex formatted question, as a list of strings.

       If 'with_solution', correct answers are marked in the text.

    """
    data = []
    choices = question.shuffled_choices(model)
    text_component = question.text(model)
    right_block = _right_block_selected(text_component)
    if right_block:
        data.append(_start_right_block(text_component))
    data.append(r"\item ")
    data.extend(format_question_component(text_component))
    data.append("\n  \\begin{enumerate}[(a)]\n")
    for choice in choices:
        data.append(r"    \item ")
        if with_solution and choice in question.correct_choices(model):
            data[-1] = data[-1] + r" \textbf{***} "
        data.extend(format_question_component(choice))
        data.append("\n")
    data.append("\n  \\end{enumerate}\n")
    if right_block:
        data.extend(_end_right_block(text_component))
    return data


def _right_block_selected(question_component):
    return (
        question_component.figure is not None or question_component.code is not None
    ) and question_component.annex_pos == "right"


def _start_right_block(question_component):
    width_right = question_component.annex_width + PARAM_TABLE_SEP
    width_left = 1 - width_right - PARAM_TABLE_MARGIN
    return (
        "\\hspace{-0.2cm}\\begin{tabular}[l]{p{%f\\textwidth}p{%f\\textwidth}}\n"
    ) % (width_left, width_right)


def _end_right_block(question_component):
    data = ["&\n"]
    if question_component.figure is not None:
        data.extend(
            write_figure(
                question_component.figure, question_component.annex_width, True
            )
        )
    elif question_component.code is not None:
        data.extend(write_code(question_component.code))
    data.append("\\\\\n\\end{tabular}\n")
    return data


def format_question_component(component):
    data = []
    if component.text is not None:
        if isinstance(component.text, str):
            data.append(component.text)
        else:
            for part in component.text:
                if part[0] == "text":
                    data.append(part[1])
                elif part[0] == "code":
                    data.extend(write_code(part[1]))
    if component.figure is not None and component.annex_pos == "center":
        data.extend(write_figure(component.figure, component.annex_width, True))
    elif component.code is not None and component.annex_pos == "center":
        data.extend(write_code(component.code))
    return data


def write_figure(figure, width, center):
    data = []
    if center:
        data.append("\\begin{center}\n")
    data.append("\\includegraphics[width=%f\\textwidth]{%s}\n" % (width * 0.9, figure))
    if center:
        data.append("\\end{center}\n")
    return data


def write_code(code):
    data = []
    data.append("\\begin{center}\n" "\\begin{verbatim}\n")
    data.append(code + "\n")
    data.append("\\end{verbatim}\n" "\\end{center}")
    return data


def re_id_box_replacer(match):
    """Takes a re.match object and returns the id box.

    Two groups expected: (1) number of digits; (2) label to show.

    """
    return create_id_box(match.group(2), int(match.group(1)))
