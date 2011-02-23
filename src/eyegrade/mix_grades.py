from optparse import OptionParser
import sys

import utils

def read_cmd_options():
    parser = OptionParser(usage = 'usage: %prog [options] <results_filename>'
                                  ' <ids_filename>',
                          version = utils.program_name + ' ' + utils.version)
    parser.add_option('-x', '--extra-grades', dest='extra_grades', default=None,
                      help = 'read and mix extra grades from the given file')
    parser.add_option('-o', '--output-file', dest='output_file',
                      default=None, help='store the output in the given file')
    parser.add_option('-i', '--ignore-missing', action='store_false',
                      dest = 'dump_missing', default=True,
                      help = 'ignore grades of students not in the '
                              'student list')
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error('Required parameters expected')
    return options, args

def mix_grades(results_filename, ids_filename, output_filename,
               extra_grades_filename, dump_missing):
    config = utils.read_config()
    if extra_grades_filename is None:
        results = utils.mix_results(results_filename, ids_filename,
                                    dump_missing)
    else:
        results = utils.mix_results_extra_grades(results_filename, ids_filename,
                                                 extra_grades_filename,
                                                 dump_missing)
    if output_filename is not None:
        file_ = open(output_filename, 'ab')
    else:
        file_ = sys.stdout
    utils.write_grades(results, file_, config['csv-dialect'])
    if output_filename is not None:
        file_.close()

def main():
    options, args = read_cmd_options()
    mix_grades(args[0], args[1], options.output_file, options.extra_grades,
               options.dump_missing)

if __name__ == '__main__':
    main()
