.. title: What will eyegrade 0.5 include? (part 4)
.. slug: what-will-eyegrade-05-include-part-4
.. date: 2015-02-26 08:50:00+00:00
.. tags: eyegrade, new-features
.. link:
.. description:
.. type: text

I'm holding release 0.5 more than expected
because I plan to add a couple of features more.
Today I'll talk about one of them.
Roberto González, a long time user and contributor of Eyegrade,
wondered in
`his comment to my previous blog post
<what-will-eyegrade-05-include-part-3.html#disqus_thread>`_
whether the new feature for assigning different scores to questions
could be used to void those questions that one doesn't want to grade.
This may be useful, for example,
when, being late for doing changes to the text of the exam,
you want to invalidate a question
because you discover that there is a severe error in how it's stated.
Roberto commented another situation
in which voiding a question would be very useful for him.

Roberto cleverly suggested that assigning weight zero
to those questions would make it.
I've been working on his idea.
When you set the scores of the questions
and select the *base score plus per-question weight* option,
you'll be able to assign weight zero to some questions:

.. figure:: /galleries/screenshots-05/void-question-set-weight.png
   :class: thumbnail
   :alt: Set weight zero to void a question

The example above voids question 5 in model A,
which is also question 1 in model B, question 2 in model C
and question 3 in model D.
Void questions will be clearly displayed
in the capture of the exam,
and won't be considered either for the score
or the count of correct and incorrect questions:

.. figure:: /galleries/screenshots-05/void-question-capture.png
   :class: thumbnail
   :alt: Set weight zero to void a question

This new feature has a limitation though:
you'll have to void the questions when you create the session.
You won't be able to do it once the session has been created.
For future releases
I'll try to allow changing question scores for existing sessions,
so that the scores of the exams that have already been graded
get computed again and their captures get updated.
