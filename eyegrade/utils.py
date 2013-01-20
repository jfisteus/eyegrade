# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2013 Jesus Arias Fisteus
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

import ConfigParser
import csv
import os
import locale
import codecs
import sys
import random
import re
import io
import fractions

program_name = 'eyegrade'
web_location = 'http://www.it.uc3m.es/jaf/eyegrade/'
source_location = 'https://github.com/jfisteus/eyegrade'
help_location = 'http://www.it.uc3m.es/jaf/eyegrade/doc/user-manual/'
version = '0.1.17'
version_status = 'alpha'

re_model_letter = re.compile('[0a-zA-Z]')

csv.register_dialect('tabs', delimiter = '\t')

results_file_keys = ['seq-num', 'student-id', 'model', 'good', 'bad',
                     'unknown', 'answers']


class EyegradeException(Exception):
    """An Eyegrade-specific exception.

    In addition to what a normal exception would do, it encapsulates
    user-friendly messages for some common causes of error due to
    the user.

    """

    _error_messages = {}
    _short_messages = {}

    def __init__(self, message, key=None):
        """Creates a new exception.

        If `key` is in `_error_messages`, a prettier version of the
        exception will be shown to the user, with the explanation appended
        to the end of what you provide in `message`.

        """
        if (key in EyegradeException._error_messages
            or key in EyegradeException._short_messages):
            parts = ['ERROR: ']
            if message:
                parts.append(message)
            elif key in EyegradeException._short_messages:
                parts.append(EyegradeException._short_messages[key])
            if key in EyegradeException._error_messages:
                parts.append('\n\n')
                parts.append(EyegradeException._error_messages[key])
            parts.append('\n')
            self.full_message = ''.join(parts)
            super(EyegradeException, self).__init__(self.full_message)
        else:
            self.full_message = None
            super(EyegradeException, self).__init__(message)

    def __str__(self):
        """Prints the exception.

        A user-friendly message, without the stack trace, is shown when such
        user-friendly message is available.

        """
        if self.full_message is not None:
            return self.full_message
        else:
            return super(EyegradeException, self).__str__()

    @staticmethod
    def register_error(key, detailed_message='', short_message=''):
        """Registers a new error message associated to a key.

        `key` is just a string used to identify this error message,
        that must be passed when creating exception
        objects. `detailed_message` is a (possibly long and with end
        of line characters inside) explanation of the
        error. `short_message` is a one line error message to be used
        only when a blank message is passed when creating the
        exception.

        Being this method static, messages added through it will be
        shared for all the instances of the exception.

        """
        if (not key in EyegradeException._error_messages
            and not key in EyegradeException._short_messages):
            if detailed_message:
                EyegradeException._error_messages[key] = detailed_message
            if short_message:
                EyegradeException._short_messages[key] = short_message
        else:
            raise EyegradeException('Duplicate error key in register_error')


EyegradeException.register_error('bad_dimensions',
    "Dimensions must be specified as a ';' separated list of tables.\n"
    "For each table, specify the number of choices + comma + the number of\n"
    "questions in that table. For example, '4,10;4,9' configures two\n"
    "tables, the left-most with 9 questions and 4 choices per question,\n"
    "and the right-most with 10 questions and the same number of choices."
    'Bad dimensions value.')

EyegradeException.register_error('same_num_choices',
    "By now, Eyegrade needs you to use the same number of choices in\n"
    "all the questions of the exam.",
    'There are questions with a different number of choices')

EyegradeException.register_error('error_student_list',
    'The syntax of the student list is not correct.\n'
    'The file is expected to contain one line per student.\n'
    'Each line can contain one or more TAB-separated columns.\n'
    'The first column must be the student id (a number).\n'
    'The second column, if present, is interpreted as the student name.\n'
    'The rest of the columns are ignored.')


def guess_data_dir():
    path = os.path.split(os.path.realpath(__file__))[0]
    if path.endswith('.zip'):
        path = os.path.split(path)[0]
    paths_to_try = [os.path.join(path, 'data'),
                    os.path.join(path, '..', 'data'),
                    os.path.join(path, '..', '..', 'data'),
                    os.path.join(path, '..', '..', '..', 'data')]
    for p in paths_to_try:
        if os.path.isdir(p):
            return os.path.abspath(p)
    raise Exception('Data path not found!')

data_dir = guess_data_dir()

def resource_path(file_name):
    return os.path.join(data_dir, file_name)

def read_results(filename, permutations = {}, allow_question_mark=False):
    """Parses an eyegrade results file.

       Results are returned as a list of dictionaries with the keys
       stored in the 'results_file_keys' variable. If 'permutations'
       is provided, answers are un-shuffled.

    """
    results = _read_results_file(filename)
    for result in results:
        result['model'] = check_model_letter(result['model'],
                                       allow_question_mark=allow_question_mark)
        result['good'] = int(result['good'])
        result['bad'] = int(result['bad'])
        result['unknown'] = int(result['unknown'])
        answers = [int(n) for n in result['answers'].split('/')]
        if len(permutations) > 0:
            answers = _permute_answers(answers, permutations[result['model']])
        result['answers'] = answers
    return results

def write_results(results, filename, csv_dialect, append=False):
    """Writes exam results to a file.

       If filename is None, results are written to stdout. The output
       file is overwritting by default. Use append=True to append
       instead of overwriting.

    """
    if filename is not None:
        if not append:
            file_ = open(filename, 'wb')
        else:
            file_ = open(filename, 'ab')
    else:
        file_ = sys.stdout
    writer = csv.writer(file_, dialect = csv_dialect)
    for result in results:
        data = [str(result['seq-num']),
                result['student-id'],
                result['model'],
                str(result['good']),
                str(result['bad']),
                str(result['unknown']),
                '/'.join([str(d) for d in result['answers']])]
        writer.writerow(data)
    if filename is not None:
        file_.close()

def check_model_letter(model, allow_question_mark=False):
    """Checks if a model letter is correct.

    The special value '?' is considered valid only if the parameter
    `allow_question_mark` is set.

    """
    if re_model_letter.match(model):
        return model.upper()
    elif allow_question_mark and model == '?':
        return '?'
    else:
        raise Exception('Incorrect model letter: ' + model)

def read_student_ids(filename=None, file_=None, data=None, with_names=False):
    """Reads the list of student IDs from a CSV-formatted file (tab-separated).

    Either 'filename', 'file_' or 'data' must be provided.  'filename'
    specifies the name of a file to read.  'file_' is a file object
    instead of a file name.  'data' must be a string that contains the
    actual content of the config file to be parsed. Only one of them
    should not be None, although this restriction is not enforced: the
    first one not to be None, in the same order they are specified in
    the function, is used.

    """
    assert((filename is not None) or (file_ is not None)
           or (data is not None))
    csvfile = None
    if filename is not None:
        csvfile = open(filename, 'rb')
        reader = csv.reader(csvfile, 'tabs')
    elif file_ is not None:
        reader = csv.reader(file_, 'tabs')
    elif data is not None:
        reader = csv.reader(io.BytesIO(data), 'tabs')
    if not with_names:
        student_ids = [row[0] for row in reader]
    else:
        student_ids = {}
        for row in reader:
            if len(row) == 0:
                raise EyegradeException('Empty line in student list',
                                        key='error_student_list')
            sid = row[0]
            if len(row) > 1:
                name = row[1]
                student_ids[sid] = unicode(name, locale.getpreferredencoding())
            else:
                name = None
                student_ids[sid] = None
    if csvfile is not None:
        csvfile.close()
    return student_ids

def read_student_ids_multiple(filenames, with_names=False):
    """Reads student ids from multiple files.

    `filenames` is an iterable of filenames. It may be empty. `with_names`
    has the same meaning as in `read_student_ids(...)`.

    Returns a combined list or dictionary, depending on the value of
    `with_names`.

    """
    if not with_names:
        st = []
        for f in filenames:
            st.extend(read_student_ids(filename=f, with_names=False))
    else:
        st = {}
        for f in filenames:
            st.update(read_student_ids(filename=f, with_names=True))
    return st

def mix_results(results_filename, student_list_filename, dump_missing):
    """Returns a list of tuples student_id, good_answers, bad_answers.

       Receives the names of the files with results and student list.
       If 'dump_missing' is True, grades of students not in the
       student list are dumped at the end of the list.

    """
    mixed_grades = []
    results = results_by_id(read_results(results_filename))
    ids = read_student_ids(filename=student_list_filename)
    for student_id in ids:
        if student_id in results:
            mixed_grades.append((student_id, results[student_id][0],
                                 results[student_id][1]))
        else:
            mixed_grades.append((student_id, '', ''))
    if dump_missing:
        for student_id in results:
            if not student_id in ids:
                mixed_grades.append((student_id, results[student_id][0],
                                     results[student_id][1]))
    return mixed_grades

def mix_results_extra_grades(results_filename, student_list_filename,
                             extra_grades_filename, dump_missing):
    """Returns a list of tuples student_id, good_answers, bad_answers, <extra>

       Receives the names of the files with results and student list.
       If 'dump_missing' is True, grades of students not in the
       student list are dumped at the end of the list.
       <extra> represents as many data as columns 1:... in the extra file
       (column 0 in that file is the student id).

    """
    mixed_grades = mix_results(results_filename, student_list_filename,
                               dump_missing)
    csvfile = open(extra_grades_filename, 'rb')
    reader = csv.reader(csvfile, 'tabs')
    extra_grades = {}
    for line in reader:
        if len(line) < 2:
            raise Exception('Incorrect line in extra grades file')
        extra_grades[line[0]] = tuple(line[1:])
    csvfile.close()
    ids = []
    for i in range(0, len(mixed_grades)):
        student_id = mixed_grades[i][0]
        ids.append(student_id)
        if student_id in extra_grades:
            mixed_grades[i] = mixed_grades[i] + extra_grades[student_id]
    if dump_missing:
        for student_id in extra_grades:
            if not student_id in ids:
                mixed_grades.append(((student_id, 0, 0) +
                                     extra_grades[student_id]))
    return mixed_grades

def write_grades(grades, file_, csv_dialect):
    """Writes the given grades to a file.

       Results are a list of tuples student_id, good_answers, bad_answers.

    """
    writer = csv.writer(file_, dialect = csv_dialect)
    for grade in grades:
        writer.writerow(grade)

def results_by_id(results):
    """Returns a dictionary student_id -> (num_good_answers, num_bad_answers).

       Results must be formatted as returned by read_results().

    """
    id_dict = {}
    for r in results:
        id_dict[r['student-id']] = (r['good'], r['bad'])
    return id_dict

def read_config():
    """Reads the general config file and returns the resulting config object.

    """
    config = {'camera-dev': '0',
              'save-filename-pattern': 'exam-{student-id}-{seq-number}.png',
              'csv-dialect': 'tabs'}
    parser = ConfigParser.SafeConfigParser()
    parser.read([os.path.expanduser('~/.eyegrade.cfg'),
                 os.path.expanduser('~/.camgrade.cfg')])
    if 'default' in parser.sections():
        for option in parser.options('default'):
            config[option] = parser.get('default', option)
    if not config['csv-dialect'] in csv.list_dialects():
        config['csv-dialect'] = 'tabs'
    if 'error-logging' in config and config['error-logging'] == 'yes':
        config['error-logging'] = True
    else:
        config['error-logging'] = False
    config['camera-dev'] = int(config['camera-dev'])
    return config

def _read_results_file(filename):
    csvfile = open(filename, 'rb')
    dialect = csv.Sniffer().sniff(csvfile.read(1024))
    csvfile.seek(0)
    reader = csv.DictReader(csvfile, fieldnames = results_file_keys,
                            dialect = dialect)
    entries = [entry for entry in reader]
    csvfile.close()
    return entries

def _permute_answers(answers, permutation):
    assert(len(answers) == len(permutation))
    permutted = [0] * len(answers)
    for i, option in enumerate(answers):
        if option == 0 or option == -1:
            resolved_option = option
        else:
            resolved_option = permutation[i][1][option - 1]
        permutted[permutation[i][0] - 1] = resolved_option
    return permutted

def encode_model(model, num_tables, num_answers):
    """Given the letter of the model, returns the infobits pattern.

       It is formatted as an array of booleans string where the pos. 0
       is the one that goes in the column of the table at the left.
       The length of the string is 'num_tables' * 'num_answers', where
       'num_tables' is the number of answer tables and 'num_tables'
       the number of answers per question. The 'model' must be a
       capital ASCII letter.

    """
    if len(model) != 1 or model < 'A' or model > 'Z':
        raise Exception('Incorrect model letter')
    if model > 'H':
        raise Exception('Model is currently limited to A - H')
    model_num = ord(model) - 65
    num_bits = num_tables * num_answers
    if model_num >= 2 ** (num_bits - 1):
        raise Exception('Model number too big given the number of answers')
    seed = _int_to_bin(model_num, 3, True)
    seed[2] = not seed[2]
    seed.append(reduce(lambda x, y: x ^ y, seed))
    seed[2] = not seed[2]
    bit_list = seed * (1 + (num_bits - 1) // 4)
    return bit_list[:num_tables * num_answers]

def decode_model(bit_list, accept_model_0=False):
    """Given the bits that encode the model, returns the associated letter.

       It decoding/checksum fails, None is returned. The list of bits must
       be a list of boolean variables.

       The special model 0 is not valid unless `accept_model_0` is set.

    """
    # x3 = x0 ^ x1 ^ not x2; x0-x3 == x4-x7 == x8-x11 == ...
    valid = False
    if len(bit_list) == 3:
        valid = True
    elif len(bit_list) >= 4:
        if (bit_list[3] == bit_list[0] ^ bit_list[1] ^ (not bit_list[2])):
            valid = True
            for i in range(4, len(bit_list)):
                if bit_list[i] != bit_list[i - 4]:
                    valid = False
                    break
    if valid:
        return chr(65 + (int(bit_list[0]) | int(bit_list[1]) << 1 |
                  int(bit_list[2]) << 2))
    elif accept_model_0 and max(bit_list) == False:
        return '0'
    else:
        return None

def _int_to_bin(n, num_digits, reverse = False):
    """Returns the binary representation of a number as a list of booleans.

       If the number of digits is less than 'num_digits', it is
       completed with False in the most-significative side. If
       'reverse' is True returns the least significative bit in the
       first position of the string.

       There is a bin() function in python >= 2.6, but by now we want
       the program to be compatible with 2.5. Anyway, the behaviour of
       that function is different.

    """
    bin = []
    while n > 0:
        n, r = divmod(n, 2)
        bin.append(True if r else False)
    if len(bin) < num_digits:
        bin.extend([False] * (num_digits - len(bin)))
    if reverse:
        return bin
    else:
        return bin[::-1]

def read_file(file_name):
    """Returns contents of a file as a Unicode string using terminal locale.

    """
    file_ = codecs.open(file_name, 'r', locale.getpreferredencoding())
    data = file_.read()
    file_.close()
    return data

def write_file(file_name, unicode_text):
    """Writes a Unicode string in a file using terminal locale.

    """
    file_ = codecs.open(file_name, 'w', locale.getpreferredencoding())
    file_.write(unicode_text)
    file_.close()

def write_to_stdout(unicode_text):
    """Writes a Unicode string in sys.stdout using terminal locale.

    """
    writer = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)
    writer.write(unicode_text)

def increment_list(list_):
    """Adds one to every element in a list of integers. Returns a new list.

    """
    return [n + 1 for n in list_]

# Some regular expressions used in class Exam
regexp_id = re.compile('\{student-id\}')
regexp_seqnum = re.compile('\{seq-number\}')

class Exam(object):
    def __init__(self, image, model, solutions, valid_student_ids,
                 im_id, score_weights, save_image_func=None,
                 save_stats=False):
        self.image = image
        self.model = model
        self.solutions = solutions
        self.im_id = im_id
        self.correct = None
        self.score = None
        self.save_stats = save_stats
        self.student_names = valid_student_ids
        if self.image.options['read-id']:
            self.student_id = self.decide_student_id(valid_student_ids)
        else:
            # Allow manual insertion of ID even if OCR detection
            # is not done
            self.student_id = '-1'
            if valid_student_ids is not None:
                self.ids_rank = [(0, sid) for sid in valid_student_ids]
            else:
                self.ids_rank = []
        self.locked = False
        self.score_weights = score_weights
        self.save_image_function = save_image_func
        self.extra_student_names = {}

    def grade(self):
        good = 0
        bad = 0
        undet = 0
        self.correct = []
        for i in range(0, len(self.image.decisions)):
            if self.solutions and self.image.decisions[i] > 0:
                if self.solutions[i] == self.image.decisions[i]:
                    good += 1
                    self.correct.append(True)
                else:
                    bad += 1
                    self.correct.append(False)
            elif self.image.decisions[i] < 0:
                undet += 1
                self.correct.append(False)
            else:
                self.correct.append(False)
        blank = self.image.num_questions - good - bad - undet
        if self.score_weights is not None:
            score = float(good * self.score_weights[0] - \
                bad * self.score_weights[1] - blank * self.score_weights[2])
            max_score = float(self.image.num_questions * self.score_weights[0])
        else:
            score = None
            max_score = None
        self.score = (good, bad, blank, undet, score, max_score)

    def draw_answers(self):
#        good, bad, blank, undet = self.score
        self.image.draw_answers(self.locked, self.solutions, self.model,
                                self.correct, self.score[0], self.score[1],
                                self.score[3], self.im_id)

    def save_image(self, filename_pattern):
        filename = self._saved_image_name(filename_pattern)
        if self.save_image_function:
            self.save_image_function(filename)
        else:
            raise Exception('No save image function declared in utils.Exam')

    def save_debug_images(self, filename_pattern):
        filename = self._saved_image_name(filename_pattern)
        if self.save_image_function:
            self.save_image_function(filename + '-raw', self.image.image_raw)
            self.save_image_function(filename + '-proc', self.image.image_proc)
        else:
            raise Exception('No save image function declared in utils.Exam')

    def save_answers(self, answers_file, csv_dialect, stats = None):
        f = open(answers_file, "ab")
        writer = csv.writer(f, dialect = csv_dialect)
        data = [self.im_id,
                self.student_id,
                self.model if self.model is not None else '?',
                self.score[0],
                self.score[1],
                self.score[3],
                "/".join([str(d) for d in self.image.decisions])]
        if stats is not None and self.save_stats:
            data.extend([stats['time'],
                         stats['manual-changes'],
                         stats['num-captures'],
                         stats['num-student-id-changes'],
                         stats['id-ocr-digits-total'],
                         stats['id-ocr-digits-error'],
                         stats['id-ocr-detected']])
        writer.writerow(data)
        f.close()

    def toggle_answer(self, question, answer):
        if self.image.decisions[question] == answer:
            self.image.decisions[question] = 0
        else:
            self.image.decisions[question] = answer
        self.grade()
        self.image.clean_drawn_image()
        self.draw_answers()

    def decide_student_id(self, valid_student_ids):
        student_id = '-1'
        self.ids_rank = []
        if self.image.id is not None:
            if valid_student_ids is not None:
                ids_rank = [(self._id_rank(sid, self.image.id_scores), sid) \
                                for sid in valid_student_ids]
                self.ids_rank = sorted(ids_rank, reverse = True)
                student_id = self.ids_rank[0][1]
                self.image.id = student_id
            else:
                student_id = self.image.id
        elif valid_student_ids is not None:
            self.ids_rank = [(0.0, sid) for sid in valid_student_ids]
        return student_id

    def lock_capture(self):
        self.locked = True

    def get_student_name(self):
        if self.student_id != '-1' and self.student_names is not None and \
                self.student_id in self.student_names:
            return self.student_names[self.student_id]
        else:
            return None

    def get_student_id_and_name(self):
        if self.student_id != '-1':
            return self._student_id_and_name(self.student_id)
        else:
            return None

    def ranked_student_ids_and_names(self):
        """Returns the list of student ids and names ranked.

        Each entry is a string with student id and name. They are ranked
        according to their probability to be the actual student id. The most
        probable is the first in the list.

        """
        return [self._student_id_and_name(student_id) \
                for rank, student_id in self.ids_rank]

    def update_student_id(self, new_id, name=None):
        """Updates the student id of the current exam.

        If a student name is given and there is no name for the
        student, this name is added to the list of extra student
        names, with validity only for this exam.

        """
        if new_id is None or new_id == '-1':
            self.image.id = None
            self.student_id = '-1'
        else:
            self.image.id = new_id
            self.student_id = new_id
        if name is not None and (self.student_names is None
                                 or new_id not in self.student_names):
            self.extra_student_names[new_id] = name
        elif name is None and new_id in self.extra_student_names:
            del self.extra_student_names[new_id]

    def _student_id_and_name(self, student_id):
        if (self.student_names is not None and
            student_id in self.student_names and
            self.student_names[student_id] is not None):
            return ' '.join((student_id, self.student_names[student_id]))
        elif student_id in self.extra_student_names:
            return ' '.join((student_id, self.extra_student_names[student_id]))
        else:
            return student_id

    def _id_rank(self, student_id, scores):
        rank = 0.0
        for i in range(len(student_id)):
            rank += scores[i][int(student_id[i])]
        return rank

    def _saved_image_name(self, filename_pattern):
        if self.student_id != '-1':
            sid = self.student_id
        else:
            sid = 'noid'
        filename = regexp_seqnum.sub(str(self.im_id), filename_pattern)
        filename = regexp_id.sub(sid, filename)
        return filename

# A score is a float number or a fraction, e.g.: '0.8' or '4/5'
_re_score = re.compile(r'^\s*((\d+(\.\d+)?)|(\d+\s*\/\s*\d+))\s*$')

class ExamConfig(object):
    """Class for representing exam configuration. Once an instance has
       been created and data loaded, access directly to the attributes
       to get the data. The constructor reads data from a file. See
       doc/exam-data.sample for an example of such a file."""

    re_model = re.compile('model-[0a-zA-Z]')

    def __init__(self, filename = None):
        """Loads data from file if 'filename' is not None. Otherwise,
           default values are assigned to the attributes."""
        if filename is not None:
            self.read(filename=filename)
        else:
            self.num_questions = 0
            self.solutions = {}
            self.id_num_digits = 0
            self.dimensions = []
            self.permutations = {}
            self.models = []
            self.score_weights = None
            self.left_to_right_numbering = False
            self.survey_mode = None
            self.session = {}

    def set_solutions(self, model, solutions):
        if self.solutions is None:
            self.solutions = {}
        self.solutions[model] = solutions

    def set_permutations(self, model, permutations):
        self.permutations[model] = permutations

    def get_num_choices(self):
        """Returns the number of choices per question.

        If not all the questions have the same number of choices, or there
        are no questions, returns None.

        """
        choices = [dim[0] for dim in self.dimensions]
        if (len(choices) > 0
            and choices[0] == min(choices) and choices[0] == max(choices)):
            return choices[0]
        else:
            return None

    def read(self, filename=None, file_=None, data=None):
        """Reads exam configuration.

           Either 'filename', 'file_' or 'data' must be provided.
           'filename' specifies the name of a file to read.  'file_' is
           a file object instead of a file name.  'data' must be a
           string that contains the actual content of the config file
           to be parsed. Only one of them should not be None, although
           this restriction is not enforced: the first one not to be
           None, in the same order they are specified in the function,
           is used.

        """
        assert((filename is not None) or (file_ is not None)
               or (data is not None))
        exam_data = ConfigParser.SafeConfigParser()
        if filename is not None:
            files_read = exam_data.read([filename])
            if len(files_read) != 1:
                raise IOError('Exam config file not found: ' + filename)
        elif file_ is not None:
            exam_data.readfp(file_)
        elif data is not None:
            exam_data.readfp(io.BytesIO(data))
        try:
            self.id_num_digits = exam_data.getint('exam', 'id-num-digits')
        except:
            self.id_num_digits = 0
        self._parse_dimensions(exam_data.get('exam', 'dimensions'))
        self.num_questions = sum(dim[1] for dim in self.dimensions)
        has_solutions = exam_data.has_section('solutions')
        has_permutations = exam_data.has_section('permutations')
        self.solutions = {}
        self.permutations = {}
        self.models = []
        if has_solutions:
            for key, value in exam_data.items('solutions'):
                if not self.re_model.match(key):
                    raise Exception('Incorrect key in exam config: ' + key)
                model = key[-1].upper()
                self.models.append(model)
                self.solutions[model] = self._parse_solutions(value)
                if has_permutations:
                    key = 'permutations-' + model
                    value = exam_data.get('permutations', key)
                    self.permutations[model] = self._parse_permutations(value)
        has_correct_weight = exam_data.has_option('exam', 'correct-weight')
        has_incorrect_weight = exam_data.has_option('exam', 'incorrect-weight')
        has_blank_weight = exam_data.has_option('exam', 'blank-weight')
        if has_correct_weight and has_incorrect_weight:
            cw = self._parse_score(exam_data.get('exam', 'correct-weight'))
            iw = self._parse_score(exam_data.get('exam', 'incorrect-weight'))
            if has_blank_weight:
                bw = self._parse_score(exam_data.get('exam', 'blank-weight'))
            else:
                bw = 0.0
            self.score_weights = (cw, iw, bw)
        elif not has_correct_weight and not has_incorrect_weight:
            self.score_weights = None
        else:
            raise Exception('Exam config must contain correct and incorrect '
                            'weight or none')
        if exam_data.has_option('exam', 'left-to-right-numbering'):
            self.left_to_right_numbering = \
                       exam_data.getboolean('exam', 'left-to-right-numbering')
        else:
            self.left_to_right_numbering = False
        if exam_data.has_option('exam', 'survey-mode'):
            self.survey_mode = exam_data.getboolean('exam', 'survey-mode')
        else:
            self.survey_mode = False
        self.models.sort()
        # Load the session if it is in the file:
        self.session = {}
        if exam_data.has_section('session'):
            if exam_data.has_option('session', 'is-session'):
                self.session['is-session'] = \
                           exam_data.getboolean('session', 'is-session')
            else:
                self.session['is-session'] = False
            if exam_data.has_option('session', 'save-filename-pattern'):
                self.session['save-filename-pattern'] = \
                           exam_data.get('session', 'save-filename-pattern')
            elif self.session['is-session']:
                raise Exception(('Exam config must contain a '
                                 'save-filename-pattern entry in [session]'))

    def save(self, filename):
        data = []
        data.append('[exam]')
        data.append('dimensions: %s'%self.format_dimensions())
        data.append('id-num-digits: %d'%self.id_num_digits)
        if self.left_to_right_numbering:
            data.append('left-to-right-numbering: yes')
        if self.survey_mode:
            data.append('survey-mode: yes')
        if self.score_weights is not None:
            data.append(('correct-weight: '
                         + self._format_weight(self.score_weights[0])))
            data.append(('incorrect-weight: '
                         + self._format_weight(self.score_weights[1])))
            data.append(('blank-weight: '
                         + self._format_weight(self.score_weights[2])))
        if len(self.session) != {} and self.session['is-session']:
            data.append('')
            data.append('[session]')
            data.append('is-session: yes')
            if 'save-filename-pattern' in self.session:
                data.append('save-filename-pattern: %s'\
                            %self.session['save-filename-pattern'])
        if len(self.solutions) > 0:
            data.append('')
            data.append('[solutions]')
            for model in sorted(self.models):
                data.append('model-%s: %s'%(model,
                                            self.format_solutions(model)))
        if len(self.permutations) > 0:
            data.append('')
            data.append('[permutations]')
            for model in sorted(self.models):
                data.append('permutations-%s: %s'%(model,
                                            self.format_permutations(model)))
        data.append('')
        file_ = open(filename, 'w')
        file_.write('\n'.join(data))
        file_.close()

    def _format_weight(self, weight):
        if type(weight) == fractions.Fraction:
            if weight.denominator != 1:
                return '{0}/{1}'.format(weight.numerator, weight.denominator)
            else:
                return str(weight.numerator)
        elif type(weight) == float:
            return '{:.16f}'.format(weight)
        else:
            return str(weight)

    def format_dimensions(self):
        return ';'.join(['%d,%d'%(cols, rows) \
                             for cols, rows in self.dimensions])

    def format_solutions(self, model):
        return '/'.join([str(n) for n in self.solutions[model]])

    def format_permutations(self, model):
        return '/'.join([self._format_permutation(p) \
                             for p in self.permutations[model]])

    def _format_permutation(self, permutation):
        num_question, options = permutation
        return '%d{%s}'%(num_question, ','.join([str(n) for n in options]))

    def _parse_solutions(self, s):
        pieces = s.split('/')
        if len(pieces) != self.num_questions:
            raise Exception('Wrong number of solutions')
        return [int(num) for num in pieces]

    def _parse_dimensions(self, s):
        self.dimensions, self.num_options = parse_dimensions(s)

    def _parse_permutations(self, s):
        permutation = []
        pieces = s.split('/')
        if len(pieces) != self.num_questions:
            raise Exception('Wrong number of permutations')
        for i, piece in enumerate(pieces):
            splitted = piece.split('{')
            num_question = int(splitted[0])
            options = [int(p) for p in splitted[1][:-1].split(',')]
            if len(options) != self.num_options[i]:
                raise Exception('Wrong number of options in permutation')
            permutation.append((num_question, options))
        return permutation

    def _parse_score(self, score):
        if score.find('-') != -1:
            raise Exception('Scores in exam config must be positive'%score)
        if not _re_score.match(score):
            raise Exception('Bad score value: "{0}"'.format(score))
        parts = [p.strip() for p in score.split('/')]
        if len(parts) == 1:
            return float(parts[0])
        elif len(parts) == 2:
            return fractions.Fraction(int(parts[0]), int(parts[1]))


def parse_dimensions(text, check_equal_num_choices=False):
    dimensions = []
    num_options = []
    boxes = text.split(';')
    for box in boxes:
        dims = box.split(',')
        try:
            data = (int(dims[0]), int(dims[1]))
        except ValueError:
            raise EyegradeException('Incorrect number in exam dimensions',
                                    'bad_dimensions')
        if data[0] <= 0 or data[1] <= 0:
            raise EyegradeException('Incorrect number in exam dimensions',
                                    'bad_dimensions')
        dimensions.append(data)
        num_options.extend([data[0]] * data[1])
    if len(dimensions) == 0:
        raise EyegradeException('Dimensions are empty', 'bad_dimensions')
    if check_equal_num_choices:
        for i in range(1, len(dimensions)):
            if dimensions[i][0] != dimensions[0][0]:
                raise EyegradeException('', 'same_num_choices')
    return dimensions, num_options

def read_exam_questions(exam_filename):
    import xml.dom.minidom
    import examparser
    dom_tree = xml.dom.minidom.parse(exam_filename)
    # By now, only one parser exists. In the future multiple parser can
    # be called from here, to allow multiple data formats.
    return examparser.parse_exam(dom_tree)

class ExamQuestions(object):
    def __init__(self):
        self.questions = []
        self.subject = None
        self.degree = None
        self.date = None
        self.duration = None
        self.shuffled_questions = {}
        self.permutations = {}

    def num_questions(self):
        """Returns the number of questions of the exam."""
        return len(self.questions)

    def num_choices(self):
        """Returns the number of choices of the questions.

           If all the questions have the same number of choices, returns
           that number. If not, returns None.

        """
        num = [len(q.correct_choices) + len(q.incorrect_choices) \
                   for q in self.questions]
        for n in num[1:]:
            if num[0] != n:
                return None
        return num[0]

    def shuffle(self, model):
        """Shuffles questions and options within questions for the given model.

        """
        shuffled, permutations = shuffle(self.questions)
        self.shuffled_questions[model] = shuffled
        self.permutations[model] = permutations
        for question in self.questions:
            question.shuffle(model)

    def set_permutation(self, model, permutation):
        self.permutations[model] = [p[0] - 1 for p in permutation]
        self.shuffled_questions[model] = \
            [self.questions[i] for i in self.permutations[model]]
        for q, p in zip(self.shuffled_questions[model], permutation):
            choices = q.correct_choices + q.incorrect_choices
            q.permutations[model] = [i - 1 for i in p[1]]
            q.shuffled_choices[model] = [choices[i - 1] for i in p[1]]

    def solutions_and_permutations(self, model):
        solutions = []
        permutations = []
        for qid in self.permutations[model]:
            answers_perm = self.questions[qid].permutations[model]
            solutions.append(1 + answers_perm.index(0))
            permutations.append((qid + 1, increment_list(answers_perm)))
        return solutions, permutations

class Question(object):
    def __init__(self):
        self.text = None
        self.correct_choices = []
        self.incorrect_choices = []
        self.shuffled_choices = {}
        self.permutations = {}

    def shuffle(self, model):
        shuffled, permutations = \
            shuffle(self.correct_choices + self.incorrect_choices)
        self.shuffled_choices[model] = shuffled
        self.permutations[model] = permutations

def shuffle(data):
    """Returns a tuple (list, permutations) with data shuffled.

       Permutations is another list with the original position of each
       term. That is, shuffled[i] was in the original list in
       permutations[i] position.

    """
    to_sort = [(random.random(), item, pos) for pos, item in enumerate(data)]
    shuffled_data = []
    permutations = []
    for val, item, pos in sorted(to_sort):
        shuffled_data.append(item)
        permutations.append(pos)
    return shuffled_data, permutations

class QuestionComponent(object):
    """A piece of text and optional figure or code.

       Represents both the text of a question and its choices.

    """
    def __init__(self, in_choice):
        self.in_choice = in_choice
        self.text = None
        self.code = None
        self.figure = None
        self.annex_width = None
        self.annex_pos = None

    def check_is_valid(self):
        if self.code is not None and self.figure is not None:
            raise Exception('Code and figure cannot be in the same block')
        if (self.in_choice and self.annex_pos != 'center' and
            (self.code is not None or self.figure is not None)):
            raise Exception('Figures and code in answers must be centered')
        if (self.code is not None and self.annex_pos == 'center' and
            self.annex_width != None):
            raise Exception('Centered code cannot have width')
        if not self.in_choice and self.text is None:
            raise Exception('Questions must have a text')

def fraction_to_str(fraction):
    """Returns as a string the given fraction, simplified if possible.

    The return string can be things such as '-5/2', '2', etc.

    """
    if fraction.denominator != 1:
        return str(fraction.numerator) + '/' + str(fraction.denominator)
    else:
        return str(fraction.numerator)
