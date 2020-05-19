# Copyright (c) 2020, Manfred Moitzi
# License: MIT License
from typing import TYPE_CHECKING, Optional, Iterable, Tuple, List, Dict, cast
import struct
import math
from enum import IntEnum
from itertools import repeat
from ezdxf.lldxf import const
from ezdxf.tools.binarydata import bytes_to_hexstr, ByteStream, BitStream
from ezdxf.tools import rgb2int
from ezdxf.math import Vector
from ezdxf.entities import factory
from ezdxf.math import ConstructionCircle, ConstructionArc
import logging

if TYPE_CHECKING:
    from ezdxf.eztypes import Tags, TagWriter, Drawing, Polymesh, Polyface, Polyline

logger = logging.getLogger('ezdxf')

CHUNK_SIZE = 127


def load_proxy_graphic(tags: 'Tags', length_code: int = 160, data_code: int = 310) -> Optional[bytes]:
    binary_data = [tag.value for tag in tags.pop_tags(codes=(length_code, data_code)) if tag.code == data_code]
    return b''.join(binary_data) if len(binary_data) else None


def export_proxy_graphic(data: bytes, tagwriter: 'TagWriter', length_code: int = 160, data_code: int = 310) -> None:
    # Do not export proxy graphic for DXF R12 files
    assert tagwriter.dxfversion > const.DXF12

    length = len(data)
    if length == 0:
        return

    tagwriter.write_tag2(length_code, length)
    index = 0
    while index < length:
        hex_str = bytes_to_hexstr(data[index:index + CHUNK_SIZE])
        tagwriter.write_tag2(data_code, hex_str)
        index += CHUNK_SIZE


class ProxyGraphicTypes(IntEnum):
    EXTENTS = 1
    CIRCLE = 2
    CIRCLE_3P = 3
    CIRCULAR_ARC = 4
    CIRCULAR_ARC_3P = 5
    POLYLINE = 6
    POLYGON = 7
    MESH = 8
    SHELL = 9
    TEXT = 10
    TEXT2 = 11
    XLINE = 12
    RAY = 13
    ATTRIBUTE_COLOR = 14
    UNUSED_15 = 15
    ATTRIBUTE_LAYER = 16
    UNUSED_17 = 17
    ATTRIBUTE_LINETYPE = 18
    ATTRIBUTE_MARKER = 19
    ATTRIBUTE_FILL = 20
    UNUSED_21 = 21
    ATTRIBUTE_TRUE_COLOR = 22
    ATTRIBUTE_LINEWEIGHT = 23
    ATTRIBUTE_LTSCALE = 24
    ATTRIBUTE_THICKNESS = 25
    ATTRIBUTE_PLOT_STYLE_NAME = 26
    PUSH_CLIP = 27
    POP_CLIP = 28
    PUSH_MATRIX = 29
    PUSH_MATRIX2 = 30
    POP_MATRIX = 31
    POLYLINE_WITH_NORMALS = 32
    LWPOLYLINE = 33
    ATTRIBUTE_MATERIAL = 34
    ATTRIBUTE_MAPPER = 35
    UNICODE_TEXT = 36
    UNKNOWN_37 = 37
    UNICODE_TEXT2 = 38


COLOR_BY_LAYER = 256

BY_LAYER = 0xFFFFFFFF
BY_BLOCK = 0xFFFFFFFE


class ProxyGraphic:
    def __init__(self, data: bytes, doc: 'Drawing' = None):
        self._doc = doc
        self._factory = doc.dxffactory.new_entity if doc else factory.new
        self._buffer: bytes = data
        self._index: int = 8
        self.dxfversion = doc.dxfversion if doc else 'AC1015'
        self.color: int = COLOR_BY_LAYER
        self.layer: str = '0'
        self.linetype: str = 'BYLAYER'
        self.marker_index: int = 0
        self.fill: bool = False
        self.true_color: Optional[int] = None
        self.lineweight: int = const.LINEWEIGHT_DEFAULT
        self.ltscale: float = 1.0
        self.thickness: float = 0.0
        # Layer list in storage order
        self.layers: List[str] = []
        # Linetypes list in storage order
        self.linetypes: List[str] = []
        # List of text styles, with font name as key
        self.textstyles = dict()
        self.required_fonts = set()

        if self._doc:
            self.layers = list(layer.dxf.name for layer in self._doc.layers)
            self.linetypes = list(linetype.dxf.name for linetype in self._doc.linetypes)
            self.textstyles = {style.dxf.font: style.dxf.name for style in self._doc.styles}

    def info(self) -> Iterable[Tuple[int, int, str]]:
        index = self._index
        buffer = self._buffer
        while index < len(buffer):
            size, type_ = struct.unpack_from('<2L', self._buffer, offset=index)
            try:
                name = ProxyGraphicTypes(type_).name
            except ValueError:
                name = f'UNKNOWN_TYPE_{type_}'
            yield index, size, name
            index += size

    def virtual_entities(self):
        index = self._index
        buffer = self._buffer
        while index < len(buffer):
            size, type_ = struct.unpack_from('<2L', self._buffer, offset=index)
            try:
                name = ProxyGraphicTypes(type_).name.lower()
            except ValueError:
                logger.debug(f'Unsupported Type Code: {type_}')
                index += size
                continue
            method = getattr(self, name, None)
            if method:
                result = method(self._buffer[index + 8: index + size])
                if isinstance(result, tuple):
                    yield from result
                elif result:
                    yield result
            else:
                logger.debug(f'Unsupported feature ProxyGraphic.{name}()')
            index += size

    def attribute_color(self, data: bytes):
        self.color = struct.unpack('<L', data)[0]
        if self.color < 0 or self.color > 256:
            self.color = COLOR_BY_LAYER

    def attribute_layer(self, data: bytes):
        if self._doc:
            index = struct.unpack('<L', data)[0]
            if index < len(self.layers):
                self.layer = self.layers[index]

    def attribute_linetype(self, data: bytes):
        if self._doc:
            index = struct.unpack('<L', data)[0]
            if index < len(self.linetypes):
                self.linetype = self.linetypes[index]

    def attribute_marker(self, data: bytes):
        self.marker_index = struct.unpack('<L', data)[0]

    def attribute_fill(self, data: bytes):
        self.fill = bool(struct.unpack('<L', data)[0])

    def attribute_true_color(self, data: bytes):
        # todo check byte order!
        self.true_color = rgb2int((data[1], data[2], data[3]))

    def attribute_lineweight(self, data: bytes):
        self.lineweight = struct.unpack('<L', data)[0]
        if self.lineweight == BY_LAYER:
            self.lineweight = const.LINEWEIGHT_BYLAYER
        if self.lineweight == BY_BLOCK:
            self.lineweight = const.LINEWEIGHT_BYBLOCK

    def attribute_ltscale(self, data: bytes):
        self.ltscale = struct.unpack('<d', data)[0]

    def attribute_thickness(self, data: bytes):
        self.thickness = struct.unpack('<d', data)[0]

    def circle(self, data: bytes):
        bs = ByteStream(data)
        attribs = self._build_dxf_attribs()
        attribs['center'] = Vector(bs.read_vertex())
        attribs['radius'] = bs.read_float()
        attribs['extrusion'] = bs.read_vertex()
        return self._factory('CIRCLE', dxfattribs=attribs)

    def circle_3p(self, data: bytes):
        bs = ByteStream(data)
        attribs = self._build_dxf_attribs()
        p1 = Vector(bs.read_vertex())
        p2 = Vector(bs.read_vertex())
        p3 = Vector(bs.read_vertex())
        circle = ConstructionCircle.from_3p(p1, p2, p3)
        attribs['center'] = circle.center
        attribs['radius'] = circle.radius
        return self._factory('CIRCLE', dxfattribs=attribs)

    def circular_arc(self, data: bytes):
        bs = ByteStream(data)
        attribs = self._build_dxf_attribs()
        attribs['center'] = Vector(bs.read_vertex())
        attribs['radius'] = bs.read_float()
        normal = Vector(bs.read_vertex())
        if normal != (0, 0, 1):
            logger.debug('ProxyGraphic: unsupported 3D ARC.')
        start_vec = Vector(bs.read_vertex())
        sweep_angle = bs.read_float()
        arc_type = bs.read_struct('L')[0]
        attribs = self._build_dxf_attribs()
        # just do 2D for now
        start_angle = start_vec.angle_deg
        end_angle = start_angle + math.degrees(sweep_angle)
        attribs['start_angle'] = start_angle
        attribs['end_angle'] = end_angle
        return self._factory('ARC', dxfattribs=attribs)

    def circular_arc_3p(self, data: bytes):
        bs = ByteStream(data)
        attribs = self._build_dxf_attribs()
        p1 = Vector(bs.read_vertex())
        p2 = Vector(bs.read_vertex())
        p3 = Vector(bs.read_vertex())
        arc_type = bs.read_struct('L')[0]
        arc = ConstructionArc.from_3p(p1, p3, p2)
        attribs['center'] = arc.center
        attribs['radius'] = arc.radius
        attribs['start_angle'] = arc.start_angle
        attribs['end_angle'] = arc.end_angle
        return self._factory('ARC', dxfattribs=attribs)

    def polyline_with_normals(self, data: bytes):
        vertices = self._load_vertices(data)
        attribs = self._build_dxf_attribs()

        if len(vertices) == 2 and vertices[0].isclose(vertices[1]):
            attribs['location'] = vertices[0]
            return self._factory('POINT', dxfattribs=attribs)

        attribs['flags'] = const.POLYLINE_3D_POLYLINE
        polyline = cast('Polyline', self._factory('POLYLINE', dxfattribs=attribs))
        polyline.append_vertices(vertices)
        return polyline

    def polyline(self, data: bytes):
        return self.polyline_with_normals(data)

    def polygon(self, data: bytes):
        polygon = self.polyline_with_normals(data)
        if polygon.dxftype() == 'POLYLINE':
            polygon.close()
        return polygon

    def lwpolyline(self, data: bytes):
        # OpenDesign Specs LWPLINE: 20.4.85 Page 211
        logger.warning('Untested proxy graphic entity: LWPOLYLINE - Need examples!')
        bs = BitStream(data)
        flag = bs.read_bit_short()
        attribs = self._build_dxf_attribs()
        if flag & 4:
            attribs['const_width'] = bs.read_bit_double()
        if flag & 8:
            attribs['elevation'] = bs.read_bit_double()
        if flag & 2:
            attribs['thickness'] = bs.read_bit_double()
        if flag & 1:
            attribs['extrusion'] = Vector(bs.read_bit_double(3))

        num_points = bs.read_bit_long()
        if flag & 16:
            num_bulges = bs.read_bit_long()
        else:
            num_bulges = 0

        if self.dxfversion >= 'AC1024':  # R2010+
            vertex_id_count = bs.read_bit_long()
        else:
            vertex_id_count = 0

        if flag & 32:
            num_width = bs.read_bit_long()
        else:
            num_width = 0
        # ignore DXF R13/14 special vertex order

        vertices = [bs.read_raw_double(2)]
        prev_point = vertices[-1]
        for _ in range(num_points - 1):
            x = bs.read_bit_double_default(default=prev_point[0])
            y = bs.read_bit_double_default(default=prev_point[1])
            prev_point = (x, y)
            vertices.append(prev_point)
        bulges = [bs.read_bit_double() for _ in range(num_bulges)]
        vertex_ids = [bs.read_bit_long() for _ in range(vertex_id_count)]
        widths = [(bs.read_bit_double(), bs.read_bit_double()) for _ in range(num_width)]
        if len(bulges) == 0:
            bulges = list(repeat(0, num_points))
        if len(widths) == 0:
            widths = list(repeat((0, 0), num_points))
        points = []
        for v, w, b in zip(vertices, widths, bulges):
            points.append((v[0], v[1], w[0], w[1], b))
        lwpolyline = cast('LWPolyline', self._factory('LWPOLYLINE', dxfattribs=attribs))
        lwpolyline.set_points(points)
        return lwpolyline
    
    def mesh(self, data: bytes):
        logger.warning('Untested proxy graphic entity: MESH - Need examples!')
        bs = ByteStream(data)
        rows, columns = bs.read_struct('2L')
        attribs = self._build_dxf_attribs()
        attribs['m_count'] = rows
        attribs['n_count'] = columns
        attribs['flags'] = const.POLYLINE_3D_POLYMESH
        polymesh = cast('Polymesh', self._factory('POLYLINE', dxfattribs=attribs))
        polymesh.append_vertices(Vector(bs.read_vertex()) for _ in range(rows * columns))
        return polymesh

    def shell(self, data: bytes):
        logger.warning('Untested proxy graphic entity: SHELL - Need examples!')
        bs = ByteStream(data)
        attribs = self._build_dxf_attribs()
        attribs['flags'] = const.POLYLINE_POLYFACE
        polyface = cast('Polyface', self._factory('POLYLINE', dxfattribs=attribs))
        vertex_count = bs.read_long()
        vertices = [Vector(bs.read_vertex()) for _ in range(vertex_count)]
        face_count = bs.read_long()
        faces = []
        for i in range(face_count):
            vertex_count = abs(bs.read_signed_long())
            face_indices = [bs.read_long() for _ in range(vertex_count)]
            face = [vertices[index] for index in face_indices]
            faces.append(face)
        polyface.append_faces(faces)
        polyface.optimize()
        # todo: SHELL - read face properties, but requires an example.
        return polyface

    def text(self, data: bytes):
        return self._text(data, unicode=False)

    def unicode_text(self, data: bytes):
        return self._text(data, unicode=True)

    def _text(self, data: bytes, unicode: bool = False):
        bs = ByteStream(data)
        start_point = Vector(bs.read_vertex())
        normal = Vector(bs.read_vertex())
        text_direction = Vector(bs.read_vertex())
        height, width_factor, oblique_angle = bs.read_struct('<3d')
        if unicode:
            text = bs.read_padded_unicode_string()
        else:
            text = bs.read_padded_string()
        attribs = self._build_dxf_attribs()
        attribs['insert'] = start_point
        attribs['text'] = text
        attribs['height'] = height
        attribs['width'] = width_factor
        attribs['rotation'] = text_direction.angle_deg
        attribs['oblique'] = math.degrees(oblique_angle)
        attribs['extrusion'] = normal
        return self._factory('TEXT', dxfattribs=attribs)

    def text2(self, data: bytes):
        bs = ByteStream(data)
        start_point = Vector(bs.read_vertex())
        normal = Vector(bs.read_vertex())
        text_direction = Vector(bs.read_vertex())
        text = bs.read_padded_string()
        ignore_length_of_string, raw = bs.read_struct('<2l')
        height, width_factor, oblique_angle, tracking_percentage = bs.read_struct('<4d')
        is_backwards, is_upside_down, is_vertical, is_underline, is_overline = bs.read_struct('<5L')
        font_filename = bs.read_padded_string()
        big_font_filename = bs.read_padded_string()
        attribs = self._build_dxf_attribs()
        attribs['insert'] = start_point
        attribs['text'] = text
        attribs['height'] = height
        attribs['width'] = width_factor
        attribs['rotation'] = text_direction.angle_deg
        attribs['oblique'] = math.degrees(oblique_angle)
        attribs['style'] = self._get_style(font_filename, big_font_filename)
        attribs['text_generation_flag'] = 2 * is_backwards + 4 * is_upside_down
        attribs['extrusion'] = normal
        return self._factory('TEXT', dxfattribs=attribs)

    def unicode_text2(self, data: bytes):
        bs = ByteStream(data)
        start_point = Vector(bs.read_vertex())
        normal = Vector(bs.read_vertex())
        text_direction = Vector(bs.read_vertex())
        text = bs.read_padded_unicode_string()
        ignore_length_of_string, ignore_raw = bs.read_struct('<2l')
        height, width_factor, oblique_angle, tracking_percentage = bs.read_struct('<4d')
        is_backwards, is_upside_down, is_vertical, is_underline, is_overline = bs.read_struct('<5L')
        is_bold, is_italic, charset, pitch = bs.read_struct('<4L')
        type_face = bs.read_padded_unicode_string()
        font_filename = bs.read_padded_unicode_string()
        big_font_filename = bs.read_padded_unicode_string()
        attribs = self._build_dxf_attribs()
        attribs['insert'] = start_point
        attribs['text'] = text
        attribs['height'] = height
        attribs['width'] = width_factor
        attribs['rotation'] = text_direction.angle_deg
        attribs['oblique'] = math.degrees(oblique_angle)
        attribs['style'] = self._get_style(font_filename, big_font_filename)
        attribs['text_generation_flag'] = 2 * is_backwards + 4 * is_upside_down
        attribs['extrusion'] = normal
        return self._factory('TEXT', dxfattribs=attribs)

    def xline(self, data: bytes):
        return self._xline(data, 'XLINE')

    def ray(self, data: bytes):
        return self._xline(data, 'RAY')

    def _xline(self, data: bytes, type_: str):
        logger.warning('Untested proxy graphic entity: RAY/XLINE - Need examples!')
        bs = ByteStream(data)
        attribs = self._build_dxf_attribs()
        start_point = Vector(bs.read_vertex())
        other_point = Vector(bs.read_vertex())
        attribs['start'] = start_point
        attribs['unit_vector'] = (other_point - start_point).normalize()
        return self._factory(type_, dxfattribs=attribs)

    def _get_style(self, font: str, bigfont: str) -> str:
        self.required_fonts.add(font)
        if font in self.textstyles:
            style = self.textstyles[font]
        else:
            style = font
            if self._doc:
                self._doc.styles.new(font, dxfattribs={'font': font, 'bigfont': bigfont})
        return style

    def _load_vertices(self, data: bytes):
        bs = ByteStream(data)
        count = bs.read_struct('<L')[0]
        vertices = []
        while count > 0:
            vertices.append(Vector(bs.read_struct('<3d')))
            count -= 1
        return vertices

    def _build_dxf_attribs(self) -> Dict:
        attribs = dict()
        if self.layer != '0':
            attribs['layer'] = self.layer
        if self.color != COLOR_BY_LAYER:
            attribs['color'] = self.color
        if self.linetype != 'BYLAYER':
            attribs['linetype'] = self.linetype
        if self.lineweight != const.LINEWEIGHT_DEFAULT:
            attribs['lineweight'] = self.lineweight
        if self.ltscale != 1.0:
            attribs['ltscale'] = self.ltscale
        if self.true_color is not None:
            attribs['true_color'] = self.true_color
        return attribs
