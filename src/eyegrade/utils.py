import ConfigParser
import csv

keys = ['seq-num', 'student-id', 'model', 'good', 'bad', 'unknown', 'answers']

def read_results(filename, permutations = []):
    """Parses an eyegrade results file.

       Results are returned as a list of dictionaries with the keys
       stored in the 'keys' variable. If 'permutations' is provided,
       answers are un-shuffled.

    """
    results = __read_results_file(filename)
    for result in results:
        if result['model'].isdigit():
            result['model'] = int(result['model'])
        else:
            result['model'] = ord(result['model']) - ord('A')
        result['good'] = int(result['good'])
        result['bad'] = int(result['bad'])
        result['unknown'] = int(result['unknown'])
        answers = [int(n) for n in result['answers'].split('/')]
        if permutations != []:
            answers = __permute_answers(answers, permutations[result['model']])
        result['answers'] = answers
    return results

def __read_results_file(filename):
    csvfile = open(filename, 'rb')
    dialect = csv.Sniffer().sniff(csvfile.read(1024))
    csvfile.seek(0)
    reader = csv.DictReader(csvfile, fieldnames = keys, dialect = dialect)
    entries = [entry for entry in reader]
    csvfile.close()
    return entries

def __permute_answers(answers, permutation):
    assert(len(answers) == len(permutation))
    permutted = [0] * len(answers)
    for i, option in enumerate(answers):
        if option == 0:
            resolved_option = 0
        else:
            resolved_option = permutation[i][1][option - 1]
        permutted[permutation[i][0] - 1] = resolved_option
    return permutted

class ExamConfig(object):
    """Class for representing exam configuration. Once an instance has
       been created and data loaded, access directly to the attributes
       to get the data. The constructor reads data from a file. See
       doc/exam-data.sample for an example of such a file."""

    def __init__(self, filename = None):
        """Loads data from file if 'filename' is not None. Otherwise,
           default values are assigned to the attributes."""
        if filename is not None:
            self.read_config(filename)
        else:
            self.num_models = 0
            self.num_questions = 0
            self.solutions = None
            self.id_num_digits = 0
            self.dimensions = []
            self.permutations = []

    def read_config(self, filename):
        """Reads exam configuration from the file named 'filename'."""
        exam_data = ConfigParser.SafeConfigParser()
        exam_data.read([filename])
        try:
            self.num_models = exam_data.getint('exam', 'num-models')
        except:
            self.num_models = 1
        try:
            self.id_num_digits = exam_data.getint('exam', 'id-num-digits')
        except:
            self.id_num_digits = 0
        self.__parse_dimensions(exam_data.get('exam', 'dimensions'))
        self.num_questions = sum(dim[1] for dim in self.dimensions)
        has_permutations = exam_data.has_section('permutations')
        self.solutions = []
        self.permutations = []
        for i in range(0, self.num_models):
            key = 'model-' + chr(65 + i)
            self.__parse_solutions(exam_data.get('solutions', key))
            if has_permutations:
                key = 'permutations-' + chr(65 + i)
                self.__parse_permutations(exam_data.get('permutations', key))

    def __parse_solutions(self, s):
        pieces = s.split('/')
        if len(pieces) != self.num_questions:
            raise Exception('Wrong number of solutions')
        self.solutions.append([int(num) for num in pieces])

    def __parse_dimensions(self, s):
        self.dimensions = []
        self.num_options = []
        boxes = s.split(';')
        for box in boxes:
            dims = box.split(',')
            self.dimensions.append((int(dims[0]), int(dims[1])))
            self.num_options.extend([int(dims[0])] * int(dims[1]))

    def __parse_permutations(self, s):
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
        self.permutations.append(permutation)
