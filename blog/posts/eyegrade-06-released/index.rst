.. title: Eyegrade 0.6 released!
.. slug: eyegrade-06-released
.. date: 2015-06-20 09:13:00+00:00
.. tags: eyegrade, release
.. category:
.. link:
.. description:
.. type: text

I've just released Eyegrade 0.6.
This release includes just one main feature
that the users that don't build their exams with LaTeX
will find useful:
there is no need anymore to edit an exam configuration file
(the `.eye` file)
manually.
Now you can choose,
when you create a new grading session,
to configure the session from a configuration file
or manually through the user interface:

.. figure:: /galleries/screenshots-06/new-session-wizard-manual-1.png
   :class: thumbnail
   :alt: Choosing how to configure the exam

This feature has been developed
by `Jonathan Araneda <https://github.com/jaraneda>`_
from Chile.
In addition,
Roberto González set the requirements for this feature,
provided quite useful suggestions,
tested the new code
and sponsored Jonathan's work.
Thanks to both of them for their useful contribution!

If you choose the to configure the exam from a file,
all works like in the previous versions:
you just load the configuration file and proceed as always.
However,
if you choose to configure the exam manually,
you'll be able to enter the following data:

- The number of digits of the student id numbers.

- The number of choices per question.

- The geometry of the answer tables
  (how many tables and how many questions per table).

- The number of models of the exam
  (number of different exams you produced
  by permuting the questions and their answers).

- The key of the exam
  (the correct choice for every question in every model).

.. figure:: /galleries/screenshots-06/new-session-wizard-manual-2.png
   :class: thumbnail
   :alt: Entering configuration parameters

.. figure:: /galleries/screenshots-06/new-session-wizard-manual-3.png
   :class: thumbnail
   :alt: Editing the key of the exam

These dialogs are documented in the
`user manual
<../../doc/user-manual/index.html#manual-configuration-of-the-exam>`_.
In addition,
the configuration you entered can be exported
as a configuration file so that
you or your colleges can create new sessions with the same configuration
(see the *Tools* menu).

But wait,
what happened to the new OCR system
that `I announced for the 0.6 release
<what-will-eyegrade-06-include-part-1.html>`_?
Unfortunately, I have to leave it for later.
Although it is ready,
it depends on some other changes regarding the installation procedure
that are not yet finished.
I prefer to keep them for the next release
in order to avoid delaying the session configuration feature.
