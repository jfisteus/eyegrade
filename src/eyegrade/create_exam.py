from optparse import OptionParser
import sys

import utils
import exammaker

def read_cmd_options():
    parser = OptionParser(usage = 'usage: %prog [options] <template_filename> '
                                  '<num_questions> <num_answers_per_question> '
                                  '<model>',
                          version = utils.program_name + ' ' + utils.version)
    parser.add_option('-o', '--output-file', dest='output_file',
                      help='store the output in the given file',
                      default=sys.stdout)
    parser.add_option('-n', '--num-tables', type='int', dest='num_tables',
                      help='number of answer tables', default=0)
    parser.add_option('-d', '--date', dest='date', default=None,
                      help='exam date')
    parser.add_option('-s', '--subject', dest='subject', default=None,
                      help='subject name')
    parser.add_option('-g', '--degree', dest='degree', default=None,
                      help='grade name')
    parser.add_option('-t', '--duration', dest='duration', default=None,
                      help='exam duration time')
    (options, args) = parser.parse_args()
    if len(args) != 4:
        parser.error('Required parameters expected')
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
    exammaker.create_answer_sheet(args[0], options.output_file, variables,
                                  int(args[1]), int(args[2]), args[3],
                                  options.num_tables)

if __name__ == '__main__':
    main()
