.. title: What will eyegrade 0.5 include? (part 1)
.. slug: what-will-eyegrade-05-include-part-1
.. date: 2014-12-28 13:46:16+00:00
.. tags: eyegrade, new-features
.. link:
.. description:
.. type: text

Apart from fixing some minor issues here and there,
I'm currently busy adding some new features to eyegrade.
Some of them are already integrated into the
`development branch at GitHub
<https://github.com/jfisteus/eyegrade/tree/development>`_.
The plan is releasing them with eyegrade 0.5 sometime in January.
I'm not sure yet which new features will make it into the release but,
starting with this post,
I'll describe some of them once they are more or less ready.

The first feature I'll talk about is actually a fix
for a counter-intuitive behavior
of the right-side view of exams
(the one I introduced in eyegrade 0.3
that shows miniatures of the exams
that have been graded in the current session).
Up to now,
the miniature was not immediately updated
when the webcam captured a new exam
or you edited something on a previously graded exam.
It was updated later, when you changed to another exam
or started to grade a new one.
That was somewhat confusing for many users.
From version 0.5 onward
the miniatures will get updated immediately
when the webcam captures a new exam or you edit an exam.
I believe that having that immediate feedback
will improve the overall user experience.

More posts will follow with the description of other
new features.
