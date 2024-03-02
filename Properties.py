import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty
from bpy.props import IntProperty
from bpy.props import BoolProperty
from bpy.props import EnumProperty
import os
from . Helpers import update_func


class DocViewProps(PropertyGroup):
    base_size: IntProperty(
        default=18,
        update=update_func
    )

    offset_x: FloatProperty(default=0.0)

    offset_y: FloatProperty(default=0.0)

    internal: BoolProperty(
        default=False,
        update=update_func
    )

    folder = os.path.dirname(os.path.abspath(__file__))
    regular_path = os.path.join(folder, 'fonts/OpenSans-Regular.ttf')
    italic_path = os.path.join(folder, 'fonts/OpenSans-Italic.ttf')
    bold_path = os.path.join(folder, 'fonts/OpenSans-Bold.ttf')
    code_path = os.path.join(folder, 'fonts/CourierPrime-Regular.ttf')
    external_path = os.path.join(folder, 'sample.md')

    # Grabbing Blender's Text Editor background and text colors
    # To create the Blender theme
    blender_theme = bpy.context.preferences.themes['Default']
    back = blender_theme.text_editor.space.back
    block = blender_theme.text_editor.line_numbers_background
    text = blender_theme.text_editor.space.text
    link = blender_theme.text_editor.cursor

    # Dict of Themes
    # Key: theme name
    # Value: list of 4 RGBA values
    # Format: Background, Block, Text and Link Colors
    # [R-bg,    G-bg,    B-bg,    A-bg,
    #  R-block, G-block, B-block, A-block,
    #  R-text,  G-text,  B-text,  A-text,
    #  R-link,  G-link,  B-link,  A-link]
    themes = {
        'light': [
            0.8, 0.8, 0.8, 1,       # bg: White
            0.6, 0.6, 0.6, 1,       # block: Grey
            0, 0, 0, 1,             # text: Black
            0, 0, 1, 1],            # link: Blue
        'dark': [
            0.1, 0.1, 0.1, 1,       # bg: Dark Grey
            0, 0, 0, 1,             # block: Black
            0.6, 0.6, 0.6, 1,       # text: Light Grey
            0, 0, 1, 1],            # link: Blue
        'blender': [
            *back, 1,                # bg: Grey
            *block, 1,               # block: Dark Grey
            *text, 1,                # text: Off White
            *link, 1],               # link: Light Blue
        'paperback': [
            0.7, 0.7, 0.6, 1,         # bg: Tan
            0.8, 0.8, 0.3, 1,         # block: Yellow
            0.2, 0.2, 0.2, 1,         # text: Grey
            0, 0, 0.7, 1],            # link: Dark Blue
        'c64': [
            0, 0, 0.66, 1,            # bg: Blue
            0, 0, 0.33, 1,            # block: Dark Blue
            0, 0.53, 1, 1,            # text: Light Blue
            0.8, 0.8, 0.8, 1],        # link: White
        'github': [
            0.051, 0.067, 0.09, 1,    # bg: Dark Blue Grey
            0.086, 0.106, 0.133, 1,   # block: Dark Grey
            0.902, 0.929, 0.953, 1,   # text: Off White
            0.184, 0.506, 0.969, 1],  # link: Blue
    }

    current_theme: EnumProperty(
        name='Theme',  # noqa
        items={
            ('light', 'Light', 'Black Text on White Background', 'OUTLINER_OB_LIGHT', 0),  # noqa
            ('dark', 'Dark', 'Light Grey Text on Dark Grey Background', 'LIGHT', 1),  # noqa
            ('blender', 'Blender', 'Off White Text on Grey Background', 'BLENDER', 2),  # noqa
            ('paperback', 'Paperback', 'Grey Text on Tan Background', 'HELP', 3),  # noqa
            ('c64', 'C64', 'Light Blue Text on Dark Blue Background', 'RESTRICT_VIEW_OFF', 4),  # noqa
            ('github', 'Github', 'White Text on Dark Blue Grey Background', 'NETWORK_DRIVE', 5),  # noqa
        },
        default='light',  # noqa
        update=update_func
    )
