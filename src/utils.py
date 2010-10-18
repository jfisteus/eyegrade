import ConfigParser

class ExamConfig(object):
    def __init__(self, filename = None):
        if filename is not None:
            self.read_config(filename)
        else:
            self.num_models = 0
            self.solutions = None
            self.id_num_digits = 0
            self.dimensions = []
            self.permutations = []

    def read_config(self, filename):
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
