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
                      help='grade name')
    parser.add_option('-m', '--models', dest='models', default='A',
                      help='concatenation of the model leters to create')
    parser.add_option('-t', '--duration', dest='duration', default=None,
                      help='exam duration time')
    parser.add_option("-k", "--dont-shuffle-again", action="store_true",
                      dest = "dont_shuffle_again", default = False,
                      help = "don't shuffle already shuffled models")
    parser.add_option('-b', '--table-dimensions', dest='dimensions',
                      default=None, help='table dimensions')
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
    variables = {}
    if options.exam_filename:
        exam = utils.read_exam_questions(options.exam_filename)
        variables['subject'] = exam.subject
        variables['degree'] = exam.degree
        variables['date'] = exam.date
        variables['duration'] = exam.duration
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
    if options.duration is not None:
        variables['duration'] = unicode(options.duration, encoding)
    if options.output_file_prefix is None:
        output_file = sys.stdout
        config_filename = None
    else:
        output_file = options.output_file_prefix + '-%s.tex'
        config_filename = options.output_file_prefix + '.eye'
    maker = exammaker.ExamMaker(num_questions, num_choices, template_filename,
                                output_file, variables, config_filename,
                                options.dont_shuffle_again, options.num_tables,
                                dimensions)
    if exam is not None:
        maker.set_exam_questions(exam)
    for model in options.models:
        maker.create_exam(model)
    if config_filename is not None:
        maker.save_exam_config()

if __name__ == '__main__':
    main()
