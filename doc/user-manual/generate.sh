#!/bin/sh

mkdir -p samples
cp ../sample-files/ms-word/sample-exam.doc samples
rst2html --stylesheet=voidspace.css user-manual.rst >index.html
