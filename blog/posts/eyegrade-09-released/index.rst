.. title: Eyegrade 0.9 released!
.. slug: eyegrade-09-released
.. date: 2022-01-16 17:35:00+01:00
.. tags: eyegrade, release
.. category:
.. link:
.. description:
.. type: text


Eyegrade 0.9 has been released!
This release includes new features for creating exams:

- Questions can be grouped,
  so that questions within a group keep their relative order.
  The group gets shuffled as a block with the rest of groups
  and questions that don't belong to any group.
  Check how to group questions
  at `the user guide <../../../doc/user-manual/#question-groups>`__.

- It's possible to define questions with several variations,
  so that variations are randomly selected for each model of the exam.
  Each variation can be defined as a whole question,
  or all the variations can be defined once
  with a dependency on some parameters.
  The values of those parameters would define the variation.
  It's also possible to assign a specific variation to a model,
  instead of letting it be randomly assigned.
  Check how to define variations
  at `the user guide <../../../doc/user-manual/#questions-with-variations>`__.

- Choices can be fixed to be always
  at the first or last position of the question.
  The rest of choices of the question get shuffled.
  Check how to fix choice positions
  at `the user guide <../../../doc/user-manual/#fixing-the-position-of-a-choice>`__.

Another new feature is the possibility to flip
the webcam image, either horizontally or vertically.
This is done from the camera selection dialog.
The reason for this feature is that a user reported
that in their system the image appeared flipped,
making it impossible to grade exams.
This features allows users to reversed that
when that happens.

As always, this version includes
bug fixes and code refactoring.

Check the
`quick start guide <../../../quick-start-guide/>`_
for instructions on how to install and try this new version,
or read the new version of the user guide at the
`documentation page <../../../documentation/>`_.

Access the binary files for this release
at the `downloads page <../../../download/>`_.
