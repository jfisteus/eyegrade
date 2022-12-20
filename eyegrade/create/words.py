# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2022 Jesus Arias Fisteus
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

import fractions
from typing import Union, Optional


class PointsWords:
    singular_word: str
    plural_word: str

    def __init__(self, word_1: str, word_2: Optional[str] = None):
        """Set the singular and plural words for "point".

        `word_1` is the singular form and `word_2` is the plural form.
        If only the first one is provided, `word_1` will be used for both.

        """
        self.singular_word = word_1
        if word_2 is not None:
            self.plural_word = word_2
        else:
            self.plural_word = word_1

    def for_score(self, score: Union[float, fractions.Fraction]):
        if score == 1:
            return self.singular_word
        else:
            return self.plural_word
