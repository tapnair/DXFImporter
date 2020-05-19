# Copyright (c) 2019-2020, Manfred Moitzi
# License: MIT-License
# Created: 2019-03-12
from typing import TYPE_CHECKING
import copy
from ezdxf.lldxf.const import SUBCLASS_MARKER, DXF2000
from ezdxf.lldxf.attributes import DXFAttributes, DefSubclass, DXFAttr
from ezdxf.lldxf.tags import Tags
from .dxfentity import base_class, SubclassProcessor
from .dxfobj import DXFObject
from .factory import register_entity

if TYPE_CHECKING:
    from ezdxf.eztypes import TagWriter, DXFNamespace, Drawing

__all__ = ['VisualStyle']

acdb_visualstyle = DefSubclass('AcDbVisualStyle', {
    'description': DXFAttr(2),
    'style_type': DXFAttr(70),
    # 0 = Flat
    # 1 = FlatWithEdges
    # 2 = Gouraud
    # 3 = GouraudWithEdges
    # 4 = 2dWireframe
    # 5 = Wireframe
    # 6 = Hidden
    # 7 = Basic
    # 8 = Realistic
    # 9 = Conceptual
    # 10 = Modeling
    # 11 = Dim
    # 12 = Brighten
    # 13 = Thicken
    # 14 = Linepattern
    # 15 = Facepattern
    # 16 = ColorChange
    # 20 = JitterOff
    # 21 = OverhangOff
    # 22 = EdgeColorOff
    # 23 = Shades of Gray
    # 24 = Sketchy
    # 25 = X-Ray
    # 26 = Shaded with edges
    # 27 = Shaded
    'face_lighting_model': DXFAttr(71),
    # 0 = Invisible
    # 1 = Visible
    # 2 = Phong
    # 3 = Gooch
    'face_lighting_quality': DXFAttr(72),
    # 0 = No lighting
    # 1 = Per face lighting
    # 2 = Per vertex lighting
    'face_color_mode': DXFAttr(73),
    # 0 = No color
    # 1 = Object color
    # 2 = Background color
    # 3 = Custom color
    # 4 = Mono color
    # 5 = Tinted
    # 6 = Desaturated
    'face_modifiers': DXFAttr(90),
    # 0 = No modifiers
    # 1 = Opacity
    # 2 = Specular
    'face_opacity_level': DXFAttr(40),
    'face_specular_level': DXFAttr(41),
    'color1': DXFAttr(62),
    'color2': DXFAttr(63),
    'face_style_mono_color': DXFAttr(421),
    'edge_style_model': DXFAttr(74),
    # 0 = No edges
    # 1 = Isolines
    # 2 = Facet edges
    'edge_style': DXFAttr(91),
    'edge_intersection_color': DXFAttr(64),
    'edge_obscured_color': DXFAttr(65),
    'edge_obscured_linetype': DXFAttr(75),
    'edge_intersection_linetype': DXFAttr(175),
    'edge_crease_angle': DXFAttr(42),
    'edge_modifiers': DXFAttr(92),
    'edge_color': DXFAttr(66),
    'edge_opacity_level': DXFAttr(43),
    'edge_width': DXFAttr(76),
    'edge_overhang': DXFAttr(77),
    'edge_jitter': DXFAttr(78),
    'edge_silhouette_color': DXFAttr(67),
    'edge_silhouette_width': DXFAttr(79),
    'edge_halo_gap': DXFAttr(170),
    'edge_isoline_count': DXFAttr(171),
    'edge_hide_precision': DXFAttr(290),  # flag
    'edge_style_apply': DXFAttr(174),  # flag
    'style_display_settings': DXFAttr(93),
    'brightness': DXFAttr(44),
    'shadow_type': DXFAttr(173),
    'unknown1': DXFAttr(177),  # required if xdata is present?
    'internal_use_only_flag': DXFAttr(291),  # visual style only use internal
    # Xdata must follow tag 291 (AutoCAD -> 'Xdata wasn't read' error)
    # 70: Xdata count (count of tag groups)
    # any code, value: multiple tags build a tag group
    # 176, 1: end of group marker
    # e.g. (291, 0) (70, 2) (62, 7) (420, 16777215) (176, 1) (90, 1) (176, 1)
})


# undocumented Xdata in DXF R2018
@register_entity
class VisualStyle(DXFObject):
    """ DXF VISUALSTYLE entity """
    DXFTYPE = 'VISUALSTYLE'
    DXFATTRIBS = DXFAttributes(base_class, acdb_visualstyle)
    MIN_DXF_VERSION_FOR_EXPORT = DXF2000  # official supported in R2007

    def __init__(self, doc: 'Drawing' = None):
        super().__init__(doc)
        self.acad_xdata = None  # to preserve AutoCAD xdata

    def _copy_data(self, entity: 'VisualStyle') -> None:
        """ Copy acad internal data. """
        entity.acad_xdata = copy.deepcopy(self.acad_xdata)

    def load_dxf_attribs(self, processor: SubclassProcessor = None) -> 'DXFNamespace':
        dxf = super().load_dxf_attribs(processor)
        if processor:
            self.acad_xdata = self.store_acad_xdata(processor.subclasses[1])
            processor.load_dxfattribs_into_namespace(dxf, acdb_visualstyle)
        return dxf

    @staticmethod
    def store_acad_xdata(tags: Tags):
        try:
            index = tags.tag_index(291)
        except IndexError:
            return None
        else:  # store tags after 291
            index += 1
            xdata = tags[index:]
            del tags[index:]  # remove xdata from subclass
            return xdata

    def export_entity(self, tagwriter: 'TagWriter') -> None:
        """ Export entity specific data as DXF tags. """
        # base class export is done by parent class
        super().export_entity(tagwriter)
        tagwriter.write_tag2(SUBCLASS_MARKER, acdb_visualstyle.name)
        self.dxf.export_dxf_attribs(tagwriter, [
            'description', 'style_type', 'face_lighting_model', 'face_lighting_quality', 'face_color_mode',
            'face_modifiers', 'face_opacity_level', 'face_specular_level', 'color1', 'color2',
            'face_style_mono_color',
            'edge_style_model', 'edge_style', 'edge_intersection_color', 'edge_obscured_color',
            'edge_obscured_linetype', 'edge_intersection_linetype', 'edge_crease_angle', 'edge_modifiers',
            'edge_color', 'edge_opacity_level', 'edge_width', 'edge_overhang', 'edge_jitter',
            'edge_silhouette_color',
            'edge_silhouette_width', 'edge_halo_gap', 'edge_isoline_count', 'edge_hide_precision',
            'edge_style_apply',
            'style_display_settings', 'brightness', 'shadow_type', 'unknown1', 'internal_use_only_flag',
        ])
        if self.acad_xdata:
            tagwriter.write_tags(self.acad_xdata)
