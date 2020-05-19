# Copyright (c) 2019-2020 Manfred Moitzi
# License: MIT License
# Created 2019-02-15
from typing import TYPE_CHECKING, Tuple, Sequence, Iterable, cast, List, Union
import array
import copy
from contextlib import contextmanager
from ezdxf.math import Vector
from ezdxf.lldxf.attributes import DXFAttr, DXFAttributes, DefSubclass, XType
from ezdxf.lldxf.const import SUBCLASS_MARKER, DXF2000, LWPOLYLINE_CLOSED, DXFStructureError
from ezdxf.lldxf.tags import Tags
from ezdxf.lldxf.types import DXFTag, DXFVertex
from ezdxf.lldxf.packedtags import VertexArray
from ezdxf.explode import virtual_lwpolyline_entities, explode_entity
from ezdxf.query import EntityQuery
from .dxfentity import base_class, SubclassProcessor
from .dxfgfx import DXFGraphic, acdb_entity
from .factory import register_entity

if TYPE_CHECKING:
    from ezdxf.eztypes import TagWriter, Drawing, Vertex, DXFNamespace, UCS, Line, Arc, BaseLayout

__all__ = ['LWPolyline']

LWPointType = Tuple[float, float, float, float, float]

FORMAT_CODES = frozenset('xysebv')
DEFAULT_FORMAT = 'xyseb'
LWPOINTCODES = (10, 20, 40, 41, 42)

# Order doesn't matter, not valid for AutoCAD:
# If tag 90 is not the first TAG, AutoCAD does not close the polyline, when the `close` flag is set.
acdb_lwpolyline = DefSubclass('AcDbPolyline', {
    'count': DXFAttr(90, xtype=XType.callback, getter='__len__'),
    # always return actual length and set tag 90
    'elevation': DXFAttr(38, default=0, optional=True),
    'thickness': DXFAttr(39, default=0, optional=True),
    'flags': DXFAttr(70, default=0),
    'const_width': DXFAttr(43, optional=True),
    'extrusion': DXFAttr(210, xtype=XType.point3d, default=Vector(0, 0, 1), optional=True),
    # 10, 20 : Vertex x, y
    # 91: vertex identifier ???
    # 40, 41, 42: start width, end width, bulge
})


@register_entity
class LWPolyline(DXFGraphic):
    """ DXF LWPOLYLINE entity """
    DXFTYPE = 'LWPOLYLINE'
    DXFATTRIBS = DXFAttributes(base_class, acdb_entity, acdb_lwpolyline)
    MIN_DXF_VERSION_FOR_EXPORT = DXF2000

    def __init__(self, doc: 'Drawing' = None):
        super().__init__(doc)
        self.lwpoints = LWPolylinePoints()

    def _copy_data(self, entity: 'LWPolyline') -> None:
        """ Copy lwpoints. """
        entity.lwpoints = copy.deepcopy(self.lwpoints)

    def load_dxf_attribs(self, processor: SubclassProcessor = None) -> 'DXFNamespace':
        """
        Adds subclass processing for AcDbPolyline, requires previous base class and AcDbEntity processing by parent
        class.
        """
        dxf = super().load_dxf_attribs(processor)
        if processor:
            tags = processor.load_dxfattribs_into_namespace(dxf, acdb_lwpolyline)
            tags = self.load_vertices(tags)
            if len(tags) and not processor.r12:
                processor.log_unprocessed_tags(tags, subclass=acdb_lwpolyline.name)
        return dxf

    def load_vertices(self, tags: 'Tags') -> Tags:
        self.lwpoints, unprocessed_tags = LWPolylinePoints.from_tags(tags)
        return unprocessed_tags

    def preprocess_export(self, tagwriter: 'TagWriter') -> bool:
        # Returns True if entity should be exported
        # Do not export polylines without vertices
        return len(self.lwpoints) > 0

    def export_entity(self, tagwriter: 'TagWriter') -> None:
        """ Export entity specific data as DXF tags. """
        # base class export is done by parent class
        super().export_entity(tagwriter)
        # AcDbEntity export is done by parent class
        tagwriter.write_tag2(SUBCLASS_MARKER, acdb_lwpolyline.name)
        self.dxf.export_dxf_attribs(tagwriter, ['count', 'flags', 'const_width', 'elevation', 'thickness'])
        tagwriter.write_tags(Tags(self.lwpoints.dxftags()))
        self.dxf.export_dxf_attribs(tagwriter, 'extrusion')
        # xdata and embedded objects export will be done by parent class

    @property
    def closed(self) -> bool:
        """ ``True`` if polyline is closed. A closed polyline has a connection from the last vertex to the
        first vertex. (read/write)
         """
        return self.get_flag_state(LWPOLYLINE_CLOSED, name='flags')

    @closed.setter
    def closed(self, status: bool) -> None:
        self.set_flag_state(LWPOLYLINE_CLOSED, status, name='flags')

    # same as POLYLINE
    def close(self, state: bool = True) -> None:
        """ Compatibility interface to :class:`Polyline`. """
        self.closed = state

    @property
    def has_arc(self) -> bool:
        """ Returns ``True`` if LWPOLYLINE has an arc segment. """
        return any(bool(b) for x, y, s, e, b in self.lwpoints)

    def __len__(self) -> int:
        """ Returns count of polyline points. """
        return len(self.lwpoints)

    def __iter__(self) -> Iterable[LWPointType]:
        """ Returns iterable of tuples (x, y, start_width, end_width, bulge). """
        return iter(self.lwpoints)

    def __getitem__(self, index: int) -> LWPointType:
        """
        Returns point at position `index` as (x, y, start_width, end_width, bulge) tuple. start_width, end_width and
        bulge is ``0`` if not present, supports extended slicing. Point format is fixed as ``'xyseb'``.

        All coordinates in :ref:`OCS`.

        """
        return self.lwpoints[index]

    def __setitem__(self, index: int, value: Sequence[float]) -> None:
        """
        Set point at position `index` as (x, y, [start_width, [end_width, [bulge]]]) tuple. If start_width or end_width
        is ``0`` or left off the default value is used. If the bulge value is left off, bulge is ``0`` by default
        (straight line). Does NOT support extend slicing. Point format is fixed as ``'xyseb'``.

        All coordinates in :ref:`OCS`.

        Args:
            index: point index
            value: point value as (x, y, [start_width, [end_width, [bulge]]]) tuple

        """
        self.lwpoints[index] = compile_array(value)

    def __delitem__(self, index: int) -> None:
        """ Delete point at position `index`, supports extended slicing. """
        del self.lwpoints[index]

    def vertices(self) -> Iterable[Tuple[float, float]]:
        """
        Returns iterable of all polyline points as (x, y) tuples in :ref:`OCS` (:attr:`dxf.elevation` is the z-axis value).

        """
        for point in self:
            yield point[0], point[1]

    def vertices_in_wcs(self) -> Iterable['Vertex']:
        """
        Returns iterable of all polyline points as Vector(x, y, z) in :ref:`WCS`.

        """
        ocs = self.ocs()
        elevation = self.get_dxf_attrib('elevation', default=0.)
        for x, y in self.vertices():
            yield ocs.to_wcs((x, y, elevation))

    def vertices_in_ocs(self) -> Iterable['Vertex']:
        """
        Returns iterable of all polyline points as Vector(x, y, z) in :ref:`OCS`.

        """
        elevation = self.get_dxf_attrib('elevation', default=0.)
        for x, y in self.vertices():
            yield Vector(x, y, elevation)

    def append(self, point: Sequence[float], format: str = DEFAULT_FORMAT) -> None:
        """
        Append `point` to polyline, `format`` specifies a user defined point format.

        All coordinates in :ref:`OCS`.

        Args:
            point: (x, y, [start_width, [end_width, [bulge]]]) tuple
            format: format string, default is ``'xyseb'``, see: `format codes`_

        """
        self.lwpoints.append(point, format=format)

    def insert(self, pos: int, point: Sequence[float], format: str = DEFAULT_FORMAT) -> None:
        """
        Insert new point in front of positions `pos`, `format` specifies a user defined point format.

        All coordinates in :ref:`OCS`.

        Args:
            pos: insert position
            point: point data
            format: format string, default is 'xyseb', see: `format codes`_

        """
        data = compile_array(point, format=format)
        self.lwpoints.insert(pos, data)

    def append_points(self, points: Iterable[Sequence[float]], format: str = DEFAULT_FORMAT) -> None:
        """
        Append new `points` to polyline, `format` specifies a user defined point format.

        All coordinates in :ref:`OCS`.

        Args:
            points: iterable of point, point is (x, y, [start_width, [end_width, [bulge]]]) tuple
            format: format string, default is ``'xyseb'``, see: `format codes`_

        """
        for point in points:
            self.lwpoints.append(point, format=format)

    @contextmanager
    def points(self, format: str = DEFAULT_FORMAT) -> List[Sequence[float]]:
        """
        Context manager for polyline points. Returns a standard Python list of points,
        according to the format string.

        All coordinates in :ref:`OCS`.

        Args:
            format: format string, see `format codes`_

        """
        points = self.get_points(format=format)
        yield points
        self.set_points(points, format=format)

    def get_points(self, format: str = DEFAULT_FORMAT) -> List[Sequence[float]]:
        """
        Returns all points as list of tuples, format specifies a user defined point format.

        All points in :ref:`OCS` as (x, y) tuples (:attr:`dxf.elevation` is the z-axis value).

        Args:
            format: format string, default is ``'xyseb'``, see `format codes`_

        """
        return [format_point(p, format=format) for p in self.lwpoints]

    def set_points(self, points: Iterable[Sequence[float]], format: str = DEFAULT_FORMAT) -> None:
        """
        Remove all points and append new `points`.

        All coordinates in :ref:`OCS`.

        Args:
            points: iterable of point, point is (x, y, [start_width, [end_width, [bulge]]]) tuple
            format: format string, default is ``'xyseb'``, see `format codes`_

        """
        self.lwpoints.clear()
        self.append_points(points, format=format)

    def clear(self) -> None:
        """ Remove all points. """
        self.lwpoints.clear()

    def transform_to_wcs(self, ucs: 'UCS') -> 'LWPolyline':
        """ Transform LWPOLYLINE entity from local :class:`~ezdxf.math.UCS` coordinates to :ref:`WCS` coordinates.

        .. versionadded:: 0.11

        """
        extrusion = self.dxf.extrusion
        vertices = list(ucs.ocs_points_to_ocs(self.vertices_in_ocs(), extrusion=extrusion))
        lwpoints = [(v[0], v[1], p[2], p[3], p[4]) for v, p in zip(vertices, self.lwpoints)]
        self.set_points(lwpoints)
        self.dxf.extrusion = ucs.direction_to_wcs(extrusion)
        # all new OCS vertices must have the same z-axis, which is the elevation of the polyline
        self.dxf.elevation = vertices[0][2]
        return self

    def virtual_entities(self) -> Iterable[Union['Line', 'Arc']]:
        """
        Yields 'virtual' parts of LWPOLYLINE as LINE or ARC entities.

        This entities are located at the original positions, but are not stored in the entity database, have no handle
        and are not assigned to any layout.

        .. versionadded:: 0.12

        """
        return virtual_lwpolyline_entities(self)

    def explode(self, target_layout: 'BaseLayout' = None) -> 'EntityQuery':
        """
        Explode parts of LWPOLYLINE as LINE or ARC entities into target layout, if target layout is ``None``,
        the target layout is the layout of the LWPOLYLINE.

        Returns an :class:`~ezdxf.query.EntityQuery` container with all DXF parts.

        Args:
            target_layout: target layout for DXF parts, ``None`` for same layout as source entity.

        .. versionadded:: 0.12

        """
        return explode_entity(self, target_layout)


class LWPolylinePoints(VertexArray):
    __slots__ = ('values',)
    VERTEX_CODE = 10
    START_WIDTH_CODE = 40
    END_WIDTH_CODE = 41
    BULGE_CODE = 42
    VERTEX_SIZE = 5

    @classmethod
    def from_tags(cls, tags: Tags) -> Tuple['LWPolylinePoints', Tags]:
        """ Setup point array from tags. """

        def get_vertex() -> LWPointType:
            point.append(attribs.get(cls.START_WIDTH_CODE, 0))
            point.append(attribs.get(cls.END_WIDTH_CODE, 0))
            point.append(attribs.get(cls.BULGE_CODE, 0))
            return tuple(point)

        unprocessed_tags = Tags()
        data = []
        point = None
        attribs = {}
        for tag in tags:
            if tag.code in LWPOINTCODES:
                if tag.code == 10:
                    if point is not None:
                        data.extend(get_vertex())
                    point = list(tag.value[0:2])  # just use x, y coordinates, z is invalid but you never know!
                    attribs = {}
                else:
                    attribs[tag.code] = tag.value
            else:
                unprocessed_tags.append(tag)
        if point is not None:
            data.extend(get_vertex())
        return cls(data=data), unprocessed_tags

    def append(self, point: Sequence[float], format: str = DEFAULT_FORMAT) -> None:
        super().append(compile_array(point, format=format))

    def dxftags(self) -> Iterable[DXFTag]:
        for point in self:
            x, y, start_width, end_width, bulge = point
            yield DXFVertex(self.VERTEX_CODE, (x, y))
            if start_width or end_width:
                # export always start- and end width together,
                # required for BricsCAD but not AutoCAD!
                yield DXFTag(self.START_WIDTH_CODE, start_width)
                yield DXFTag(self.END_WIDTH_CODE, end_width)
            if bulge:
                yield DXFTag(self.BULGE_CODE, bulge)


def format_point(point: Sequence[float], format: str = 'xyseb') -> Sequence[float]:
    """
    Reformat point components.

    Format codes:

        - ``x`` = x-coordinate
        - ``y`` = y-coordinate
        - ``s`` = start width
        - ``e`` = end width
        - ``b`` = bulge value
        - ``v`` = (x, y) as tuple

    Args:
        point: list or tuple of (x, y, start_width, end_width, bulge)
        format: format string, default is 'xyseb'

    Returns:
        Sequence[float]: tuple of selected components

    """
    x, y, s, e, b = point
    v = (x, y)
    vars = locals()
    return tuple(vars[code] for code in format.lower() if code in FORMAT_CODES)


def compile_array(data: Sequence[float], format='xyseb') -> array.array:
    """
    Gather point components from input data.

    Format codes:

        - ``x`` = x-coordinate
        - ``y`` = y-coordinate
        - ``s`` = start width
        - ``e`` = end width
        - ``b`` = bulge value
        - ``v`` = (x, y [,z]) tuple (z-axis is ignored)

    Args:
        data: list or tuple of point components
        format: format string, default is 'xyseb'

    Returns:
        array.array: array.array('d', (x, y, start_width, end_width, bulge))

    """
    a = array.array('d', (0., 0., 0., 0., 0.))
    format = [code for code in format.lower() if code in FORMAT_CODES]
    for code, value in zip(format, data):
        if code not in FORMAT_CODES:
            continue
        if code == 'v':
            value = cast('Vertex', value)
            a[0] = value[0]
            a[1] = value[1]
        else:
            a['xyseb'.index(code)] = value
    return a
