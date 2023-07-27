#!/usr/bin/python3
# SPDX-FileCopyrightText: 2016-2023 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only


class OCRConfig(object):
    lang = "eng"  # type: str
    _lang = "Specifies the language seen on the screen 3-character ISO 639-2 language code (eng, deu, fra ...)"

    dump_boxes = ""  # type: str
    _dump_boxes = "Dumps the image of detected lines and boxes in the VNC image to given file"

    dump_screen = ""  # type: str
    _dump_screen = "Dumps the captured VNC screen to the given file"

    dump_x_gradients = ""  # type: str
    _dump_x_gradients = "Dumps the computed gradients on the x-axis to given file"

    dump_y_gradients = ""  # type: str
    _dump_y_gradients = "Dumps the computed gradients on the y-ayis to given file"

    dump_dir = ""  # type: str
    _dump_dir = "Dump every analyzed screen into the given directory"

    img_resize = 2.0  # type: float
    _img_resize = "Resize factor for image to improve OCR results"

    box_max_height = 200  # type: int
    _box_max_height = "Specifies the maximum height a detect box can have"

    box_min_height = 15  # type: int
    _box_min_height = "Specifies the minimum height a detect box must have"

    box_min_width = 40  # type: int
    _box_min_width = "Specifies the minimum width a detect box must have"

    box_corner_points_max_distance = 10.0  # type: float
    _box_corner_points_max_distance = "Maximum distance of the end points of two lines for being detected as box corner"

    line_min_length = 15  # type: int
    _line_min_length = "Specifies the minimum length a detected line must have"

    line_segment_min_covariance = 5  # type: int
    _line_segment_min_covariance = "Specifies the minimum covariance value line segments must have on order to be detected as line"

    line_segment_low_threshold = 20.0  # type: float
    _line_segment_low_threshold = "Minimum absolute gradient value for pixels to be included into the line segment"

    line_segment_high_threshold = 20.0  # type: float
    _line_segment_high_threshold = "Minimum absolute gradient value for pixels to initiate a line segmentation"

    min_str_match_score = 0.7  # type: float
    _min_str_match_score = "Specifies the minimum score a words sequence match needs to have"

    def __init__(self, **kwargs):
        # type: (**str) -> None
        for name, value in kwargs.items():
            if not name.startswith("_") and isinstance(getattr(self, name, None), (float, int, str)):
                setattr(self, name, value)

    update = __init__

    def __repr__(self):
        # type: () -> str
        return "%s(%s)" % (
            self.__class__.__name__,
            ", ".join(
                sorted(
                    "%s=%r" % (name, value)
                    for name, value in ((name, getattr(self, name)) for name in dir(self))
                    if isinstance(value, (float, int, str)) and not name.startswith("_")
                )
            ),
        )

    __str__ = __repr__
