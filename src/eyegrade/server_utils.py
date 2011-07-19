import array

# Import the cv module. If new style bindings not found, use the old ones:
try:
    import cv
    cv_new_style = True
except ImportError:
    import cvwrapper
    cv = cvwrapper.CVWrapperObject()
    cv_new_style = False

def bitmap_to_image(image_width, image_height, bitmap):
    """Converts an array of bytes into an IPL image.

       Bitmap must be an array.array of type 'B' (unsigned bytes). The
       byte 0 represents the 8 pixels to the upper-left of the image.
       In that byte, the most significative bit is the left-most bit
       of the row. The rest of the bytes go from left to right, up to
       bottom. Each row is represented by an integer number of bytes,
       with the possibility of unused bits in the last byte of each row.

       The returned IPL image will have depth 8 and 1 channel. Pixels
       will be either 255 or 0.
    """
    assert(bitmap.typecode == 'B')
    image = cv.CreateImage((image_width, image_height), 8, 1)
    byte_pos = 0
    bytes_per_row = (image_width + 7) // 8
    masks = (1 << 7, 1 << 6, 1 << 5, 1 << 4, 1 << 3, 1 << 2, 1 << 1, 1)
    for i in range(0, image_height):
        row_pos = 0
        for j in range(0, bytes_per_row):
            byte = bitmap[byte_pos]
            byte_pos += 1
            for k in range(0, 8):
                image[i, row_pos] = 255 if byte & masks[k] else 0
                row_pos += 1
                if row_pos == image_width:
                    break
    return image

def image_to_bitmap(image):
    """Converts an IPL image into an array of bytes.

       See bitmap_to_image() for details.
    """

    assert(image.depth == 8 and image.nChannels == 1)
    bytes_per_row = (image.width + 7) // 8
    bitmap_list = []
    for i in range(0, image.height):
        row_pos = 0
        for j in range(0, bytes_per_row):
            byte = 0
            for k in range(0, 8):
                byte = byte | (image[i, row_pos] > 0) << (7 - k)
                row_pos += 1
                if row_pos == image.width:
                    break
            bitmap_list.append(byte)
    return array.array('B', bitmap_list)

def test():
    import imageproc
    image = cv.LoadImage('../captures/test-001-processed.png')
    image_proc = imageproc.rgb_to_gray(image)
    bitmap = image_to_bitmap(image_proc)
    image2 = bitmap_to_image(image_proc.width, image_proc.height, bitmap)
    cv.SaveImage('/tmp/test.png', image2)
