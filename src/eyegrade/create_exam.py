# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2011 Jesus Arias Fisteus
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

from optparse import OptionParser
import sys
import locale

# Local imports
import utils
import exammaker

def read_cmd_options():
    parser = OptionParser(usage = 'usage: %prog [options] <template_filename>',
                          version = utils.program_name + ' ' + utils.version)
    parser.add_option('-o', '--output-file-prefix', dest='output_file_prefix',
                      help='store the output in the given file',
                      default=None)
    parser.add_option('-e', '--exam', dest='exam_filename', default=None,
                      help='filename of the questions for the exam')
    parser.add_option('-q', '--num-questions', type='int', dest='num_questions',
                      help='number of questions', default=None)
    parser.add_option('-c', '--num-choices', type='int', dest='num_choices',
                      help='number of choices per question', default=None)
    parser.add_option('-n', '--num-tables', type='int', dest='num_tables',
                      help='number of answer tables', default=0)
    parser.add_option('-d', '--date', dest='date', default=None,
                      help='exam date')
    parser.add_option('-s', '--subject', dest='subject', default=None,
                      help='subject name')
    parser.add_option('-g', '--degree', dest='degree', default=None,
                      help='degree name')
    parser.add_option('-m', '--models', dest='models', default='A',
                      help='concatenation of the model leters to create')
    parser.add_option('-t', '--duration', dest='duration', default=None,
                      help='exam duration time')
    parser.add_option('-l', '--title', dest='title', default=None,
                      help='title of the exam')
    parser.add_option("-k", "--dont-shuffle-again", action="store_true",
                      dest = "dont_shuffle_again", default = False,
                      help = "don't shuffle already shuffled models")
    parser.add_option('-b', '--table-dimensions', dest='dimensions',
                      default=None, help='table dimensions')
    # The -w below is maintained for compatibility; its use is deprecated
    # Use -W instead.
    parser.add_option('-w', '-W', '--table-width', type='float',
                      dest='table_width',
                      default=None, help='answer table width in cm')
    parser.add_option('-H', '--id-box-height', type='float',
                      dest='table_height', default=None,
                      help='answer table height in cm')
    parser.add_option('-x', '--id-box-width', type='float',
                      dest='id_box_width', default=None,
                      help='ID box width in cm')
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Required parameters expected')
    options.models = options.models.upper()
    # Either -e is specified, or -q and -c are used
    if not options.exam_filename:
        if (options.dimensions is None and
            (options.num_questions is None or options.num_choices is None)):
            parser.error('A file with questions must be given, or options'
                         ' -q and -c must be set, or tables dimensions'
                         ' must be set.')
    else:
        if options.num_questions or options.num_choices:
            parser.error('Option -e is mutually exclusive with -q and -c')
    return options, args

def main():
    options, args = read_cmd_options()
    template_filename = args[0]
    variables = {
        'subject': '',
        'degree': '',
        'date': '',
        'duration': '',
        'title': ''
        }
    dimensions = None
    if options.exam_filename:
        exam = utils.read_exam_questions(options.exam_filename)
        if exam.subject is not None:
            variables['subject'] = exam.subject
        if exam.degree is not None:
            variables['degree'] = exam.degree
        if exam.date is not None:
            variables['date'] = exam.date
        if exam.duration is not None:
            variables['duration'] = exam.duration
        if exam.title is not None:
            variables['title'] = exam.title
        num_questions = exam.num_questions()
        num_choices = exam.num_choices()
        if num_choices is None:
            raise Exception('All the questions in the exam must have the '
                            'same number of choices')
        for q in exam.questions:
            if len(q.correct_choices) != 1:
                raise Exception('Questions must have exactly 1 correct choice')
    else:
        exam = None
        if options.dimensions is not None:
            dimensions, num_options = utils.parse_dimensions(options.dimensions,
                                                             True)
            num_choices = dimensions[0][0]
            num_questions = sum([d[1] for d in dimensions])
            if (options.num_choices is not None and
                options.num_choices != num_choices):
                raise Exception('Incoherent number of choices')
            if (options.num_questions is not None and
                options.num_questions != num_questions):
                raise Exception('Incoherent number of questions')
            if (options.num_tables != 0 and
                len(dimensions) != options.num_tables):
                raise Exception('Incoherent number of tables')
        else:
            num_questions = options.num_questions
            num_choices = options.num_choices
            if num_questions is None or num_choices is None:
                raise Exception('Expected a number of questions and choices')

    # Command line options override options from the file
    encoding = locale.getpreferredencoding()
    if options.date is not None:
        variables['date'] = unicode(options.date, encoding)
    if options.subject is not None:
        variables['subject'] = unicode(options.subject, encoding)
    if options.degree is not None:
        variables['degree'] = unicode(options.degree, encoding)
    if options.title is not None:
        variables['title'] = unicode(options.title, encoding)
    if options.duration is not None:
        variables['duration'] = unicode(options.duration, encoding)
    if options.output_file_prefix is None:
        output_file = sys.stdout
        config_filename = None
    else:
        output_file = options.output_file_prefix + '-%s.tex'
        config_filename = options.output_file_prefix + '.eye'

    try:
        # Create and call the exam maker object
        maker = exammaker.ExamMaker(num_questions, num_choices,
                                    template_filename,
                                    output_file, variables, config_filename,
                                    options.num_tables,
                                    dimensions,
                                    options.table_width, options.table_height,
                                    options.id_box_width)
        if exam is not None:
            maker.set_exam_questions(exam)
        for model in options.models:
            maker.create_exam(model, not options.dont_shuffle_again)
        if options.output_file_prefix is not None:
            maker.output_file = options.output_file_prefix + '-%s-solutions.tex'
            for model in options.models:
                maker.create_exam(model, False, with_solution=True)
        if config_filename is not None:
            maker.save_exam_config()
    except utils.EyegradeException as ex:
        print >>sys.stderr, ex
        sys.exit(1)

    # Dump some final warnings
    for key in maker.empty_variables:
        print >>sys.stderr, 'Warning: empty \'%s\' variable'%key

if __name__ == '__main__':
    main()
