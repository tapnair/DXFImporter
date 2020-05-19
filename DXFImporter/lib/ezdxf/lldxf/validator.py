# Purpose: validate DXF tag structures
# Created: 03.01.2018
# Copyright (C) 2018, Manfred Moitzi
# License: MIT License
import logging
import io
from typing import TextIO, Iterable, List, Optional

from .const import DXFStructureError, DXFError, DXFValueError, DXFAppDataError, DXFXDataError
from .const import APP_DATA_MARKER, HEADER_VAR_MARKER, XDATA_MARKER
from .const import INVALID_LAYER_NAME_CHARACTERS, acad_release
from .tagger import ascii_tags_loader
from .types import is_embedded_object_marker, DXFTag, NONE_TAG
from ezdxf.tools.codepage import toencoding

logger = logging.getLogger('ezdxf')


class DXFInfo:
    def __init__(self):
        self.release = 'R12'
        self.version = 'AC1009'
        self.encoding = 'cp1252'
        self.handseed = '0'

    def set_header_var(self, name: str, value: str) -> int:
        if name == '$ACADVER':
            self.version = value
            self.release = acad_release.get(value, 'R12')
        elif name == '$DWGCODEPAGE':
            self.encoding = toencoding(value)
        elif name == '$HANDSEED':
            self.handseed = value
        else:
            return 0
        return 1


def dxf_info(stream: TextIO) -> DXFInfo:
    info = DXFInfo()
    tagger = ascii_tags_loader(stream)  # filters already comments
    if next(tagger) != (0, 'SECTION'):  # maybe a DXF structure error, handled by later processing
        return info
    if next(tagger) != (2, 'HEADER'):  # no leading HEADER section like DXF R12 with only ENTITIES section
        return info
    tag = NONE_TAG
    found = 0
    while tag != (0, 'ENDSEC'):  # until end of HEADER section
        tag = next(tagger)
        if tag.code != HEADER_VAR_MARKER:
            continue
        name = tag.value
        value = next(tagger).value
        found += info.set_header_var(name, value)
        if found > 2:  # all expected values collected
            break
    return info


def header_validator(tagger: Iterable[DXFTag]) -> Iterable[DXFTag]:
    """
    Checks the tag structure of the content of the header section.

    Do not feed (0, 'SECTION') (2, 'HEADER') and (0, 'ENDSEC') tags!

    Args:
        tagger: generator/iterator of low level tags or compiled tags

    Yields:
        DXFTag()

    Raises:
        DXFStructureError() -> invalid group codes
        DXFValueError() -> invalid header variable name
    """
    variable_name_tag = True
    for tag in tagger:
        if variable_name_tag:
            if tag.code != HEADER_VAR_MARKER:
                raise DXFStructureError('Invalid header variable tag ({0.code}, {0.value}).'.format(tag))
            if not tag.value.startswith('$'):
                raise DXFValueError('Invalid header variable name "{}", missing leading "$".'.format(tag.value))
            variable_name_tag = False
        else:
            variable_name_tag = True
        yield tag


def entity_structure_validator(tags: List[DXFTag]) -> Iterable[DXFTag]:
    """
    Checks for valid DXF entity tag structure.

    - APP DATA can not be nested and every opening tag (102, '{...') needs a closing tag (102, '}')
    - extended group codes (>=1000) allowed before XDATA section
    - XDATA section starts with (1001, APPID) and is always at the end of an entity
    - XDATA section: only group code >= 1000 is allowed
    - XDATA control strings (1002, '{') and (1002, '}') have to be balanced
    - embedded objects may follow XDATA

    XRECORD entities will not be checked.

    Args:
        tags: list of DXFTag()

    Yields:
        DXFTag()

    Raises:
        DXFAppDataError() for invalid APP DATA
        DXFXDataError() for invalid XDATA
    """
    assert isinstance(tags, list)
    dxftype = tags[0].value  # type: str
    handle = '???'
    app_data = False
    xdata = False
    xdata_list_level = 0
    app_data_closing_tag = '}'
    embedded_object = False
    for tag in tags:
        if tag.code == 5 and handle == '???':
            handle = tag.value

        if is_embedded_object_marker(tag):
            embedded_object = True

        if embedded_object:  # no further validation
            yield tag
            continue  # with next tag

        if xdata and not embedded_object:
            if tag.code < 1000:
                dxftype = tags[0].value
                raise DXFXDataError(
                    'Invalid XDATA structure in entity {}(#{}), only group code >=1000 allowed in XDATA section'.format(
                        dxftype, handle))
            if tag.code == 1002:
                value = tag.value
                if value == '{':
                    xdata_list_level += 1
                elif value == '}':
                    xdata_list_level -= 1
                else:
                    raise DXFXDataError(
                        'Invalid XDATA control string (1002, "{}") entity {}(#{}).'.format(value, dxftype, handle))
                if xdata_list_level < 0:  # more closing than opening tags
                    raise DXFXDataError(
                        'Invalid XDATA structure in entity {}(#{}), unbalanced list markers, missing  (1002, "{{").'.format(
                            dxftype, handle))

        if tag.code == APP_DATA_MARKER:
            value = tag.value
            if value.startswith('{'):
                if app_data:  # already in app data mode
                    raise DXFAppDataError(
                        'Invalid APP DATA structure in entity {}(#{}), APP DATA can not be nested.'.format(dxftype,
                                                                                                           handle))
                app_data = True
                # 'APPID}' is also a valid closing tag
                app_data_closing_tag = value[1:] + '}'
            elif value == '}' or value == app_data_closing_tag:
                if not app_data:
                    raise DXFAppDataError(
                        'Invalid APP DATA structure in entity {}(#{}), found (102, "}}") tag without opening tag.'.format(
                            dxftype, handle))
                app_data = False
                app_data_closing_tag = '}'
            else:
                if dxftype != 'XRECORD':  # group code 102 as non app data allowed in XRECORD
                    raise DXFAppDataError(
                        'Invalid APP DATA structure tag (102, "{}") in entity {}(#{}).'.format(value, dxftype, handle))

        # XDATA section starts with (1001, APPID) and is always at the end of an entity,
        # since AutoCAD 2018, embedded objects may follow XDATA
        if tag.code == XDATA_MARKER and xdata is False:
            xdata = True
            if app_data:
                raise DXFAppDataError(
                    'Invalid APP DATA structure in entity {}(#{}), missing closing tag (102, "}}").'.format(dxftype,
                                                                                                            handle))
        yield tag

    if app_data:
        raise DXFAppDataError(
            'Invalid APP DATA structure in entity {}(#{}), missing closing tag (102, "}}").'.format(dxftype, handle))

    if xdata:
        if xdata_list_level < 0:
            raise DXFXDataError(
                'Invalid XDATA structure in entity {}(#{}), unbalanced list markers, missing  (1002, "{{").'.format(
                    dxftype, handle))
        elif xdata_list_level > 0:
            raise DXFXDataError(
                'Invalid XDATA structure in entity {}(#{}), unbalanced list markers, missing  (1002, "}}").'.format(
                    dxftype, handle))


def is_dxf_file(filename: str) -> bool:
    """ Returns ``True`` if `filename` is an ASCII DXF file. """
    with io.open(filename, errors='ignore') as fp:
        return is_dxf_stream(fp)


def is_binary_dxf_file(filename: str) -> bool:
    """ Returns ``True`` if `filename` is a binary DXF file. """
    with open(filename, 'rb') as fp:
        sentinel = fp.read(22)
    return sentinel == b'AutoCAD Binary DXF\r\n\x1a\x00'


def is_dwg_file(filename: str) -> bool:
    """ Returns ``True`` if `filename` is a DWG file. """
    return dwg_version(filename) is not None


def dwg_version(filename: str) -> Optional[str]:
    """ Returns DWG version of `filename` as string or ``None``. """
    with open(str(filename), 'rb') as fp:
        try:
            version = fp.read(6).decode(errors='ignore')
        except IOError:
            return None
        if version not in acad_release:
            return None
        return version


def is_dxf_stream(stream: TextIO) -> bool:
    try:
        reader = ascii_tags_loader(stream)
    except DXFError:
        return False
    try:
        for tag in reader:
            # The common case for well formed DXF files
            if tag == (0, 'SECTION'):
                return True
            # Accept/Ignore tags in front of first SECTION - like AutoCAD and BricsCAD
            # But group code should be < 1000, until reality proofs otherwise
            if tag.code > 999:
                return False
    except DXFStructureError:
        pass
    return False


def is_valid_layer_name(name: str) -> bool:
    return not bool(INVALID_LAYER_NAME_CHARACTERS.intersection(set(name)))


is_valid_name = is_valid_layer_name


def is_adsk_special_layer(name: str) -> bool:
    return name.upper().startswith('*ADSK_')  # special Autodesk layers starts with invalid character *
