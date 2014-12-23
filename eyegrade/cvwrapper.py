# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2011 Jesus Arias Fisteus
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
# <http://www.gnu.org/licenses/>.
#

# Wrapper to the old bindings for OpenCV. Maps new style calls to old
# style calls. Useful while versions of python-opencv with only the
# old interface exist.
#
# Usage:
#
# try:
#     import cv
#     cv_new_style = True
# except ImportError:
#     from . import cvwrapper
#     cv = cvwrapper.CVWrapperObject()
#     cv_new_style = False
#
# Functions are then called using their 'new-style' name. For example:
#
# cv.Circle(...)
#

try:
    import opencv
    from opencv import highgui
except:
    raise ImportError('Both modules cv and opencv missing; at least one needed')

class CVWrapperObject(object):
    def __init__(self):
        self.function_cache = {
            'CaptureFromCAM': getattr(highgui, 'cvCreateCameraCapture')
            }

    def ipl_to_pil(self, image):
        """This function does not exist in the new bindings, and therefore
           it cannot be handled by __getattr__"""
        return opencv.adaptors.Ipl2PIL(image)

    def __getattr__(self, name):
        """Dinamically returns old-style cv functions/attributes given their
           new-style name."""
        if name in self.function_cache:
            function = self.function_cache[name]
        else:
            if not name.startswith('CV'):
                cv_name = 'cv' + name
            else:
                cv_name = name
            try:
                function = getattr(opencv, cv_name)
            except AttributeError:
                try:
                    function = getattr(highgui, cv_name)
                except AttributeError:
                    function = None
            self.function_cache[name] = function
        if function is None:
            raise AttributeError()
        else:
            return function
