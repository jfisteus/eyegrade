# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2024 Jesus Arias Fisteus
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

from . import compute_stats

import argparse


def print_answer_counts(answer_counts: list[list[int]]) -> None:
    for i, counts in enumerate(answer_counts):
        print(f"[Q{i + 1}] {_format_choice_counts(counts)}")


def _format_choice_counts(choice_counts: list[int]) -> str:
    not_blank = ", ".join(
        f"{chr(65 + i)}: {count}" for i, count in enumerate(choice_counts[1:])
    )
    blank = f", blank: {choice_counts[0]}"
    return not_blank + blank


def _cmd_options():
    parser = argparse.ArgumentParser(
        description="Compute statistics from a session database"
    )
    parser.add_argument(
        "session",
        type=str,
        help="Path to the session database",
    )
    return parser.parse_args()


def main():
    args = _cmd_options()
    stats = compute_stats.stats_from_session_path(args.session)
    reference_model = stats.reference_model
    if reference_model is not None:
        print_answer_counts(stats.get_answer_counts(reference_model))
    else:
        for model in stats.models:
            print(f"Model {model}")
            print_answer_counts(stats.get_answer_counts(model))


if __name__ == "__main__":
    main()
