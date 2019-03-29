[Eyegrade](https://www.eyegrade.org/)
uses a webcam to grade multiple choice question (MCQ) exams.
Needing just a cheap low-end webcam, it aims to be a low-cost
and portable solution available to everyone, on the contrary to other
solutions based on scanners.

The main features of Eyegrade are:

- Grading exams:
Using a webcam, the graphical user interface of
Eyegrade allows you to scan and grade your students' exams.
Eyegrade is able to recognize not only the answers to the questions,
but also the identity of the student
by using its hand-written digit recognition module.
The whole process is supervised by you so that you can detect
and fix any potential error of the image recognition system.

- Exporting grades:
Grades can be exported in
[Office Open XML](https://en.wikipedia.org/wiki/Office_Open_XML) format
(.XLSX files that can be read from Microsoft Excel
LibreOffice, Google Docs and other spreadsheet software)
as well as the
[CSV (comma-separated
values)](https://en.wikipedia.org/wiki/Comma-separated_values) format.

- Typesetting exams: Although you can create your exams with other tools,
Eyegrade integrates an utility to creating MCQ exams. It is able to
create your exams in PDF format.  Eyegrade can automatically build
several versions of the exam by reordering questions and choices
within questions.
The [LaTeX document preparation system](https://en.wikipedia.org/wiki/LaTeX)
must be installed in your system in order to use this feature.

For more information about Eyegrade you can visit:

- Its website: https://www.eyegrade.org/
- Its blog: https://www.eyegrade.org/blog/
- Its documentation: https://www.eyegrade.org/documentation/
- Its source code at GitHub: https://github.com/jfisteus/eyegrade
- The downloads page, for pre-built binary files:
  https://www.eyegrade.org/download/

Eyegrade is fully functional and has been used in courses at
Universidad Carlos III de Madrid and other institutions since 2010.

The program is free software, licensed under the terms of the
[GNU General Public License (GPL)
version 3](https://www.gnu.org/licenses/gpl-3.0.html)
or any later version.

Bug reports, feature requests and pull requests are welcome at the
Github repository:

https://github.com/jfisteus/eyegrade

An article describing an earlier version of Eyegrade has been
published by the Journal of Science Education and Technology:

Jesus Arias Fisteus, Abelardo Pardo and Norberto Fernández García,
*Grading Multiple Choice Exams with Low-Cost and Portable
Computer-Vision Techniques*.
Journal of Science Education and Technology,
volume 22, issue 4 (August 2013), pages 560-571.
[doi:10.1007/s10956-012-9414-8](https://dx.doi.org/10.1007/s10956-012-9414-8).

Note for developers: the Eyegrade repository contains two main
branches, *master* and *development*. The *master* branch will be
placed at the latest stable release of Eyegrade. The *development*
branch will receive commits of yet-to-be-released features. If you
plan to submit pull-requests, base your work on the development branch
in order to facilitate their integration.
