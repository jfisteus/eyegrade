from optparse import OptionParser
import sys

import utils
import exammaker

def read_cmd_options():
    parser = OptionParser(usage = 'usage: %prog [options] <template_filename> '
                                  '<num_questions> <num_answers_per_question> ',
                          version = utils.program_name + ' ' + utils.version)
    parser.add_option('-o', '--output-file-prefix', dest='output_file_prefix',
                      help='store the output in the given file',
                      default=None)
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
    (options, args) = parser.parse_args()
    if len(args) != 3:
        parser.error('Required parameters expected')
    options.models = options.models.upper()
    return options, args

def main():
    options, args = read_cmd_options()
    variables = {}
    if options.date is not None:
        variables['date'] = options.date
        variables['fecha'] = options.date
    if options.subject is not None:
        variables['subject'] = options.subject
        variables['asignatura'] = options.subject
    if options.degree is not None:
        variables['degree'] = options.degree
        variables['titulacion'] = options.degree
    if options.duration is not None:
        variables['duration'] = options.duration
        variables['duracion'] = options.duration
    if options.output_file_prefix is None:
        output_file = sys.stdout
    else:
        output_file = options.output_file_prefix + '-%s.tex'
    maker = exammaker.ExamMaker(int(args[1]), int(args[2]), args[0],
                                output_file, variables)
    for model in options.models:
        maker.create_exam(model)

if __name__ == '__main__':
    main()
