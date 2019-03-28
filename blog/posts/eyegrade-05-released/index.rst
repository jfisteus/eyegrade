.. title: Eyegrade 0.5 released!
.. slug: eyegrade-05-released
.. date: 2015-03-23 18:39:00+00:00
.. tags: eyegrade, release
.. link:
.. description:
.. type: text

I've finally released Eyegrade 0.5.
As I've advanced in the previous four posts,
its new features are:

- It stores exam captures and updates their miniatures immediately
  when they are captured or you edit an answer or the student id
  (`blog post <what-will-eyegrade-05-include-part-1.html>`__).

- I've reworked the subsystem that manages the identity of the students.
  Optionally, students may now have separate first and last name,
  and there is a new dialog for entering new students
  when they aren't in your student lists
  (`blog post <what-will-eyegrade-05-include-part-2.html>`__,
  `explanation in the user manual
  <../../doc/user-manual/index.html#student-list-files>`__).

- Each question in a exam can have now a different weight in the final scores.
  This way, you can assign a bigger weight to the most important questions
  (`blog post <what-will-eyegrade-05-include-part-3.html>`__,
  `explanation in the user manual <../../doc/user-manual/index.html#scores>`__).

- If you don't want a question to contribute to the score of the exam,
  now you can do it when creating the session.
  For example, it is useful when you discover an error
  in the statement of a question,
  but it's too late for fixing it.
  With this feature you can avoid grading that question
  (`blog post <what-will-eyegrade-05-include-part-4.html>`__,
  `explanation in the user manual
  <../../doc/user-manual/index.html#modifying-the-student-id>`__).

If you have installed eyegrade through *git*, you can easily update
the program from versions in the series 0.2.x and later
by executing the command
*git pull* from inside the directory in which Eyegrade is installed
(`explanation in the user manual
<../../doc/user-manual/index.html#updating-eyegrade>`__).

Be aware that Eyegrade 0.5 uses an updated session database schema.
Although Eyegrade 0.5 is able to work
with sessions created by the previous versions of Eyegrade,
those previous versions don't work
with sessions created by Eyegrade 0.5.
