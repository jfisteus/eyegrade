from optparse import OptionParser
import sys

import utils

avail_options = ['marks']

def read_cmd_options():
    parser = OptionParser(usage = 'usage: %prog [options] command [args...]',
                          version = utils.program_name + ' ' + utils.version)
    parser.add_option('-o', '--output-file', dest = 'output_file',
                      help = 'store the output in the given file')
    parser.add_option('-i', '--ignore-missing', action='store_false',
                      dest = 'dump_missing', default = True,
                      help = 'ignore grades of students not in the '
                              'student list')
    (options, args) = parser.parse_args()
    if len(args) > 0:
        options.command = args[0]
        options.args = args[1:]
    elif len(args) == 0:
        parser.error('Command required')
    return options, parser

def mix_grades(results_filename, ids_filename, output_filename, dump_missing):
    config = utils.read_config()
    results = utils.mix_results(results_filename, ids_filename, dump_missing)
    if output_filename is not None:
        file_ = open(output_filename, 'ab')
    else:
        file_ = sys.stdout
    utils.write_grades(results, file_, config['csv-dialect'])
    if output_filename is not None:
        file_.close()
    print dump_missing

def main():
    options, parser = read_cmd_options()
    if options.command == 'mix-grades':
        if len(options.args) == 2:
            mix_grades(options.args[0], options.args[1], options.output_file,
                       options.dump_missing)
        else:
            parser.error('mix-grades expects results-file and '
                         'student list file')

if __name__ == '__main__':
    main()
