#
# Module for analysis of results
#
import csv

# Local imports
import utils

keys = ['seq-num', 'student-id', 'model', 'good', 'bad', 'unknown', 'answers']

def read_results(filename):
    csvfile = open(filename, 'rb')
    dialect = csv.Sniffer().sniff(csvfile.read(1024))
    csvfile.seek(0)
    reader = csv.DictReader(csvfile, fieldnames = keys, dialect = dialect)
    entries = [entry for entry in reader]
    csvfile.close()
    return entries

def analyze(results_filename, exam_cfg_filename):
    exam_data = utils.ExamConfig(exam_cfg_filename)
    results_raw = read_results(results_filename)

