#import utils

param_min_num_questions = 4

# Numbers of questions in which the number of tables is changed
param_table_limits = [8, 24, 48]

def create_answer_table(num_questions, num_answers, num_tables = 0):
    """Returns a string with the answer tables of the asnwer sheet.

       Tables are LaTeX-formatted. 'num_questions' specifies the
       number of questions of the exam. 'num_answers' specifies the
       number of answers per question. 'num_tables' (optional)
       specifies the number of tables. If not specified or set to a
       non-positive vale, a number of tables that best fits the number
       of questions is chosen.

    """
    if num_questions < param_min_num_questions:
        raise Exception('Too few questions')
    if num_answers < 2:
        raise Exception('Too few answers per question')
    if num_tables <= 0:
        num_tables = __choose_num_tables(num_questions)
    elif num_tables * 2 > num_questions:
        raise Exception('Too many tables for the given number of questions')
    tables, question_numbers = __table_geometry(num_questions, num_answers,
                                                num_tables)
    rows = __table_top(num_tables, num_answers)
    hline = __horizontal_line(tables[0])
    for i, row_geometry in enumerate(tables):
        rows.append(hline)
        rows.append(__build_row(i, row_geometry, question_numbers))
    rows.append('\\end{tabular}')
    return '\n'.join(rows)

def __choose_num_tables(num_questions):
    """Returns a good number of tables for the given number of questions."""
    num_tables = 1
    for numq in param_table_limits:
        if numq >= num_questions:
            break
        else:
            num_tables += 1
    return num_tables

def __table_geometry(num_questions, num_answers, num_tables):
    """Returns the geometry of the answer tables.

       The result is a tuple (tables, question_numbers) where:
       - 'tables' is a bidimensional list such that table[row][column]
       represents the number of answers for the question in 'row' /
       'column'. If 0, the question does not exist.
       - 'question_numbers' is a list with the number of question of
       the first row of each table. The first question is numbered as
       1.

    """
    rows_per_table = num_questions // num_tables
    tables = rows_per_table * [num_tables * [num_answers]]
    question_numbers = []
    for i in range(0, num_tables):
        question_numbers.append(1 + i * rows_per_table)
    diff = num_questions - num_tables * rows_per_table
    if diff > 0:
        last_row = diff * [num_answers]
        last_row.extend((num_tables - diff) * [0])
        tables.append(last_row)
        acc = 0
        for i in range(1, num_tables):
            if i <= diff:
                acc += 1
            question_numbers[i] += acc
    return tables, question_numbers

def __horizontal_line(row_geometry):
    parts = []
    first = 2
    for i, num_questions in enumerate(row_geometry):
        if num_questions > 0:
            parts.append('\\cline{%d-%d}'%(first, first + num_questions - 1))
            first += 2 + num_questions
    return ' '.join(parts)

def __table_top(num_tables, num_answers):
    l = 'p{3mm}'.join(num_tables
                      * ['|'.join(['r'] + num_answers * ['c'] + [''])])
    l = '\\begin{tabular}{' + l + '}'
    lines = [l]
    parts = []
    for i in range(0, num_tables):
        parts.append('\\multicolumn{1}{c}{}')
        for j in range(0, num_answers):
            parts.append('\\multicolumn{1}{c}{%s}'%chr(65 + j))
    lines.append(' & '.join(parts) + ' \\\\')
    return lines

def __build_row(num_row, row_geometry, question_numbers):
    parts = []
    skip_cells = 0
    for i, num_answers in enumerate(row_geometry):
        if num_answers > 0:
            parts.append(__build_question_cell(num_row + question_numbers[i],
                                               num_answers))
        else:
            skip_cells += 2 + row_geometry[0]
    row = ' & & '.join(parts)
    if skip_cells > 0:
        row += ' & \\multicolumn{%d}{c}{}'%skip_cells
    return row + ' \\\\'

def __build_question_cell(num_question, num_answers):
    parts = [str(num_question)]
    for i in range(0, num_answers):
        parts.append('\\light{%s}'%chr(65 + i))
    return ' & '.join(parts)
