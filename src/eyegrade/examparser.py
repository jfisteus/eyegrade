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
        exam.questions = []
        for node in root.getElementsByTagNameNS(namespace, 'question'):
            exam.questions.append(parse_question(node))
    else:
        raise Exception('Error: root element expected to be "exam"')
    return exam

def parse_question(question_node):
    question = utils.Question()
    question.text = get_element_content(question_node, namespace, 'text')
    question.code, question.code_width = \
        get_element_content_with_attr(question_node, namespace, 'code', 'width')
    question.figure, question.figure_width = \
        get_element_content_with_attr(question_node, namespace,
                                      'figure', 'width')
    choices_list = question_node.getElementsByTagNameNS(namespace, 'choices')
    if len(choices_list) != 1:
        raise Exception('Expected exacly one choices element')
    choices = choices_list[0]
    for node in choices.getElementsByTagNameNS(namespace, 'correct'):
        question.correct_choices.append(get_element_content_node(node))
    for node in choices.getElementsByTagNameNS(namespace, 'incorrect'):
        question.incorrect_choices.append(get_element_content_node(node))
    return question

def get_element_content(parent, namespace, local_name):
    node_list = parent.getElementsByTagNameNS(namespace, local_name)
    if len(node_list) == 1:
        return get_text(node_list[0].childNodes)
    elif len(node_list) == 0:
        return None
    elif len(node_list) > 1:
        raise Exception('Duplicate element: ' + local_name)

def get_element_content_node(element_node):
    return get_text(element_node.childNodes)

def get_element_content_with_attr(parent, namespace, local_name, attr_name):
    node_list = parent.getElementsByTagNameNS(namespace, local_name)
    if len(node_list) == 1:
        return get_text(node_list[0]), get_attribute_text(node_list[0], 'width')
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

def get_text(node_list):
    data = []
    for node in node_list:
        if node.nodeType == node.TEXT_NODE:
            data.append(node.data)
    if len(data) > 0:
        text = ''.join(data)
        return text_norm_re.sub(' ', text.strip())
    else:
        return None

def get_full_name(element):
    return (element.namespaceURI, element.localName)
