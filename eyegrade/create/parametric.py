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

import re

from typing import Dict, List, Tuple

from .. import utils
from . import questions

_PARAM_REPLACE_RE = re.compile("{{([^{}]+)}}")

EyegradeException = utils.EyegradeException

EyegradeException.register_error(
    "undefined_parameter",
    "A parameter declaration is missing in a parametric question variation.",
)


class ParametricQuestion(questions.Question):
    """Question with variations defined through a common pattern and varying parameter sets."""

    question_pattern: questions.QuestionVariation
    parameter_sets: List["ParameterSet"]

    def __init__(self, question_pattern: questions.QuestionVariation) -> None:
        super().__init__()
        self.question_pattern = question_pattern
        self.parameter_sets = []

    def add_parameter_set(self, parameter_set: "ParameterSet"):
        self.parameter_sets.append(parameter_set)
        super().add_variation(parameter_set.apply_to(self.question_pattern))


class ParametricGroupCommonComponent(questions.GroupCommonComponent):
    """Group common component with parametric variations."""

    component_pattern: questions.QuestionComponent
    parameter_sets: List["ParameterSet"]

    def __init__(self, component_pattern: questions.QuestionComponent) -> None:
        super().__init__()
        self.component_pattern = component_pattern
        self.parameter_sets = []

    def add_parameter_set(self, parameter_set: "ParameterSet"):
        self.parameter_sets.append(parameter_set)
        super().add_variation(
            parameter_set.apply_to_question_component(self.component_pattern)
        )


class ParameterSet:
    """Container for a set of name/value parameters."""

    parameters: Dict[str, str]

    def __init__(self):
        self.parameters = {}

    def add_parameter(self, name: str, value: str) -> None:
        self.parameters[name] = value

    def apply_to(
        self, question_pattern: questions.QuestionVariation
    ) -> questions.QuestionVariation:
        text = self.apply_to_question_component(question_pattern.text)
        correct_choices = [
            self.apply_to_question_component(choice)
            for choice in question_pattern.correct_choices
        ]
        incorrect_choices = [
            self.apply_to_question_component(choice)
            for choice in question_pattern.incorrect_choices
        ]
        return questions.QuestionVariation(
            text,
            correct_choices,
            incorrect_choices,
            question_pattern.fix_first,
            question_pattern.fix_last,
        )

    def apply_to_question_component(
        self, component: questions.QuestionComponent
    ) -> questions.QuestionComponent:
        replaced = questions.QuestionComponent(component.in_choice)
        replaced.annex_width = component.annex_width
        replaced.annex_pos = component.annex_pos
        text = component.text
        if text is None:
            replaced.text = None
        elif isinstance(text, str):
            replaced.text = self._apply_to_text(text)
        else:
            replaced.text = [self._apply_to_text_part(part) for part in text]
        if component.code is not None:
            replaced.code = self._apply_to_text(component.code)
        if component.figure is not None:
            replaced.figure = self._apply_to_text(component.figure)
        return replaced

    def _apply_to_text_part(self, part: Tuple[str, str]) -> Tuple[str, str]:
        if part[0] == "text":
            return ("text", self._apply_to_text(part[1]))
        return part

    def _apply_to_text(self, text: str) -> str:
        replaced: List[str]
        parts = _PARAM_REPLACE_RE.split(text)
        # Replacement keys are at odd positions of parts
        replaced = len(parts) * [""]
        replaced[::2] = parts[::2]
        try:
            replaced[1::2] = [self.parameters[param_name] for param_name in parts[1::2]]
        except KeyError as exception:
            raise EyegradeException(
                "Parameter: {}".format(exception.args[0]), key="undefined_parameter"
            )
        return "".join(replaced)
