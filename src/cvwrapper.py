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
#     import cvwrapper
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
        self.function_cache = {}

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
