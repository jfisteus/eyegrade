.. title: Bugfix release 0.5.1
.. slug: bugfix-release-051
.. date: 2015-04-22 22:51:00+00:00
.. tags: bugfix, eyegrade, release
.. category:
.. link:
.. description:
.. type: text

I've released Eyegrade 0.5.1.
This version does not include any new feature,
but addresses a bug
that caused an empty spurious exam
to be stores in the session database
through the *capture exam* feature,
when used before the answer table of the current exam
were detected at least once.
Eyegrade would refuse to open this session anymore.
This release prevents the spurious exam to be stored in that case.
Additionally,
it allows Eyegrade to open the session
even when such an exam made its way into the session database.

As always, you can update with ``git pull``
if you installed Eyegrade through *git*.
