# Copyright (c) 2019-2020 Manfred Moitzi
# License: MIT License
# Created 2019-03-06
from typing import TYPE_CHECKING, Union, Tuple, List
import math

from ezdxf.math import Vector
from ezdxf.lldxf import const
from ezdxf.lldxf.attributes import DXFAttr, DXFAttributes, DefSubclass, XType
from ezdxf.lldxf.const import SUBCLASS_MARKER, DXF2000
from ezdxf.lldxf.tags import Tags
from ezdxf.tools.rgb import rgb2int
from .dxfentity import base_class, SubclassProcessor
from .dxfgfx import DXFGraphic, acdb_entity
from .factory import register_entity

if TYPE_CHECKING:
    from ezdxf.eztypes import TagWriter, DXFNamespace, Drawing, DXFEntity, Vertex, UCS

__all__ = ['MText']

acdb_mtext = DefSubclass('AcDbMText', {
    'insert': DXFAttr(10, xtype=XType.point3d, default=Vector(0, 0, 0)),
    'char_height': DXFAttr(40, default=2.5),  # nominal (initial) text height
    'width': DXFAttr(41, optional=True),  # reference column width
    'defined_height': DXFAttr(46, dxfversion='AC1021'),  # found in BricsCAD export

    # 1 = Top left; 2 = Top center; 3 = Top right
    # 4 = Middle left; 5 = Middle center; 6 = Middle right
    # 7 = Bottom left; 8 = Bottom center; 9 = Bottom right
    'attachment_point': DXFAttr(71, default=1),

    # 1 = Left to right
    # 3 = Top to bottom
    # 5 = By style (the flow direction is inherited from the associated text style)
    'flow_direction': DXFAttr(72, default=1, optional=True),

    # code 1: text
    # code 3: additional text (optional)

    'style': DXFAttr(7, default='Standard', optional=True),  # text style name
    'extrusion': DXFAttr(210, xtype=XType.point3d, default=Vector(0, 0, 1), optional=True),

    # x-axis direction vector (in WCS)
    # If rotation and text_direction are present, text_direction wins
    'text_direction': DXFAttr(11, xtype=XType.point3d, default=Vector(1, 0, 0), optional=True),

    # Horizontal width of the characters that make up the mtext entity.
    # This value will always be equal to or less than the value of *width*, (read-only, ignored if supplied)
    'rect_width': DXFAttr(42, optional=True),

    # vertical height of the mtext entity (read-only, ignored if supplied)
    'rect_height': DXFAttr(43, optional=True),

    # in degrees (circle=360 deg) -  error in DXF reference, which says radians
    'rotation': DXFAttr(50, default=0, optional=True),

    # 1 = At least (taller characters will override)
    # 2 = Exact (taller characters will not override)
    'line_spacing_style': DXFAttr(73, default=1, optional=True),  # line spacing style (optional):

    # Percentage of default (3-on-5) line spacing to be applied. Valid values
    # range from 0.25 to 4.00
    'line_spacing_factor': DXFAttr(44, default=1, optional=True),  # line spacing factor (optional):

    # Determines how much border there is around the text.
    # (45) + (90) + (63) all three required, if one of them is used
    'box_fill_scale': DXFAttr(45, dxfversion='AC1021'),

    # background fill type:
    # 0 = off
    # 1 = color -> (63) < (421) or (431)
    # 2 = drawing window color
    # 3 = use background color
    'bg_fill': DXFAttr(90, dxfversion='AC1021'),

    'bg_fill_color': DXFAttr(63, dxfversion='AC1021'),  # background fill color as ACI, required even true color is used

    # 420-429? : background fill color as true color value, (63) also required but ignored
    'bg_fill_true_color': DXFAttr(421, dxfversion='AC1021'),

    # 430-439? : background fill color as color name ???, (63) also required but ignored
    'bg_fill_color_name': DXFAttr(431, dxfversion='AC1021'),

    # background fill color transparency - not used by AutoCAD/BricsCAD
    'bg_fill_transparency': DXFAttr(441, dxfversion='AC1021'),

})


# ----------------------------------------------------------------------
# NO MULTI-COLUMN SUPPORT
# ----------------------------------------------------------------------
# MTEXT column information will be preserved by ezdxf, but no further
# support for accessing the information nor to create multi-column MTEXT.
# The column definition is stored in XDATA 'ACAD' and new in DXF R2018
# as 'embedded object', but codes are different to codes in the
# DXF reference:
#
# code 75   Column type
# code 76	Column count
# code 78	Column Flow Reversed
# code 79	Column Auto height
# code 48	Column width
# code 49	Column gutter
#
# code 50	Column heights; this code is followed by a column count
# (Int16), and then the number of column heights
# ----------------------------------------------------------------------


@register_entity
class MText(DXFGraphic):
    """ DXF MTEXT entity """
    DXFTYPE = 'MTEXT'
    DXFATTRIBS = DXFAttributes(base_class, acdb_entity, acdb_mtext)
    MIN_DXF_VERSION_FOR_EXPORT = DXF2000

    UNDERLINE_START = r'\L'
    UNDERLINE_STOP = r'\l'
    UNDERLINE = UNDERLINE_START + '%s' + UNDERLINE_STOP
    OVERSTRIKE_START = r'\O'
    OVERSTRIKE_STOP = r'\o'
    OVERSTRIKE = OVERSTRIKE_START + '%s' + OVERSTRIKE_STOP
    STRIKE_START = r'\K'
    STRIKE_STOP = r'\k'
    STRIKE = STRIKE_START + '%s' + STRIKE_STOP
    NEW_LINE = r'\P'
    GROUP_START = '{'
    GROUP_END = '}'
    GROUP = GROUP_START + '%s' + GROUP_END
    NBSP = r'\~'  # none breaking space

    def __init__(self, doc: 'Drawing' = None):
        """ Default constructor """
        super().__init__(doc)
        self.text = ""  # type: str

    def _copy_data(self, entity: 'DXFEntity') -> None:
        """ Copy entity data: text """
        entity.text = self.text

    def load_dxf_attribs(self, processor: SubclassProcessor = None) -> 'DXFNamespace':
        dxf = super().load_dxf_attribs(processor)
        if processor:
            self.load_mtext(processor.subclasses[2])
            tags = processor.load_dxfattribs_into_namespace(dxf, acdb_mtext)
            if len(tags):
                processor.log_unprocessed_tags(tags, subclass=acdb_mtext.name)
        return dxf

    def export_entity(self, tagwriter: 'TagWriter') -> None:
        """ Export entity specific data as DXF tags. """
        # base class export is done by parent class
        super().export_entity(tagwriter)
        # AcDbEntity export is done by parent class
        tagwriter.write_tag2(SUBCLASS_MARKER, acdb_mtext.name)
        self.dxf.export_dxf_attribs(tagwriter, [
            'insert', 'char_height', 'width', 'defined_height', 'attachment_point', 'flow_direction'
        ])
        self.export_mtext(tagwriter)
        self.dxf.export_dxf_attribs(tagwriter, [
            'style', 'extrusion', 'text_direction', 'rect_width', 'rect_height', 'rotation', 'line_spacing_style',
            'line_spacing_factor', 'box_fill_scale', 'bg_fill', 'bg_fill_color', 'bg_fill_true_color',
            'bg_fill_color_name', 'bg_fill_transparency'
        ])
        # xdata and embedded_object export by parent class

    def load_mtext(self, tags: Tags) -> None:
        tail = ""
        parts = []
        for tag in tags:
            if tag.code == 1:
                tail = tag.value
            if tag.code == 3:
                parts.append(tag.value)
        parts.append(tail)
        self.text = "".join(parts)
        tags.remove_tags((1, 3))

    def export_mtext(self, tagwriter: 'TagWriter') -> None:
        # replacing '\n' by '\P' is required, else an invalid DXF file would be created
        txt = self.text.replace('\n', '\\P')
        str_chunks = split_mtext_string(txt, size=250)
        if len(str_chunks) == 0:
            str_chunks.append("")
        while len(str_chunks) > 1:
            tagwriter.write_tag2(3, str_chunks.pop(0))
        tagwriter.write_tag2(1, str_chunks[0])

    def get_rotation(self) -> float:
        """ Get text rotation in degrees, independent if it is defined by :attr:`dxf.rotation` or
        :attr:`dxf.text_direction`.
        """
        if self.dxf.hasattr('text_direction'):
            vector = self.dxf.text_direction
            radians = math.atan2(vector[1], vector[0])  # ignores z-axis
            rotation = math.degrees(radians)
        else:
            rotation = self.dxf.get('rotation', 0)
        return rotation

    def set_rotation(self, angle: float) -> 'MText':
        """ Set attribute :attr:`rotation` to `angle` (in degrees) and deletes :attr:`dxf.text_direction` if present.
        """
        # text_direction has higher priority than rotation, therefore delete it
        self.dxf.discard('text_direction')
        self.dxf.rotation = angle
        return self  # fluent interface

    def set_location(self, insert: 'Vertex', rotation: float = None, attachment_point: int = None) -> 'MText':
        """ Set attributes :attr:`dxf.insert`, :attr:`dxf.rotation` and :attr:`dxf.attachment_point`,
        ``None`` for :attr:`dxf.rotation` or :attr:`dxf.attachment_point` preserves the existing value.
        """
        self.dxf.insert = Vector(insert)
        if rotation is not None:
            self.set_rotation(rotation)
        if attachment_point is not None:
            self.dxf.attachment_point = attachment_point
        return self  # fluent interface

    def set_bg_color(self, color: Union[int, str, Tuple[int, int, int], None], scale: float = 1.5):
        """
        Set background color as :ref:`ACI` value or as name string or as RGB tuple ``(r, g, b)``.

        Use special color name ``canvas``, to set background color to canvas background color.

        Args:
            color: color as :ref:`ACI`, string or RGB tuple
            scale: determines how much border there is around the text, the value is based on the text height,
                   and should be in the range of ``1`` - ``5``, where ``1`` fits exact the MText entity.

        """
        if 1 <= scale <= 5:
            self.dxf.box_fill_scale = scale
        else:
            raise ValueError('argument scale has to be in range from 1 to 5.')
        if color is None:
            self.dxf.discard('bg_fill')
            self.dxf.discard('box_fill_scale')
            self.dxf.discard('bg_fill_color')
            self.dxf.discard('bg_fill_true_color')
            self.dxf.discard('bg_fill_color_name')
        elif color == 'canvas':  # special case for use background color
            self.dxf.bg_fill = const.MTEXT_BG_CANVAS_COLOR
            self.dxf.bg_fill_color = 0  # required but ignored
        else:
            self.dxf.bg_fill = const.MTEXT_BG_COLOR
            if isinstance(color, int):
                self.dxf.bg_fill_color = color
            elif isinstance(color, str):
                self.dxf.bg_fill_color = 0  # required but ignored
                self.dxf.bg_fill_color_name = color
            elif isinstance(color, tuple):
                self.dxf.bg_fill_color = 0  # required but ignored
                self.dxf.bg_fill_true_color = rgb2int(color)
        return self  # fluent interface

    def __iadd__(self, text: str) -> 'MText':
        """ Append `text` to existing content (:attr:`.text` attribute). """
        self.text += text
        return self

    append = __iadd__

    def set_font(self, name: str, bold: bool = False, italic: bool = False, codepage: int = 1252,
                 pitch: int = 0) -> None:
        """ Append font change (e.g. ``'\\Fkroeger|b0|i0|c238|p10'`` ) to existing content (:attr:`.text` attribute).

        Args:
            name: font name
            bold: flag
            italic: flag
            codepage: character codepage
            pitch: font size

        """
        bold_flag = 1 if bold else 0
        italic_flag = 1 if italic else 0
        s = r"\F{}|b{}|i{}|c{}|p{};".format(name, bold_flag, italic_flag, codepage, pitch)
        self.append(s)

    def set_color(self, color_name: str) -> None:
        """ Append text color change to existing content, `color_name` as ``red``, ``yellow``, ``green``, ``cyan``,
        ``blue``, ``magenta`` or ``white``.
        """
        self.append(r"\C%d" % const.MTEXT_COLOR_INDEX[color_name.lower()])

    def add_stacked_text(self, upr: str, lwr: str, t: str = '^') -> None:
        r"""
        Add stacked text `upr` over `lwr`, `t` defines the kind of stacking:

        .. code-block:: none

            "^": vertical stacked without divider line, e.g. \SA^B:
                 A
                 B

            "/": vertical stacked with divider line,  e.g. \SX/Y:
                 X
                 -
                 Y

            "#": diagonal stacked, with slanting divider line, e.g. \S1#4:
                 1/4

        """
        # space ' ' in front of {lwr} is important
        self.append(r'\S{upr}{t} {lwr};'.format(upr=upr, lwr=lwr, t=t))

    def transform_to_wcs(self, ucs: 'UCS') -> 'MText':
        """ Transform MTEXT entity from local :class:`~ezdxf.math.UCS` coordinates to :ref:`WCS` coordinates.

        .. versionadded:: 0.11

        """
        if self.dxf.hasattr('rotation'):
            self.dxf.text_direction = Vector.from_deg_angle(self.dxf.rotation)
            self.dxf.discard('rotation')

        self.dxf.insert = ucs.to_wcs(self.dxf.insert)
        self.dxf.text_direction = ucs.direction_to_wcs(self.dxf.text_direction)
        self.dxf.extrusion = ucs.direction_to_wcs(self.dxf.extrusion)
        return self

    def plain_text(self, split=False) -> Union[List[str], str]:
        """
        Returns text content without formatting codes.

        Args:
            split: returns list of strings splitted at line breaks if ``True`` else returns a single string.

        .. versionadded:: 0.11.1

        """
        return plain_text(self.text, split=split)


def plain_text(text: str, split=False) -> Union[List[str], str]:
    chars = []
    raw_chars = list(reversed(text))  # text splitted into chars, in reversed order for efficient pop()
    while len(raw_chars):
        char = raw_chars.pop()
        if char == '\\':  # is a formatting command
            try:
                char = raw_chars.pop()
            except IndexError:
                break  # premature end of text - just ignore

            if char in '\\{}':
                chars.append(char)
            elif char in ONE_CHAR_COMMANDS:
                if char == 'P':  # new line
                    chars.append('\n')
                    # discard other commands
            else:  # more character commands are terminated by ';'
                stacking = char == 'S'  # stacking command surrounds user data
                try:
                    while char != ';':  # end of format marker
                        char = raw_chars.pop()
                        if stacking and char != ';':
                            chars.append(char)  # append user data of stacking command
                except IndexError:
                    break  # premature end of text - just ignore
        elif char in '{}':  # grouping
            pass  # discard group markers
        elif char == '%':  # special characters
            if len(raw_chars) and raw_chars[-1] == '%':
                raw_chars.pop()  # discard next '%'
                if len(raw_chars):
                    special_char = raw_chars.pop()
                    # replace or discard formatting code
                    chars.append(SPECIAL_CHARS.get(special_char, ""))
            else:  # char is just a single '%'
                chars.append(char)
        else:  # char is what it is, a character
            chars.append(char)

    result = "".join(chars)
    return result.split('\n') if split else result


ONE_CHAR_COMMANDS = "PLlOoKkX"
SPECIAL_CHARS = {
    'd': '°'
}


##################################################
# MTEXT inline codes
# \L	Start underline
# \l	Stop underline
# \O	Start overstrike
# \o	Stop overstrike
# \K	Start strike-through
# \k	Stop strike-through
# \P	New paragraph (new line)
# \pxi	Control codes for bullets, numbered paragraphs and columns
# \X	Paragraph wrap on the dimension line (only in dimensions)
# \Q	Slanting (oblique) text by angle - e.g. \Q30;
# \H	Text height - e.g. \H3x;
# \W	Text width - e.g. \W0.8x;
# \F	Font selection
#
#     e.g. \Fgdt;o - GDT-tolerance
#     e.g. \Fkroeger|b0|i0|c238|p10 - font Kroeger, non-bold, non-italic, codepage 238, pitch 10
#
# \S	Stacking, fractions
#
#     e.g. \SA^B:
#     A
#     B
#     e.g. \SX/Y:
#     X
#     -
#     Y
#     e.g. \S1#4:
#     1/4
#
# \A	Alignment
#
#     \A0; = bottom
#     \A1; = center
#     \A2; = top
#
# \C	Color change
#
#     \C1; = red
#     \C2; = yellow
#     \C3; = green
#     \C4; = cyan
#     \C5; = blue
#     \C6; = magenta
#     \C7; = white
#
# \T	Tracking, char.spacing - e.g. \T2;
# \~	Non-wrapping space, hard space
# {}	Braces - define the text area influenced by the code
# \	Escape character - e.g. \\ = "\", \{ = "{"
#
# Codes and braces can be nested up to 8 levels deep


def split_mtext_string(s: str, size: int = 250) -> List[str]:
    chunks = []
    pos = 0
    while True:
        chunk = s[pos:pos + size]
        if len(chunk):
            if len(chunk) < size:
                chunks.append(chunk)
                return chunks
            pos += size
            # do not split chunks at '^'
            if chunk[-1] == '^':
                chunk = chunk[:-1]
                pos -= 1
            chunks.append(chunk)
        else:
            return chunks
