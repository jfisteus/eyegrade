# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2015 Jesus Arias Fisteus
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
# <http://www.gnu.org/licenses/>.
#

import xml.dom.minidom as dom
import re

from . import utils

EyegradeException = utils.EyegradeException

namespace = 'http://www.it.uc3m.es/jaf/eyegrade/ns/'
text_norm_re = re.compile(r'[\ \t\n]+')

# Register user-friendly error messages
EyegradeException.register_error('exam_root_element',
    "The root element of the exam XML with the questions is expected\n"
    "to be named 'exam' in the Eyegrade namespace. Review the\n"
    "syntax of your exam and namespace declarations.\n"
    "The Eyegrade namespace is: " + namespace)
EyegradeException.register_error('exam_one_choices',
    short_message="Only one 'choices' element is allowed in a question.")
EyegradeException.register_error('bad_position_value',
    "The value of 'position' must be either 'center' or 'right'.",
    "Incorrect value for the 'position' attribute.")
EyegradeException.register_error('missing_width_code',
    "Code positioned to the right must have a 'width' attribute.",
    "Missing 'width' attribute in a 'code' element.")
EyegradeException.register_error('missing_width_fig',
    "Figures must always have a 'width' attribute.",
    "Missing 'width' attribute in a 'figure' element.")
EyegradeException.register_error('missing_text',
    "Questions must contain exactly one 'text' element.",
    "Text element expected in a question.")
EyegradeException.register_error('duplicate_text',
    "Questions must contain exactly one 'text' element.",
    "Multiple text elements in a question.")

def parse_exam(dom_tree):
    assert dom_tree.nodeType == dom.Node.DOCUMENT_NODE
    root = dom_tree.childNodes[0]
    if get_full_name(root) == (namespace, 'exam'):
        exam = utils.ExamQuestions()
        exam.subject = get_element_content(root, namespace, 'subject')
        exam.degree = get_element_content(root, namespace, 'degree')
        exam.date = get_element_content(root, namespace, 'date')
        exam.duration = get_element_content(root, namespace, 'duration')
        exam.title = get_element_content(root, namespace, 'title')
        exam.questions = []
        for node in get_children_by_tag_name(root, namespace, 'question'):
            exam.questions.append(parse_question(node))
    else:
        raise EyegradeException('Bad root element: ' + printable_name(root),
                                key='exam_root_element')
    return exam

def parse_question(question_node):
    question = utils.Question()
    question.text = parse_question_component(question_node, False)
    choices_list = get_children_by_tag_name(question_node, namespace, 'choices')
    if len(choices_list) != 1:
        raise EyegradeException('', key='exam_one_choices')
    choices = choices_list[0]
    for node in get_children_by_tag_name(choices, namespace, 'correct'):
        question.correct_choices.append(parse_question_component(node, True))
    for node in get_children_by_tag_name(choices, namespace, 'incorrect'):
        question.incorrect_choices.append(parse_question_component(node, True))
    return question

def parse_question_component(parent_node, is_choice):
    component = utils.QuestionComponent(is_choice)
    if not is_choice:
        component.text = get_question_text_content(parent_node, namespace)
    else:
        component.text = get_element_content_node(parent_node)
    component.code, code_atts = \
        get_element_content_with_attrs(parent_node, namespace, 'code',
                                       ['width', 'position'])
    component.figure, figure_atts = \
        get_element_content_with_attrs(parent_node, namespace, 'figure',
                                       ['width', 'position'])
    if component.code is not None:
        if code_atts[1] is None:
            code_atts[1] = 'center'
        elif code_atts[1] != 'center' and code_atts[1] != 'right':
            raise EyegradeException('', key='bad_position_value')
        if code_atts[0] is None and code_atts[1] == 'right':
            raise EyegradeException('', key='missing_width_code')
        if code_atts[0] is not None:
            component.annex_width = float(code_atts[0])
        else:
            component.annex_width = None
        component.annex_pos = code_atts[1]
    if component.figure is not None:
        if figure_atts[1] is None:
            figure_atts[1] = 'center'
        elif figure_atts[1] != 'center' and figure_atts[1] != 'right':
            raise EyegradeException('', key='bad_position_value')
        if figure_atts[0] is None:
            raise EyegradeException('', key='missing_width_fig')
        component.annex_width = float(figure_atts[0])
        component.annex_pos = figure_atts[1]
    component.check_is_valid()
    return component

def get_question_text_content(parent, namespace):
    parts = []
    node_list = get_children_by_tag_name(parent, namespace, 'text')
    if len(node_list) == 1:
        for node in node_list[0].childNodes:
            if node.nodeType == node.TEXT_NODE:
                parts.append(('text', node.data))
#                parts.append(('text', text_norm_re.sub(' ', node.data)))
            elif node.nodeType == node.ELEMENT_NODE:
                if (node.namespaceURI == namespace
                    and node.localName == 'code'):
                    parts.append(('code', get_text(node.childNodes, False)))
                else:
                    raise EyegradeException(
                        'Unknown element: ' + node.localName)
    elif len(node_list) == 0:
        raise EyegradeException('', key='missing_text')
    elif len(node_list) > 1:
        raise EyegradeException('', key='duplicate_text')
    return parts

def get_element_content(parent, namespace, local_name):
    node_list = get_children_by_tag_name(parent, namespace, local_name)
    if len(node_list) == 1:
        return get_text(node_list[0].childNodes)
    elif len(node_list) == 0:
        return None
    elif len(node_list) > 1:
        raise EyegradeException('Duplicate element: ' + local_name)

def get_element_content_node(element_node):
    return get_text(element_node.childNodes, False)

def get_element_content_with_attrs(parent, namespace, local_name, attr_names):
    node_list = get_children_by_tag_name(parent, namespace, local_name)
    if len(node_list) == 1:
        normalize = True if local_name != 'code' else False
        att_vals = []
        for att in attr_names:
            att_vals.append(get_attribute_text(node_list[0], att))
        return (get_text(node_list[0].childNodes, normalize), att_vals)
    elif len(node_list) == 0:
        return None, None
    elif len(node_list) > 1:
        raise EyegradeException('Duplicate element: ' + local_name)

def get_attribute_text(element, attribute_name):
    value = element.getAttributeNS(namespace, attribute_name)
    if value != '':
        return text_norm_re.sub(' ', value.strip())
    else:
        return None

def get_children_by_tag_name(parent, namespace, local_name):
    return [e for e in parent.childNodes \
                if (e.nodeType == e.ELEMENT_NODE and
                    e.localName == local_name and
                    e.namespaceURI == namespace)]

def get_text(node_list, normalize = True):
    data = []
    for node in node_list:
        if node.nodeType == node.TEXT_NODE:
            data.append(node.data)
    if len(data) > 0:
        text = ''.join(data)
        if normalize:
            return text_norm_re.sub(' ', text.strip())
        else:
            return text
    else:
        return None

def get_full_name(element):
    """Returns a tuple with (namespace, local_name) for the given element."""
    return (element.namespaceURI, element.localName)

def printable_name(element):
    """Returns a string 'namespace:local_name' for the given element."""
    return '%s:%s'%(element.namespaceURI, element.localName)
