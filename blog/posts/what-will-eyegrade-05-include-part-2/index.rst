.. title: What will eyegrade 0.5 include? (part 2)
.. slug: what-will-eyegrade-05-include-part-2
.. date: 2014-12-29 16:54:15+00:00
.. tags: eyegrade, new-features
.. link:
.. description:
.. type: text

This post describes another feature that will be available
in eyegrade 0.5 (see `the first installment of this series of posts
<what-will-eyegrade-05-include-part-1.html>`_).

I've largely reworked the code that handles the student lists.
In eyegrade 0.5 you'll see two visible changes regarding this.
Firstly, you'll be able to specify the first and last name of
students in two separate fields.
Secondly, there is a new dialog for entering,
while grading an exam,
new students.

Separating first and last name will be optional.
Eyegrade will infer, from the student lists it imports,
whether you are providing separate first and last name fields,
or the whole name together in just one field.
When exporting grades, you'll have control
over which name fields get exported and will be able
to sort the listing by last name if you wish so.

Regarding the second change,
there will be a new button
in the dialog for editing the student id
that lets you open a dialog for entering the data
for a student that is not in your student lists:

.. figure:: /galleries/screenshots-05/change-id-preview.png
   :class: thumbnail
   :alt: Screenshot of the new version of the student id edit dialog

The dialog asks for the numerical id, first name, last name and email.
Only the numerical id is mandatory.
This is the current look of the dialog,
although it might change before the release:

.. figure:: /galleries/screenshots-05/new-student-preview.png
   :class: thumbnail
   :alt: Screenshot of the new dialog for adding a new student
