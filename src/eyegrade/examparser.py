# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2011 Jesus Arias Fisteus
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

import utils

namespace = 'http://www.it.uc3m.es/jaf/eyegrade/ns/'
text_norm_re = re.compile(r'[\ \t\n]+')

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
        raise Exception('Error: root element expected to be "exam"')
    return exam

def parse_question(question_node):
    question = utils.Question()
    question.text = parse_question_component(question_node, False)
    choices_list = get_children_by_tag_name(question_node, namespace, 'choices')
    if len(choices_list) != 1:
        raise Exception('Expected exacly one choices element')
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
            raise Exception('Incorrect value for attribute "position"')
        if code_atts[0] is None and code_atts[1] == 'right':
            raise Exception('Attribute "width" is mandatory for code '
                            'positioned at the right')
        if code_atts[0] is not None:
            component.annex_width = float(code_atts[0])
        else:
            component.annex_width = None
        component.annex_pos = code_atts[1]
    if component.figure is not None:
        if figure_atts[1] is None:
            figure_atts[1] = 'center'
        elif figure_atts[1] != 'center' and figure_atts[1] != 'right':
            raise Exception('Incorrect value for attribute "position"')
        if figure_atts[0] is None:
            raise Exception('Attribute "width" is mandatory for figures')
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
                    raise Exception('Unknown element: ' + node.localName)
    elif len(node_list) == 0:
        raise Exception('Text element expected in question')
    elif len(node_list) > 1:
        raise Exception('Duplicate text element')
    return parts

def get_element_content(parent, namespace, local_name):
    node_list = get_children_by_tag_name(parent, namespace, local_name)
    if len(node_list) == 1:
        return get_text(node_list[0].childNodes)
    elif len(node_list) == 0:
        return None
    elif len(node_list) > 1:
        raise Exception('Duplicate element: ' + local_name)

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
        raise Exception('Duplicate element: ' + local_name)

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
    return (element.namespaceURI, element.localName)
