# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2021 Jesus Arias Fisteus
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
# <https://www.gnu.org/licenses/>.
#
import argparse
import sys

# Local imports
from .. import utils
from .. import scoring
from . import latex
from . import parser


EyegradeException = utils.EyegradeException

EyegradeException.register_error(
    "correct_weight_none",
    "The option '--incorrect-weight' was set. It requires\n"
    "'--correct-weight' to be also set.",
    "'--correct-weight' not set.",
)


def read_cmd_options():
    arg_parser = argparse.ArgumentParser(
        description="Create exam PDF files using the LaTeX system."
    )
    arg_parser.add_argument("template", help="LaTeX template file")
    arg_parser.add_argument(
        "--version",
        action="version",
        version="{} {}".format(utils.program_name, utils.version),
    )
    arg_parser.add_argument(
        "-o",
        "--output-file-prefix",
        dest="output_file_prefix",
        help="store the output in the given file",
        default=None,
    )
    arg_parser.add_argument(
        "-e",
        "--exam",
        dest="exam_filename",
        default=None,
        help="filename of the questions for the exam",
    )
    arg_parser.add_argument(
        "-q",
        "--num-questions",
        type=int,
        dest="num_questions",
        help="number of questions",
        default=None,
    )
    arg_parser.add_argument(
        "-c",
        "--num-choices",
        type=int,
        dest="num_choices",
        help="number of choices per question",
        default=None,
    )
    arg_parser.add_argument(
        "-n",
        "--num-tables",
        type=int,
        dest="num_tables",
        help="number of answer tables",
        default=0,
    )
    arg_parser.add_argument("-d", "--date", dest="date", default=None, help="exam date")
    arg_parser.add_argument(
        "-s", "--subject", dest="subject", default=None, help="subject name"
    )
    arg_parser.add_argument(
        "-g", "--degree", dest="degree", default=None, help="degree name"
    )
    arg_parser.add_argument(
        "-m",
        "--models",
        dest="models",
        default="A",
        help="concatenation of the model leters to create",
    )
    arg_parser.add_argument(
        "-t", "--duration", dest="duration", default=None, help="exam duration time"
    )
    arg_parser.add_argument(
        "-l", "--title", dest="title", default=None, help="title of the exam"
    )
    arg_parser.add_argument(
        "-k",
        "--dont-shuffle-again",
        action="store_true",
        dest="dont_shuffle_again",
        default=False,
        help="don't shuffle already shuffled models",
    )
    arg_parser.add_argument(
        "-b",
        "--table-dimensions",
        dest="dimensions",
        default=None,
        help="table dimensions",
    )
    arg_parser.add_argument(
        "-f",
        "--force",
        dest="force_config_overwrite",
        action="store_true",
        default=False,
        help="force removal of the previous .eye exam file",
    )
    arg_parser.add_argument(
        "--cw",
        "--correct-weight",
        dest="correct_weight",
        help="score for correct answers",
        default=None,
    )
    arg_parser.add_argument(
        "--iw",
        "--incorrect-weight",
        dest="incorrect_weight",
        help="negative score for incorrect answers",
        default=None,
    )
    arg_parser.add_argument(
        "--id-length",
        type=int,
        dest="student_id_length",
        default=None,
        help="Number of digits of student IDs (0 to disable)",
    )
    arg_parser.add_argument(
        "--id-label",
        dest="student_id_label",
        default=None,
        help="Label to show with the student ID box",
    )
    # The -w below is maintained for compatibility; its use is deprecated
    # Use -W instead.
    arg_parser.add_argument(
        "-w",
        "-W",
        "--table-width",
        type=float,
        dest="table_width",
        default=None,
        help="answer table width in cm",
    )
    arg_parser.add_argument(
        "-H",
        "--table-height",
        type=float,
        dest="table_height",
        default=None,
        help="answer table height in cm",
    )
    arg_parser.add_argument(
        "-S",
        "--table-scale",
        type=float,
        dest="table_scale",
        default=1.0,
        help="scale answer table with respect to default"
        " values > 1.0 for augmenting, < 1.0 for reducing",
    )
    arg_parser.add_argument(
        "-x",
        "--id-box-width",
        type=float,
        dest="id_box_width",
        default=None,
        help="ID box width in cm",
    )
    arg_parser.add_argument(
        "--left-to-right-numbering",
        dest="left_to_right_numbering",
        action="store_true",
        default=False,
        help=("number questions from left to right instead of " "up to bottom"),
    )
    arg_parser.add_argument(
        "--survey-mode",
        dest="survey_mode",
        action="store_true",
        default=False,
        help=("this is a survey instead of an exam"),
    )
    arg_parser.add_argument(
        "--no-pdf",
        dest="no_pdf",
        action="store_true",
        default=False,
        help=("produce the .tex files instead of PDF"),
    )
    arg_parser.add_argument(
        "--variation",
        type=int,
        dest="variation",
        help="select the same variation for all questions (set 1 for the first variation)",
        default=None,
    )
    args = arg_parser.parse_args()
    args.models = args.models.upper()
    # Either -e is specified, or -q and -c are used
    if not args.exam_filename:
        if args.dimensions is None and (
            args.num_questions is None or args.num_choices is None
        ):
            arg_parser.error(
                "A file with questions must be given, or options"
                " -q and -c must be set, or tables dimensions"
                " must be set."
            )
    else:
        if args.num_questions or args.num_choices:
            arg_parser.error("Option -e is mutually exclusive with -q and -c")
    # Check student id length 0 <= length <= 16
    if args.student_id_length is not None and (
        args.student_id_length < 0 or args.student_id_length > 16
    ):
        arg_parser.error(
            "The number of digits of student IDs must be "
            "between 0 and 16 (both included)"
        )
    # The scale factor must be greater than 0.1
    if args.table_scale < 0.1:
        arg_parser.error(
            "The scale factor must be positive and greater or equal" " to 0.1"
        )
    # Check score weights
    if args.correct_weight is not None:
        if args.incorrect_weight is None:
            args.incorrect_weight = 0
    elif args.incorrect_weight is not None:
        arg_parser.error("The score for correct answers is also needed (--cw)")
    return args


def create_exam():
    args = read_cmd_options()
    template_filename = args.template
    variables = {"subject": "", "degree": "", "date": "", "duration": "", "title": ""}
    scores = None
    dimensions = None

    # Take options from the input question files
    if args.exam_filename:
        exam = parser.parse_exam(args.exam_filename)
        if exam.subject is not None:
            variables["subject"] = exam.subject
        if exam.degree is not None:
            variables["degree"] = exam.degree
        if exam.date is not None:
            variables["date"] = exam.date
        if exam.duration is not None:
            variables["duration"] = exam.duration
        if exam.title is not None:
            variables["title"] = exam.title
        if exam.student_id_label is not None:
            variables["student_id_label"] = exam.student_id_label
        if exam.student_id_length is not None:
            variables["student_id_length"] = exam.student_id_length
        if exam.scores is not None:
            scores = exam.scores
        num_questions = exam.num_questions()
        num_choices = exam.num_choices()
        if not exam.homogeneous_num_choices():
            print(
                ("Warning: not all the questions have " "the same number of choices."),
                file=sys.stderr,
            )
        if num_choices is None:
            raise Exception(
                "All the questions in the exam must have the " "same number of choices"
            )
        for q in exam.questions:
            if q.num_correct_choices != 1:
                raise Exception("Questions must have exactly 1 correct choice")
    else:
        exam = None
        if args.dimensions is not None:
            dimensions, __ = utils.parse_dimensions(args.dimensions, True)
            num_choices = dimensions[0][0]
            num_questions = sum([d[1] for d in dimensions])
            if args.num_choices is not None and args.num_choices != num_choices:
                raise Exception("Incoherent number of choices")
            if args.num_questions is not None and args.num_questions != num_questions:
                raise Exception("Incoherent number of questions")
            if args.num_tables != 0 and len(dimensions) != args.num_tables:
                raise EyegradeException("", "incoherent_num_tables")
        else:
            num_questions = args.num_questions
            num_choices = args.num_choices
            if num_questions is None or num_choices is None:
                raise Exception("Expected a number of questions and choices")

    # Command line options override options from the file
    if args.date is not None:
        variables["date"] = args.date
    if args.subject is not None:
        variables["subject"] = args.subject
    if args.degree is not None:
        variables["degree"] = args.degree
    if args.title is not None:
        variables["title"] = args.title
    if args.duration is not None:
        variables["duration"] = args.duration
    if args.student_id_label is not None:
        variables["student_id_label"] = args.student_id_label
    if args.student_id_length is not None:
        variables["student_id_length"] = args.student_id_length
    if args.correct_weight is not None:
        scores = scoring.QuestionScores(args.correct_weight, args.incorrect_weight, 0)
    if args.output_file_prefix is None:
        output_file = sys.stdout
        config_filename = None
    else:
        config_filename = args.output_file_prefix + ".eye"
        if not args.survey_mode:
            output_file = args.output_file_prefix + "-%s.tex"
        else:
            output_file = args.output_file_prefix
    if args.variation is None:
        variation = None
    else:
        # Variations in cmd agrs begin at 1. Internally, they begin at 0.
        variation = args.variation - 1

    # Create and call the exam maker object
    maker = latex.ExamMaker(
        num_questions,
        num_choices,
        template_filename,
        output_file,
        variables,
        config_filename,
        num_tables=args.num_tables,
        dimensions=dimensions,
        table_width=args.table_width,
        table_height=args.table_height,
        table_scale=args.table_scale,
        id_box_width=args.id_box_width,
        force_config_overwrite=args.force_config_overwrite,
        scores=scores,
        left_to_right_numbering=args.left_to_right_numbering,
        survey_mode=args.survey_mode,
    )
    if not args.no_pdf and args.output_file_prefix is not None:
        if latex.check_latex():
            produce_pdf = True
        else:
            produce_pdf = False
            print("Warning: pdflatex not found in your system PATH", file=sys.stderr)
    else:
        produce_pdf = False
    if exam is not None:
        maker.set_exam_questions(exam)
    if not args.survey_mode:
        for model in args.models:
            produced_filename = maker.create_exam(
                model,
                not args.dont_shuffle_again,
                variation=variation,
                produce_pdf=produce_pdf,
            )
            if produced_filename is not None:
                print("Created file:", produced_filename, file=sys.stderr)
        if args.output_file_prefix is not None:
            maker.output_file = args.output_file_prefix + "-%s-solutions.tex"
            for model in args.models:
                produced_filename = maker.create_exam(
                    model,
                    False,
                    with_solution=True,
                    variation=variation,
                    produce_pdf=produce_pdf,
                )
                print("Created file:", produced_filename, file=sys.stderr)
    else:
        produced_filename = maker.create_exam(
            None,
            not args.dont_shuffle_again,
            variation=variation,
            produce_pdf=produce_pdf,
        )
        print("Created file:", produced_filename, file=sys.stderr)
    if config_filename is not None:
        maker.save_exam_config()

    # Dump some final warnings
    for key in maker.empty_variables:
        print("Warning: empty '%s' variable" % key, file=sys.stderr)


def main():
    try:
        create_exam()
    except utils.EyegradeException as ex:
        print(ex, file=sys.stderr)


if __name__ == "__main__":
    main()
