# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2018 Jesus Arias Fisteus
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

import xml.dom.minidom as dom
import re

from . import utils
from . import exams
from . import scoring


EyegradeException = utils.EyegradeException

EYEGRADE_NAMESPACE = "http://www.it.uc3m.es/jaf/eyegrade/ns/"
text_norm_re = re.compile(r"[\ \t\n]+")

# Register user-friendly error messages
EyegradeException.register_error(
    "exam_root_element",
    "The root element of the exam XML with the questions is expected\n"
    "to be named 'exam' in the Eyegrade namespace. Review the\n"
    "syntax of your exam and namespace declarations.\n"
    "The Eyegrade namespace is: " + EYEGRADE_NAMESPACE,
)
EyegradeException.register_error(
    "exam_one_choices",
    short_message="Only one 'choices' element is allowed in a question.",
)
EyegradeException.register_error(
    "bad_position_value",
    "The value of 'position' must be either 'center' or 'right'.",
    "Incorrect value for the 'position' attribute.",
)
EyegradeException.register_error(
    "missing_width_code",
    "Code positioned to the right must have a 'width' attribute.",
    "Missing 'width' attribute in a 'code' element.",
)
EyegradeException.register_error(
    "missing_width_fig",
    "Figures must always have a 'width' attribute.",
    "Missing 'width' attribute in a 'figure' element.",
)
EyegradeException.register_error(
    "missing_text",
    "Questions must contain exactly one 'text' element.",
    "Text element expected in a question.",
)
EyegradeException.register_error(
    "duplicate_text",
    "Questions must contain exactly one 'text' element.",
    "Multiple text elements in a question.",
)
EyegradeException.register_error(
    "score_correct_needed",
    "When a score for incorrect answers is provided, "
    "a score for correct answers is also needed.",
)
EyegradeException.register_error(
    "duplicate_studentid_element", "At most one studentId element can be provided."
)
EyegradeException.register_error(
    "studentid_number_format", "Student id length must be an integer"
)
EyegradeException.register_error(
    "duplicate_score_element", "At most one score element can be provided."
)
EyegradeException.register_error(
    "empty_score_element",
    "The score element must specify either a maximum score "
    "or a score for correct answers.",
)
EyegradeException.register_error(
    "incorrect_score_element",
    "The score element must specify either a maximum score "
    "or scores for correct and incorrect answers, but not both.",
)
EyegradeException.register_error(
    "penalize_attribute",
    "The value of the penalize attribute must be either 'true' or 'false'.",
)


def parse_exam(dom_tree):
    assert dom_tree.nodeType == dom.Node.DOCUMENT_NODE
    root = dom_tree.childNodes[0]
    if get_full_name(root) == (EYEGRADE_NAMESPACE, "exam"):
        exam = exams.ExamQuestions()
        exam.subject = get_element_content(root, EYEGRADE_NAMESPACE, "subject")
        exam.degree = get_element_content(root, EYEGRADE_NAMESPACE, "degree")
        exam.date = get_element_content(root, EYEGRADE_NAMESPACE, "date")
        exam.duration = get_element_content(root, EYEGRADE_NAMESPACE, "duration")
        exam.title = get_element_content(root, EYEGRADE_NAMESPACE, "title")
        student_id_length, student_id_label = parse_student_id(root)
        if student_id_length is not None:
            exam.student_id_length = student_id_length
        if student_id_label is not None:
            exam.student_id_label = student_id_label
        for node in get_children_by_tag_names(
            root, EYEGRADE_NAMESPACE, ["question", "group"]
        ):
            if node.localName == "question":
                exam.questions.append(parse_question(node))
            else:
                exam.questions.append(parse_group(node))
        scores = parse_scores(root)
        if isinstance(scores, scoring.AutomaticScore):
            exam.scores = scores.compute(exam.num_questions(), exam.num_choices())
        else:
            exam.scores = scores
    else:
        raise EyegradeException(
            "Bad root element: " + printable_name(root), key="exam_root_element"
        )
    return exam


def parse_student_id(root):
    student_id_length = None
    student_id_label = None
    element_list = get_children_by_tag_name(root, EYEGRADE_NAMESPACE, "studentId")
    if len(element_list) == 1:
        student_id_element = element_list[0]
        student_id_length = get_attribute_text(student_id_element, "length")
        student_id_label = get_attribute_text(student_id_element, "label")
        try:
            student_id_length = int(student_id_length)
        except ValueError:
            raise EyegradeException("", key="student_id_number_format")
    elif len(element_list) > 1:
        raise EyegradeException("", key="duplicate_studentid_element")
    return student_id_length, student_id_label


def parse_scores(root):
    scores = None
    element_list = get_children_by_tag_name(root, EYEGRADE_NAMESPACE, "scores")
    if len(element_list) == 1:
        score_element = element_list[0]
        max_score_attr = get_attribute_text(score_element, "maxScore")
        penalize_attr = get_attribute_text(score_element, "penalize")
        correct_attr = get_attribute_text(score_element, "correct")
        incorrect_attr = get_attribute_text(score_element, "incorrect")
        if max_score_attr is not None:
            # Automatically compute scores from the maximum score
            if correct_attr is not None or incorrect_attr is not None:
                raise EyegradeException("", key="incorrect_score_element")
            if penalize_attr == "true":
                penalize = True
            elif penalize_attr is None or penalize_attr == "false":
                penalize = False
            else:
                raise EyegradeException("", key="penalize_attribute")
            scores = scoring.AutomaticScore(max_score_attr, penalize)
        elif correct_attr is not None:
            if incorrect_attr is None:
                incorrect_attr = 0
            scores = scoring.QuestionScores(correct_attr, incorrect_attr, 0)
        elif incorrect_attr is not None:
            raise EyegradeException("", key="score_correct_needed")
        else:
            raise EyegradeException("", key="empty_score_element")
    elif len(element_list) > 1:
        raise EyegradeException("", key="duplicate_score_element")
    return scores


def parse_question(question_node):
    question = exams.Question()
    question.text = parse_question_component(question_node, False)
    choices_list = get_children_by_tag_name(
        question_node, EYEGRADE_NAMESPACE, "choices"
    )
    if len(choices_list) != 1:
        raise EyegradeException("", key="exam_one_choices")
    choices = choices_list[0]
    for node in get_children_by_tag_name(choices, EYEGRADE_NAMESPACE, "correct"):
        question.correct_choices.append(parse_question_component(node, True))
    for node in get_children_by_tag_name(choices, EYEGRADE_NAMESPACE, "incorrect"):
        question.incorrect_choices.append(parse_question_component(node, True))
    return question


def parse_group(group_node):
    questions = []
    for node in get_children_by_tag_name(group_node, EYEGRADE_NAMESPACE, "question"):
        questions.append(parse_question(node))
    return exams.QuestionsGroup(questions)


def parse_question_component(parent_node, is_choice):
    component = exams.QuestionComponent(is_choice)
    if not is_choice:
        component.text = get_question_text_content(parent_node, EYEGRADE_NAMESPACE)
    else:
        component.text = get_element_content_node(parent_node)
    component.code, code_atts = get_element_content_with_attrs(
        parent_node, EYEGRADE_NAMESPACE, "code", ["width", "position"]
    )
    component.figure, figure_atts = get_element_content_with_attrs(
        parent_node, EYEGRADE_NAMESPACE, "figure", ["width", "position"]
    )
    if component.code is not None:
        if code_atts[1] is None:
            code_atts[1] = "center"
        elif code_atts[1] != "center" and code_atts[1] != "right":
            raise EyegradeException("", key="bad_position_value")
        if code_atts[0] is None and code_atts[1] == "right":
            raise EyegradeException("", key="missing_width_code")
        if code_atts[0] is not None:
            component.annex_width = float(code_atts[0])
        else:
            component.annex_width = None
        component.annex_pos = code_atts[1]
    if component.figure is not None:
        if figure_atts[1] is None:
            figure_atts[1] = "center"
        elif figure_atts[1] != "center" and figure_atts[1] != "right":
            raise EyegradeException("", key="bad_position_value")
        if figure_atts[0] is None:
            raise EyegradeException("", key="missing_width_fig")
        component.annex_width = float(figure_atts[0])
        component.annex_pos = figure_atts[1]
    component.check_is_valid()
    return component


def get_question_text_content(parent, namespace):
    parts = []
    node_list = get_children_by_tag_name(parent, namespace, "text")
    if len(node_list) == 1:
        for node in node_list[0].childNodes:
            if node.nodeType == node.TEXT_NODE:
                parts.append(("text", node.data))
            #                parts.append(('text', text_norm_re.sub(' ', node.data)))
            elif node.nodeType == node.ELEMENT_NODE:
                if node.namespaceURI == namespace and node.localName == "code":
                    parts.append(("code", get_text(node.childNodes, False)))
                else:
                    raise EyegradeException("Unknown element: " + node.localName)
    elif len(node_list) == 0:
        raise EyegradeException("", key="missing_text")
    elif len(node_list) > 1:
        raise EyegradeException("", key="duplicate_text")
    return parts


def get_element_content(parent, namespace, local_name):
    node_list = get_children_by_tag_name(parent, namespace, local_name)
    if len(node_list) == 1:
        return get_text(node_list[0].childNodes)
    elif len(node_list) == 0:
        return None
    elif len(node_list) > 1:
        raise EyegradeException("Duplicate element: " + local_name)


def get_element_content_node(element_node):
    return get_text(element_node.childNodes, False)


def get_element_content_with_attrs(parent, namespace, local_name, attr_names):
    node_list = get_children_by_tag_name(parent, namespace, local_name)
    if len(node_list) == 1:
        normalize = True if local_name != "code" else False
        att_vals = []
        for att in attr_names:
            att_vals.append(get_attribute_text(node_list[0], att))
        return (get_text(node_list[0].childNodes, normalize), att_vals)
    elif len(node_list) == 0:
        return None, None
    elif len(node_list) > 1:
        raise EyegradeException("Duplicate element: " + local_name)


def get_attribute_text(element, attribute_name):
    value = element.getAttributeNS(EYEGRADE_NAMESPACE, attribute_name)
    if value != "":
        return text_norm_re.sub(" ", value.strip())
    else:
        return None


def get_children_by_tag_name(parent, namespace, local_name):
    return get_children_by_tag_names(parent, namespace, [local_name])


def get_children_by_tag_names(parent, namespace, local_names):
    return [
        e
        for e in parent.childNodes
        if (
            e.nodeType == e.ELEMENT_NODE
            and e.localName in local_names
            and e.namespaceURI == namespace
        )
    ]


def get_text(node_list, normalize=True):
    data = []
    for node in node_list:
        if node.nodeType == node.TEXT_NODE:
            data.append(node.data)
    if len(data) > 0:
        text = "".join(data)
        if normalize:
            return text_norm_re.sub(" ", text.strip())
        else:
            return text
    else:
        return None


def get_full_name(element):
    """Returns a tuple with (namespace, local_name) for the given element."""
    return (element.namespaceURI, element.localName)


def printable_name(element):
    """Returns a string 'namespace:local_name' for the given element."""
    return "%s:%s" % (element.namespaceURI, element.localName)
