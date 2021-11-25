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

import xml.dom.minidom
import re

from typing import List, Iterable, Optional, Tuple, Union, TYPE_CHECKING

from .. import utils
from .. import scoring
from . import questions
from . import parametric

if TYPE_CHECKING:
    import xml.dom


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
    "Questions must contain exactly one 'text' element, and groups one 'common' element.",
    "Multiple text elements in a question or common elements in a group.",
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
EyegradeException.register_error(
    "incompatible_variation",
    "Variations of the same question must contain "
    "the same number of correct and incorrect choices. "
    "Fixed choices must appear at the same positions.",
)
EyegradeException.register_error(
    "incompatible_variation_num_group",
    "Questions within the same group must contain the same number of variations.",
)
EyegradeException.register_error(
    "incompatible_variations_declarations",
    "Incompatible elements within the same question: <variation> and <variation_params>",
)
EyegradeException.register_error(
    "multiple_variation_params",
    "At most one <variation_params> element per question is allowed",
)
EyegradeException.register_error(
    "missing_param_name", "Missing 'eye:name' attribute in <param> element"
)
EyegradeException.register_error("bad_fix_value", "Bad value for eye:fix attribute")


def parse_exam(exam_filename: str) -> questions.ExamQuestions:
    """ Parses the questions of a exam from an XML file."""
    dom_tree = xml.dom.minidom.parse(exam_filename)
    # By now, only one parser exists. In the future multiple parsers can
    # be called from here, to allow multiple data formats.
    return _parse_tree(dom_tree)


def _parse_tree(dom_tree: xml.dom.minidom.Element) -> questions.ExamQuestions:
    assert dom_tree.nodeType == xml.dom.minidom.Node.DOCUMENT_NODE
    root = dom_tree.childNodes[0]
    if get_full_name(root) == (EYEGRADE_NAMESPACE, "exam"):
        exam = questions.ExamQuestions()
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


def parse_student_id(
    root: xml.dom.minidom.Element,
) -> Tuple[Optional[int], Optional[str]]:
    student_id_length = None
    student_id_label = None
    element_list = get_children_by_tag_name(root, EYEGRADE_NAMESPACE, "studentId")
    if len(element_list) == 1:
        student_id_element = element_list[0]
        student_id_length_str = get_attribute_text(student_id_element, "length")
        student_id_label = get_attribute_text(student_id_element, "label")
        if student_id_length_str is not None:
            try:
                student_id_length = int(student_id_length_str)
            except ValueError:
                raise EyegradeException("", key="student_id_number_format")
    elif len(element_list) > 1:
        raise EyegradeException("", key="duplicate_studentid_element")
    return student_id_length, student_id_label


def parse_scores(
    root: xml.dom.minidom.Element,
) -> Optional[Union[scoring.AutomaticScore, scoring.QuestionScores]]:
    scores: Optional[Union[scoring.AutomaticScore, scoring.QuestionScores]] = None
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
                incorrect_attr = "0"
            scores = scoring.QuestionScores(correct_attr, incorrect_attr, "0")
        elif incorrect_attr is not None:
            raise EyegradeException("", key="score_correct_needed")
        else:
            raise EyegradeException("", key="empty_score_element")
    elif len(element_list) > 1:
        raise EyegradeException("", key="duplicate_score_element")
    return scores


def parse_question(question_node: xml.dom.minidom.Element) -> questions.Question:
    question: questions.Question
    variation_nodes = get_children_by_tag_name(
        question_node, EYEGRADE_NAMESPACE, "variation"
    )
    parameter_sets = parse_parameter_sets(question_node)
    if variation_nodes and parameter_sets:
        raise EyegradeException("", key="incompatible_variations_declarations")
    if variation_nodes:
        question = questions.Question()
        for node in variation_nodes:
            question.add_variation(parse_question_variation(node))
    elif parameter_sets:
        question = parse_parametric_question(question_node, parameter_sets)
    else:
        question = questions.FixedQuestion(parse_question_variation(question_node))
    return question


def parse_question_variation(
    variation_node: xml.dom.minidom.Element,
) -> questions.QuestionVariation:
    text = parse_question_component(variation_node, False)
    choices_list = get_children_by_tag_name(
        variation_node, EYEGRADE_NAMESPACE, "choices"
    )
    if len(choices_list) != 1:
        raise EyegradeException("", key="exam_one_choices")
    choices = choices_list[0]
    correct_choices = []
    incorrect_choices = []
    fix_first: List[int] = []
    fix_last: List[int] = []
    counter = 0
    for node in get_children_by_tag_name(choices, EYEGRADE_NAMESPACE, "correct"):
        correct_choices.append(parse_question_component(node, True))
        read_fix_attr(node, fix_first, fix_last, counter)
        counter += 1
    for node in get_children_by_tag_name(choices, EYEGRADE_NAMESPACE, "incorrect"):
        incorrect_choices.append(parse_question_component(node, True))
        read_fix_attr(node, fix_first, fix_last, counter)
        counter += 1
    return questions.QuestionVariation(
        text, correct_choices, incorrect_choices, fix_first, fix_last
    )


def read_fix_attr(
    node: xml.dom.minidom.Element, fix_first: List[int], fix_last: List[int], index: int
) -> None:
    value = get_attribute_text(node, "fix")
    if not value:
        pass
    elif value == "first":
        fix_first.append(index)
    elif value == "last":
        fix_last.append(index)
    else:
        raise EyegradeException(
            f"Got '{value}' but expected 'first' or 'last'", key="bad_fix_value"
        )


def parse_parametric_question(
    node: xml.dom.minidom.Element, parameter_sets: List[parametric.ParameterSet]
) -> parametric.ParametricQuestion:
    question = parametric.ParametricQuestion(parse_question_variation(node))
    for parameter_set in parameter_sets:
        question.add_parameter_set(parameter_set)
    return question


def parse_parameter_sets(
    parent: xml.dom.minidom.Element,
) -> List[parametric.ParameterSet]:
    variation_params_nodes = get_children_by_tag_name(
        parent, EYEGRADE_NAMESPACE, "variation_params"
    )
    if variation_params_nodes:
        if len(variation_params_nodes) > 1:
            raise EyegradeException("", key="multiple_variation_params")
        return parse_variation_params_node(variation_params_nodes[0])
    return []


def parse_group(group_node: xml.dom.minidom.Element) -> questions.QuestionsGroup:
    question_list: List[questions.Question] = []
    common_text: Optional[questions.GroupCommonComponent]
    parameter_sets = parse_parameter_sets(group_node)
    common_text = _parse_group_common(group_node, parameter_sets)
    for node in get_children_by_tag_name(group_node, EYEGRADE_NAMESPACE, "question"):
        if not parameter_sets:
            question = parse_question(node)
        else:
            question = parse_parametric_question(node, parameter_sets)
        question_list.append(question)
    return questions.QuestionsGroup(question_list, common_text=common_text)


def _parse_group_common(
    group_node: xml.dom.minidom.Element, parameter_sets: List[parametric.ParameterSet]
) -> Optional[questions.GroupCommonComponent]:
    common_text: Optional[questions.GroupCommonComponent]
    element_list = get_children_by_tag_name(group_node, EYEGRADE_NAMESPACE, "common")
    if len(element_list) == 1:
        common_node = element_list[0]
        variation_nodes = get_children_by_tag_name(
            common_node, EYEGRADE_NAMESPACE, "variation"
        )
        if variation_nodes and parameter_sets:
            raise EyegradeException("", key="incompatible_variations_declarations")
        if variation_nodes:
            common_text = questions.GroupCommonComponent()
            for node in variation_nodes:
                common_text.add_variation(parse_question_component(node, False))
        elif parameter_sets:
            common_text = parametric.ParametricGroupCommonComponent(
                parse_question_component(common_node, False)
            )
            for parameter_set in parameter_sets:
                common_text.add_parameter_set(parameter_set)
        else:
            common_text = questions.FixedGroupCommonComponent(
                parse_question_component(common_node, False)
            )
    elif not element_list:
        common_text = None
    elif len(element_list) > 1:
        raise EyegradeException("", key="duplicate_text")
    return common_text


def parse_question_component(
    parent_node: xml.dom.minidom.Element, is_choice: bool
) -> questions.QuestionComponent:
    component = questions.QuestionComponent(is_choice)
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


def parse_variation_params_node(
    node: xml.dom.minidom.Element,
) -> List[parametric.ParameterSet]:
    parameter_sets = []
    for variation_node in get_children_by_tag_name(
        node, EYEGRADE_NAMESPACE, "variation"
    ):
        parameter_sets.append(parse_parameter_set(variation_node))
    return parameter_sets


def parse_parameter_set(node: xml.dom.minidom.Element) -> parametric.ParameterSet:
    parameter_set = parametric.ParameterSet()
    for parameter_node in get_children_by_tag_name(node, EYEGRADE_NAMESPACE, "param"):
        name = get_attribute_text(parameter_node, "name")
        if name is None:
            raise EyegradeException("", key="missing_param_name")
        value = get_element_content_node(parameter_node)
        if value is None:
            value = ""
        parameter_set.add_parameter(name, value)
    return parameter_set


def get_question_text_content(
    parent: xml.dom.minidom.Element, namespace: str
) -> List[Tuple[str, str]]:
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
    elif not node_list:
        raise EyegradeException("", key="missing_text")
    else:
        raise EyegradeException("", key="duplicate_text")
    return parts


def get_element_content(
    parent: xml.dom.minidom.Element, namespace: str, local_name: str
) -> Optional[str]:
    content: Optional[str]
    node_list = get_children_by_tag_name(parent, namespace, local_name)
    if not node_list:
        content = None
    elif len(node_list) == 1:
        content = get_text(node_list[0].childNodes)
    else:
        raise EyegradeException("Duplicate element: " + local_name)
    return content


def get_element_content_node(element_node: xml.dom.minidom.Element) -> Optional[str]:
    return get_text(element_node.childNodes, False)


def get_element_content_with_attrs(
    parent: xml.dom.minidom.Element,
    namespace: str,
    local_name: str,
    attr_names: Iterable[str],
) -> Tuple[Optional[str], List[Optional[str]]]:
    content: Optional[str]
    att_vals: List[Optional[str]]
    node_list = get_children_by_tag_name(parent, namespace, local_name)
    if not node_list:
        content = None
        att_vals = []
    elif len(node_list) == 1:
        content = get_text(node_list[0].childNodes, local_name != "code")
        att_vals = []
        for att in attr_names:
            att_vals.append(get_attribute_text(node_list[0], att))
    elif len(node_list) > 1:
        raise EyegradeException("Duplicate element: " + local_name)
    return content, att_vals


def get_attribute_text(
    element: xml.dom.minidom.Element, attribute_name: str
) -> Optional[str]:
    value = element.getAttributeNS(EYEGRADE_NAMESPACE, attribute_name)
    if value != "":
        return text_norm_re.sub(" ", value.strip())
    return None


def get_children_by_tag_name(
    parent: xml.dom.minidom.Element, namespace: str, local_name: str
) -> List[xml.dom.minidom.Element]:
    return get_children_by_tag_names(parent, namespace, [local_name])


def get_children_by_tag_names(
    parent: xml.dom.minidom.Element, namespace: str, local_names: Iterable[str]
) -> List[xml.dom.minidom.Element]:
    return [
        e
        for e in parent.childNodes
        if (
            e.nodeType == e.ELEMENT_NODE
            and e.localName in local_names
            and e.namespaceURI == namespace
        )
    ]


def get_text(
    node_list: xml.dom.minicompat.NodeList, normalize: bool = True
) -> Optional[str]:
    data = []
    for node in node_list:
        if node.nodeType == node.TEXT_NODE:
            data.append(node.data)
    if data:
        text = "".join(data)
        if normalize:
            return text_norm_re.sub(" ", text.strip())
        return text
    return None


def get_full_name(element: xml.dom.minidom.Element) -> Tuple[str, str]:
    """Returns a tuple with (namespace, local_name) for the given element."""
    return (element.namespaceURI, element.localName)


def printable_name(element: xml.dom.minidom.Element) -> str:
    """Returns a string 'namespace:local_name' for the given element."""
    return "{}:{}".format(element.namespaceURI, element.localName)
