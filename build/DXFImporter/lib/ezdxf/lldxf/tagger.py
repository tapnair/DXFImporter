# Purpose: untrusted stream tag reader, tag compiler for trusted and untrusted sources
# Created: 10.04.2016
# Copyright (c) 2016-2020, Manfred Moitzi
# License: MIT License
from typing import Iterable, TextIO, Iterator
import struct
from .types import DXFTag, DXFVertex, DXFBinaryTag
from .types import BYTES, INT16, INT32, INT64, DOUBLE, BINARY_DATA
from .const import DXFStructureError, DXFVersionError
from .types import POINT_CODES, TYPE_TABLE, BINARY_DATA
from ezdxf.tools.codepage import toencoding


def internal_tag_compiler(s: str) -> Iterable[DXFTag]:
    """
    Yields DXFTag() from trusted (internal) source - relies on
    well formed and error free DXF format. Does not skip comment
    tags (group code == 999).

    Args:
        s: DXF unicode string, lines separated by universal line endings '\n'

    """
    assert isinstance(s, str)
    lines = s.split('\n')
    # split() creates an extra item, if s ends with '\n',
    # but lines[-1] can be an empty string!!!
    if s.endswith('\n'):
        lines.pop()
    pos = 0
    count = len(lines)
    while pos < count:
        code = int(lines[pos])
        value = lines[pos + 1]
        pos += 2
        if code in POINT_CODES:
            # next tag; y coordinate is mandatory - internal_tag_compiler relies on well formed DXF strings
            y = lines[pos + 1]
            pos += 2
            if pos < count:
                # next tag; z coordinate just for 3d points
                z_code = int(lines[pos])
                z = lines[pos + 1]
            else:  # if string s ends with a 2d point
                z_code, z = None, 0.
            if z_code == code + 20:  # 3d point
                pos += 2
                point = (float(value), float(y), float(z))
            else:  # 2d point
                point = (float(value), float(y))
            yield DXFVertex(code, point)  # 2d/3d point
        elif code in BINARY_DATA:
            yield DXFBinaryTag.from_string(code, value)
        else:  # single value tag: int, float or string
            yield DXFTag(code, TYPE_TABLE.get(code, str)(value))


def ascii_tags_loader(stream: TextIO, skip_comments: bool = True) -> Iterable[DXFTag]:
    """
    Yields :class:``DXFTag`` objects from a text `stream` (untrusted external source) and does not
    optimize coordinates. Comment tags (group code == 999) will be skipped if argument `skip_comments` is `True`.
    ``DXFTag.code`` is always an ``int`` and ``DXFTag.value`` is always an unicode string without a trailing '\n'.
    Works with file system streams and :class:`StringIO` streams, only required feature is the :meth:`readline`
    method.

    Args:
        stream: text stream
        skip_comments: skip comment tags (group code == 999) if `True`

    Raises:
        DXFStructureError: Found invalid group code.

    """
    line = 1
    while True:
        try:
            code = stream.readline()
            value = stream.readline()  # if throws EOFError -> DXFStructureError, but should be handled in higher layers
        except EOFError:
            return
        if code and value:  # StringIO(): empty strings indicates EOF
            try:
                code = int(code)
            except ValueError:
                raise DXFStructureError('Invalid group code "{}" at line {}.'.format(code, line))
            else:
                if code != 999 or skip_comments is False:
                    yield DXFTag(code, value.rstrip('\n'))
                line += 2
        else:
            return


def binary_tags_loader(data: bytes) -> Iterable[DXFTag]:
    """
    Yields :class:`DXFTag` or :class:`DXFBinaryTag` objects from binary DXF `data` (untrusted external source) and
    does not optimize coordinates.
    ``DXFTag.code`` is always an ``int`` and ``DXFTag.value`` is either an unicode string,``float``,
    ``int`` or ``bytes`` for binary chunks.

    Args:
        data: binary DXF data

    Raises:
        DXFStructureError: Not a binary DXF file
        DXFVersionError: Unsupported DXF version

    """
    if data[:22] != b'AutoCAD Binary DXF\r\n\x1a\x00':
        raise DXFStructureError('Not a binary DXF data structure.')

    def scan_params():
        dxfversion = 'AC1009'
        encoding = 'cp1252'
        try:
            # limit search to first 1024 bytes - an arbitrary number
            start = data.index(b'$ACADVER', 22, 1024) + 10  # start index for 1-byte group code
        except ValueError:
            pass  # HEADER var $ACADVER not present
        else:
            if data[start] != 65:  # not 'A' = 2-byte group code
                start += 1
            dxfversion = data[start:start + 6].decode()

        if dxfversion >= 'AC1021':
            encoding = 'utf8'
        else:
            try:
                # limit search to first 1024 bytes - an arbitrary number
                start = data.index(b'$DWGCODEPAGE', 22, 1024) + 14  # start index for 1-byte group code
            except ValueError:
                pass  # HEADER var $DWGCODEPAGE not present
            else:  # name schema is 'ANSI_xxxx'
                if data[start] != 65:  # not 'A' = 2-byte group code
                    start += 1
                end = start + 5
                while data[end] != 0:
                    end += 1
                codepage = data[start: end].decode()
                encoding = toencoding(codepage)

        return encoding, dxfversion

    encoding, dxfversion = scan_params()
    r12 = dxfversion <= 'AC1009'
    index = 22
    data_length = len(data)
    unpack = struct.unpack_from

    while index < data_length:
        # decode next group code
        code = data[index]
        if r12:
            if code == 255:  # extended data
                code = (data[index + 2] << 8) | data[index + 1]
                index += 3
            else:
                index += 1
        else:  # 2-byte group code
            code = (data[index + 1] << 8) | code
            index += 2

        # decode next value
        if code in BINARY_DATA:
            length = data[index]
            index += 1
            value = data[index:index + length]
            index += length
            yield DXFBinaryTag(code, value)
        else:
            if code in INT16:
                value = unpack('<h', data, offset=index)[0]
                index += 2
            elif code in DOUBLE:
                value = unpack('<d', data, offset=index)[0]
                index += 8
            elif code in INT32:
                value = unpack('<i', data, offset=index)[0]
                index += 4
            elif code in INT64:
                value = unpack('<q', data, offset=index)[0]
                index += 8
            elif code in BYTES:
                value = data[index]
                index += 1
            else:  # zero terminated string
                start_index = index
                end_index = data.index(b'\x00', start_index)
                s = data[start_index:end_index]
                index = end_index + 1
                value = s.decode(encoding, errors='ignore')
            yield DXFTag(code, value)


# invalid point codes if not part of a point started with 1010, 1011, 1012, 1013
INVALID_POINT_CODES = {1020, 1021, 1022, 1023, 1030, 1031, 1032, 1033}


def tag_compiler(tagger: Iterator[DXFTag]) -> Iterable[DXFTag]:
    """
    Compiles DXF tag values imported by ascii_tags_loader() into Python types.

    Raises DXFStructureError() for invalid float values and invalid coordinate values.

    Expects DXF coordinates written in x, y[, z] order, this is not required by the DXF standard, but nearly all CAD
    applications write DXF coordinates that (sane) way, there are older CAD applications (namely an older QCAD version)
    that write LINE coordinates in x1, x2, y1, y2 order, which does not work with tag_compiler(). For this cases use
    tag_reorder_layer() from the repair module to reorder the LINE coordinates::

        tag_compiler(tag_reorder_layer(ascii_tags_loader(stream)))

    Args:
        tagger: DXF tag generator e.g. ascii_tags_loader()

    Raises:
        DXFStructureError: Found invalid DXF tag or unexpected coordinate order.

    """

    def error_msg(tag):
        return 'Invalid tag (code={code}, value="{value}") near line: {line}.'.format(line=line, code=tag.code,
                                                                                      value=tag.value)

    undo_tag = None
    line = 0
    while True:
        try:
            if undo_tag is not None:
                x = undo_tag
                undo_tag = None
            else:
                x = next(tagger)
                line += 2
            code = x.code
            if code in POINT_CODES:
                y = next(tagger)  # y coordinate is mandatory
                line += 2
                if y.code != code + 10:  # like 20 for base x-code 10
                    raise DXFStructureError("Missing required y coordinate near line: {}.".format(line))
                z = next(tagger)  # z coordinate just for 3d points
                line += 2
                try:
                    if z.code == code + 20:  # it is a z-coordinate like (30, 0.0) for base x-code 10
                        point = (float(x.value), float(y.value), float(z.value))
                    else:
                        point = (float(x.value), float(y.value))
                        undo_tag = z
                except ValueError:  # internal exception
                    raise DXFStructureError('Invalid floating point values near line: {}.'.format(line))
                yield DXFVertex(code, point)
            elif code in BINARY_DATA:
                if isinstance(x, DXFBinaryTag):  # maybe pre compiled in low level tagger (binary DXF)
                    tag = x
                else:
                    try:
                        tag = DXFBinaryTag.from_string(code, x.value)
                    except ValueError:
                        raise DXFStructureError('Invalid binary data near line: {}.'.format(line))
                yield tag
            else:  # just a single tag
                try:
                    # fast path!
                    yield DXFTag(code, TYPE_TABLE.get(code, str)(x.value))
                except ValueError:  # internal exception
                    # slow path
                    if TYPE_TABLE.get(code, str) is int:  # ProE stores int values as floats :((
                        try:
                            yield DXFTag(code, int(float(x.value)))
                        except ValueError:
                            raise DXFStructureError(error_msg(x))
                    else:
                        raise DXFStructureError(error_msg(x))
        except StopIteration:
            return
