import re
import copy
import sys

# Local imports
import utils

param_min_num_questions = 1

# For formatting questions
param_table_sep = 0.05
param_table_margin = 0.1

# Numbers of questions in which the number of tables is changed
param_table_limits = [8, 24, 55]
re_split_template = re.compile('{{([^{}]+)}}')

class ExamMaker(object):
    def __init__(self, num_questions, num_choices, template_filename,
                 output_file, variables, exam_config_filename,
                 num_tables=0, dimensions=None,
                 table_width=None, id_box_width=None):
        """
           Class able to create exams. One object is enough for all models.

        """
        self.num_questions = num_questions
        self.num_choices = num_choices
        template = utils.read_file(template_filename)
        self.parts = re_split_template.split(template)
        self.output_file = output_file
        self.exam_questions = None
        self.table_width = table_width
        self.id_box_width = id_box_width
        id_label, self.id_num_digits = id_num_digits(self.parts)
        self.__load_replacements(variables, id_label)
        self.exam_config_filename = exam_config_filename
        if (num_tables > 0 and dimensions is not None and
            len(dimensions) != num_tables):
            raise Exception('Incoherent number of tables')
        if dimensions is not None:
            self.dimensions = dimensions
        else:
            self.dimensions = compute_table_dimensions(num_questions,
                                                       num_choices, num_tables)
        if self.exam_config_filename is not None:
            self.__load_exam_config()
        else:
            self.exam_config = None

    def set_exam_questions(self, exam):
        if exam.num_questions() != self.num_questions:
            raise Exception('Incorrect number of questions')
        self.exam_questions = exam

    def create_exam(self, model, shuffle, with_solution=False):
        """Creates a new exam.

           'shuffle' must be a boolean. If True, the exam is shuffled
           again even if it was previously shuffled. If False, it is
           only shuffled if it was not previously shuffled.

        """
        if model is None or len(model) != 1 or ((ord(model) < 65 or \
                 ord(model) > 90) and model != '0'):
            raise Exception('Incorrect model value')
        replacements = copy.copy(self.replacements)
        answer_table = create_answer_table(self.dimensions, model,
                                           self.table_width)
        if self.exam_config is not None:
            if self.exam_config.dimensions == []:
                self.exam_config.dimensions = self.dimensions
            if model != '0' and not model in self.exam_config.models:
                self.exam_config.models.append(model)
        if self.exam_questions is not None:
            if model != '0':
                if (self.exam_config is None or
                    not model in self.exam_config.permutations or
                    (model in self.exam_config.permutations and shuffle)):
                    print "shuffling model", model
                    self.exam_questions.shuffle(model)
                    if self.exam_config is not None:
                        solutions, permutations = \
                          self.exam_questions.solutions_and_permutations(model)
                        self.exam_config.solutions[model] = solutions
                        self.exam_config.permutations[model] = permutations
                else:
                    p = self.exam_config.permutations[model]
                    self.exam_questions.set_permutation(model, p)
            replacements['questions'] = format_questions(self.exam_questions,
                                                         model, with_solution)
        replacements['answer-table'] = answer_table
        replacements['model'] = model
        replacements['declarations'] = latex_declarations(with_solution)

        # Replacement keys are in odd positions of self.parts
        replaced = len(self.parts) * [None]
        replaced[::2] = self.parts[::2]
        replaced[1::2] = [self.__replace(key, replacements) \
                              for key in self.parts[1::2]]
        exam_text = ''.join(replaced)
        if self.output_file == sys.stdout:
            utils.write_to_stdout(exam_text)
        else:
            utils.write_file(self.output_file%model, exam_text)

    def save_exam_config(self):
        if self.exam_config is not None:
            self.exam_config.save(self.exam_config_filename)

    def __load_exam_config(self):
        if self.exam_config_filename is not None:
            try:
                self.exam_config = utils.ExamConfig(self.exam_config_filename)
                if self.num_questions != self.exam_config.num_questions:
                    raise Exception('Incoherent number of questions')
                if self.id_num_digits != self.exam_config.id_num_digits:
                    raise Exception('Incoherent configuration of id box')
                if self.dimensions != self.exam_config.dimensions:
                    raise Exception('Incoherent table dimensions')
            except IOError:
                self.exam_config = utils.ExamConfig()
                self.exam_config.num_questions = self.num_questions
                self.exam_config.id_num_digits = self.id_num_digits

    def __load_replacements(self, variables, id_label):
        self.replacements = copy.copy(variables)
        self.replacements['id-box'] = create_id_box(id_label,
                                                    self.id_num_digits,
                                                    self.id_box_width)
        self.replacements['questions'] = ''

    def __replace(self, key, replacements):
        if key in replacements:
            return replacements[key]
        elif key.startswith('id-box'):
            return replacements['id-box']
        else:
            raise Exception('Unknown replacement key: ' + key)

def latex_declarations(with_solution):
    """Returns the list of declarations to be set in the preamble
       of the LaTeX output.

    """
    data = [r'\usepackage[dvipdf]{graphicx}',
            r'\usepackage{fancyvrb}',
            r'\usepackage{enumerate}',
            r'\usepackage{color}',
            r'\definecolor{lightgray}{rgb}{1, 1, 1}',
            r'\newcommand{\light}[1]{\textcolor{lightgray}{#1}}',
            r'\definecolor{hidden}{rgb}{1, 1, 1}',
            r'\newcommand{\hidden}[1]{\textcolor{hidden}{#1}}',
            r'\newif\ifsolutions']
    if with_solution:
        data.append(r'\solutionstrue')
    else:
        data.append(r'\solutionsfalse')
    return '\n'.join(data)

def create_answer_table(dimensions, model, table_width=None):
    """Returns a string with the answer tables of the answer sheet.

       Tables are LaTeX-formatted. 'dimensions' specifies the geometry
       of the tables. 'model' is a one letter string with the name of
       the model, or '0' for the un-shuffled exam. 'table_width' is
       the desired width of the answer table, in cm. None for the default
       width.

    """
    if len(dimensions) == 0:
        raise Exception('No tables defined in dimensions')
    compact = (len(dimensions) > 2)
    num_choices = dimensions[0][0]
    num_tables = len(dimensions)
    for d in dimensions:
        if d[0] != num_choices:
            raise Exception(('By now, all tables must have the same number'
                             ' of choices'))
    if model != '0':
        bits = utils.encode_model(model, num_tables, num_choices)
    else:
        bits = [False] * num_tables * num_choices
    bits_rows = __create_infobits(bits, num_tables, num_choices)
    tables, question_numbers = table_geometry(dimensions)
    rows = __table_top(num_tables, num_choices, compact, table_width)
    for i, row_geometry in enumerate(tables):
        rows.append(__horizontal_line(row_geometry, num_choices, compact))
        rows.append(__build_row(i, row_geometry, question_numbers,
                                num_choices, bits_rows, compact))
    rows.append(r'\end{tabular}')
    if table_width is not None:
        rows.append('}')
    rows.append(r'\end{center}')
    return '\n'.join(rows)

def create_id_box(label, num_digits, box_width=None):
    """Creates the ID box given a label to show and number of digits.

    """
    parts = [r'\begin{center}', r'\Large']
    if box_width is not None:
        parts.append(r'\resizebox{%fcm}{!}{'%box_width)
    parts.append(r'\begin{tabular}{l|' + num_digits * 'p{3mm}|' + '}')
    parts.append(r'\cline{2-%d}'%(1 + num_digits))
    parts.append(r'\textbf{%s}: '%label + num_digits * '& ' + r'\\')
    parts.append(r'\cline{2-%d}'%(1 + num_digits))
    parts.append(r'\end{tabular}')
    if box_width is not None:
        parts.append('}')
    parts.append(r'\end{center}')
    return '\n'.join(parts)

def id_num_digits(parts):
    """Returns the tuple (label, number of digits) for the ID box.

       Receives the splitted text of the template for the exam, which
       may contain a key like 'id-box(9,NIA)' in an odd position, in
       which NIA is the label and 9 the number of digits. If the key
       does not exist in the template, returns (0, None).

    """
    # Replacement keys are in odd positions of the list
    for part in parts[1::2]:
        if part.startswith('id-box'):
            data = part[7:-1].split(',')
            # data[0] is num_digits; data[1] is label
            return data[1], int(data[0])
    return None, 0

def compute_table_dimensions(num_questions, num_choices, num_tables):
    """Computes and returns dimensions for answer tables.

       The result is a list of tuples in which each element contains
       the pair (num_cols, num_rows) for each table.

    """
    if num_questions < param_min_num_questions:
        raise Exception('Too few questions')
    if num_choices < 2:
        raise Exception('Too few answers per question')
    if num_tables <= 0:
        num_tables = __choose_num_tables(num_questions)
    elif num_tables * 2 > num_questions:
        raise Exception('Too many tables for the given number of questions')
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

def __choose_num_tables(num_questions):
    """Returns a good number of tables for the given number of questions."""
    num_tables = 1
    for numq in param_table_limits:
        if numq >= num_questions:
            break
        else:
            num_tables += 1
    return num_tables

def __horizontal_line(row_geometry, num_choices, compact):
    parts = []
    num_empty_columns = 1 if not compact else 0
    first = 2
    for i, geometry in enumerate(row_geometry):
        if geometry > 0 or geometry == -1:
            parts.append(r'\cline{%d-%d}'%(first, first + num_choices - 1))
        first += 1 + num_empty_columns + num_choices
    return ' '.join(parts)

def __table_top(num_tables, num_choices, compact, table_width=None):
    middle_sep_format = 'p{3mm}' if not compact else ''
    middle_sep_header = ' & & ' if not compact else ' & '
    lines = [r'\begin{center}', r'\large']
    if table_width is not None:
        lines.append(r'\resizebox{%fcm}{!}{'%table_width)
    l = middle_sep_format.join(num_tables
                               * ['|'.join(['r'] + num_choices * ['c'] + [''])])
    l = r'\begin{tabular}{' + l + '}'
    lines.append(l)
    parts = []
    for i in range(0, num_tables):
        parts_internal = []
        parts_internal.append(r'\multicolumn{1}{c}{}')
        for j in range(0, num_choices):
            parts_internal.append(r'\multicolumn{1}{c}{%s}'%chr(65 + j))
        parts.append(' & '.join(parts_internal))
    lines.append(middle_sep_header.join(parts) + r' \\')
    return lines

def __build_row(num_row, row_geometry, question_numbers, num_choices,
                infobits_row, compact):
    parts = []
    num_empty_columns = 1 if not compact else 0
    skip_cells = 0
    for i, geometry in enumerate(row_geometry):
        if geometry > 0:
            parts.append(__build_question_cell(num_row + question_numbers[i],
                                               geometry))
        elif geometry == -1:
            parts.append(infobits_row[0][i])
        elif geometry == -2:
            parts.append(infobits_row[1][i])
        else:
            parts.append('\multicolumn{%d}{c}{}'%(1 + num_choices))
    row = ' & & '.join(parts) if not compact else ' & '.join(parts)
    return row + r' \\'

def __build_question_cell(num_question, num_choices):
    parts = [str(num_question)]
    for i in range(0, num_choices):
        parts.append(r'\light{%s}'%chr(65 + i))
    return ' & '.join(parts)

def __create_infobits(bits, num_tables, num_choices):
    column_active = r'\multicolumn{1}{c}{$\blacksquare$}'
    column_inactive = r'\multicolumn{1}{c}{}'
    parts = [[], []]
    for i in range(0, num_tables):
        data = bits[i * num_choices: (i + 1) * num_choices]
        for j in (0, 1):
            val = (j == 1)
            components = [column_inactive]
            for bit in data:
                if val ^ bit:
                    components.append(column_active)
                else:
                    components.append(column_inactive)
            parts[j].append(' & '.join(components))
    return parts

def format_questions(exam, model, with_solution=False):
    """Returns the questions of 'exam' formatted in LaTeX, as a string.

       'exam' is a utils.ExamQuestions object. Writtes the questions
       in their 'shuffled' order. If 'with_solution', correct answers
       are marked in the text.

    """
    data = []
    if exam.num_questions() > 0:
        if model == '0':
            questions = exam.questions
        else:
            questions = exam.shuffled_questions[model]
        data.append('\\begin{enumerate}[1.-]\n')
        for question in questions:
            data.append('\\vspace{2mm}\n')
            data.extend(format_question(question, model, with_solution))
            data.append('\n')
        data.append('\\end{enumerate}\n')
        if model != '0':
            data.append('\n\n% solutions: ')
            solutions, permutations = exam.solutions_and_permutations(model)
            data.append(' '.join([str(n) for n in solutions]))
            data.append('\n')
    return ''.join(data)

def format_question(question, model, with_solution=False):
    """Returns a latex formatted question, as a list of strings.

       If 'with_solution', correct answers are marked in the text.

    """
    data = []
    if model == '0':
        choices = question.correct_choices + question.incorrect_choices
    else:
        choices = question.shuffled_choices[model]
    if ((question.text.figure is not None
         or question.text.code is not None) and
        question.text.annex_pos == 'right'):
        width_right = question.text.annex_width + param_table_sep
        width_left = 1 - width_right - param_table_margin
        data.append('\\hspace{-0.2cm}\\begin{tabular}[l]{p{%f\\textwidth}'
                    'p{%f\\textwidth}}\n'%(width_left, width_right))
    data.append(r'\item ')
    data.extend(format_question_component(question.text))
    data.append('\n  \\begin{enumerate}[(a)]\n')
    for choice in choices:
        data.append(r'    \item ')
        if with_solution and choice in question.correct_choices:
            data[-1] = data[-1] + r' \textbf{***} '
        data.extend(format_question_component(choice))
        data.append('\n')
    data.append('\n  \\end{enumerate}\n')
    if ((question.text.figure is not None
         or question.text.code is not None) and
        question.text.annex_pos == 'right'):
        data.append('&\n')
        if question.text.figure is not None:
            data.extend(write_figure(question.text.figure,
                                     question.text.annex_width))
        elif question.text.code is not None:
            data.extend(write_code(question.text.code))
        data.append('\\\\\n\\end{tabular}\n')
    return data

def format_question_component(component):
    data = []
    if component.text is not None:
        data.append(component.text)
    if component.figure is not None and component.annex_pos == 'center':
        data.extend(write_figure(component.figure,
                                 component.annex_width))
    elif component.code is not None and component.annex_pos == 'center':
        data.extend(write_code(component.code))
    return data

def write_figure(figure, width):
    data = []
    data.append('\\begin{center}\n')
    data.append('\\includegraphics[width=%f\\textwidth]{%s}\n'%\
                    (width * 0.9, figure))
    data.append('\\end{center}\n')
    return data

def write_code(code):
    data = []
    data.append('\\begin{center}\n'
                '\\begin{verbatim}\n')
    data.append(code + '\n')
    data.append('\\end{verbatim}\n'
                '\\end{center}')
    return data

def re_id_box_replacer(match):
    """Takes a re.match object and returns the id box.

    Two groups expected: (1) number of digits; (2) label to show.

    """
    return create_id_box(match.group(2), int(match.group(1)))
