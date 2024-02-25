import bpy
from bpy.types import NodeTree
from bpy.types import Operator
from bpy.types import PropertyGroup
from bpy.props import PointerProperty
from bpy.props import FloatProperty
from bpy.props import IntProperty
from bpy.props import BoolProperty
import blf
import gpu
from gpu_extras.batch import batch_for_shader
import os
# import math
import re
from PIL import ImageFont

bl_info = {
    "name": "Document Viewer",
    "author": "Spectral Vectors",
    "version": (0, 0, 2),
    "blender": (2, 80, 0),
    "location": "Document Viewer Editor",
    "description": "Read and render Markdown files in a custom Editor",
    "warning": "",
    "doc_url": "https://github.com/SpectralVectors/DocViewer",
    "category": "Interface",
}

# Grabbing Blender's Text Editor background and text colors
# To create the Blender theme
blender_theme = bpy.context.preferences.themes['Default']
back = blender_theme.text_editor.space.back
text = blender_theme.text_editor.space.text

# Dict of available themes, Key is theme name
# Value is an 8d FloatVector, composed of 2 4d FloatVectors
themes = {
    # Format is Background Color, then Text Color, both in RGBA
    # (bg-r, bg-g, bg-b, bg-a, text-r, text-g, text-b, text-a)
    #
    # Light: White BG, Black Text
    # Dark: Dark Grey BG, Light Grey Text
    # Blender: Dark Grey BG, Off White Text
    # Paperback: Yellowed BG, Dark Grey Text
    # C64: Dark Blue BG, Light Blue Text
    'light': (0.8, 0.8, 0.8, 1, 0, 0, 0, 1),
    'dark': (0.1, 0.1, 0.1, 1, 0.6, 0.6, 0.6, 1),
    'blender': (*back, 1, *text, 1),
    'paperback': (0.7, 0.7, 0.6, 1, 0.25, 0.25, 0.25, 1),
    'c64': (0, 0, 0.66, 1, 0, 0.53, 1, 1)
}

# Set the current theme
theme = themes['light']

# Separate the theme into 2 RGBA colors
bg_color = theme[:4]
text_color = theme[4:]


# Function to calculate screen size of rendered characters
def get_pil_text_size(text, font_size, font_name):
    font = ImageFont.truetype(font_name, font_size)
    size = font.getbbox(text)
    return size


# Function to set up Background drawing
def draw_bg():
    window = bpy.context.window
    for area in window.screen.areas:
        if area.ui_type == 'DocumentViewer':
            width = area.width
            height = area.height

# Here we define the positions of the vertices of the background
    bg_vertices = (
        (0, 0),  # Bottom Left
        (width, 0),  # Bottom Right
        (0, height),  # Top Left
        (width, height)  # Top Right
    )

# This defines the order in which we connect the vertices,
# creating two triangles
    indices = (
        (0, 1, 2),  # _ \
        (2, 1, 3)  # \ |
    )

# Creating the shader to fill in the faces we created above
    bg_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(
        bg_shader,
        'TRIS',
        {"pos": bg_vertices},
        indices=indices
    )
# This is where we define the background color
    bg_shader.uniform_float(
        "color",
        bg_color
    )
    batch.draw(bg_shader)


# Format the text before passing it onto the draw function
def format_text(context, text_lines, fonts):
    props = context.scene.docview_props
    base_size = props.base_size
    regular_path = props.regular_path

    draw_lines = {}  # '0': (sub_line, text, font_id, size, color, position)
    sub_lines = {}  # '0_0': (char, font_id, size, color, position, start, end)

    regular = fonts[0]
    italic = fonts[1]
    bold = fonts[2]

    offset_x = base_size / 2
    offset_y = base_size + (base_size / 2) + (base_size / 4)

    for line_index, line in enumerate(text_lines):

        # Shorten line.startswith to first: 1st character in line
        first = line.startswith

        # Define lines types
        header = first('#')
        bullet = line.lstrip().startswith('-')
        italicized = first('_') or first('*')
        italicized = italicized and not first('**') or first('__')
        bolded = first('__') or first('**')

        # Format Headers
        if header:
            # Header 1
            if first('# '):
                text_size = base_size * 2 + (base_size / 6)
                font_id = bold
            # Header 2
            elif first('## '):
                text_size = base_size * 2
                font_id = bold
            # Header 3
            elif first('### '):
                text_size = base_size + (base_size / 2) + (base_size / 3)
                font_id = bold
            # Header 4
            elif first('#### '):
                text_size = base_size + (base_size / 2) + (base_size / 6)
            # Header 5
            elif first('##### '):
                text_size = base_size + (base_size / 3)
            # Header 6
            elif first('####### '):
                text_size = base_size + (base_size / 8)
            line = line.replace('#', '')
            offset_y += text_size

        # Format Italic
        elif italicized:
            text_size = base_size
            font_id = italic
            line = line.replace('_', '').replace('*', '')

        # Format Bold
        elif bolded:
            text_size = base_size
            font_id = bold
            line = line.replace('__', '').replace('**', '')

        # Format Bullets
        elif bullet:
            if first('-'):
                b1 = int(base_size / 6)
                text_size = base_size
                font_id = regular
                line = line.lstrip().replace('-', '◦')
                line = f"{' '*b1}{line}"
            elif first('  -'):
                b2 = int(base_size / 3)
                text_size = base_size
                font_id = regular
                line = line.lstrip().replace('-', '•')
                line = f"{' '*b2}{line}"
            elif first('    -'):
                b3 = int(base_size / 2)
                text_size = base_size
                font_id = regular
                line = line.lstrip().replace('-', '∙')
                line = f"{' '*b3}{line}"

        # Format Regular Text
        else:
            text_size = base_size
            font_id = regular

        # Determine X, Y offsets for drawing lines
        if text_size == base_size:
            offset_y += base_size / 6
            offset_x = base_size + (base_size / 6)
        else:
            offset_x = base_size / 2

        # Format Links
        sub_line = False
        regex = r'\[([^\[]+)]\(\s*(http[s]?:\/\/.+)\s*\)'
        brackets = ['[', ']', '(', ')']

        for name, url in re.findall(regex, line):
            sub_line = True
            for brace in brackets:
                line = line.replace(brace, '')
            line = line.replace(url, '')

            link = re.search(name, line)
            start = link.start()
            start = start - 1
            end = link.end()

        # For sub-line formatting
        # e.g. links, single words in italic or bold
        if sub_line:
            for i, char in enumerate(line):
                if i in range(start, end):
                    text_color = (0, 0, 1, 1)
                else:
                    text_color = theme[4:]
                i = str(i)
                fli = f'{line_index}_{i}'
                sub_lines[fli] = (
                    char,
                    font_id,
                    text_size,
                    text_color,
                    offset_x,
                    offset_y
                )
                offset_x += get_pil_text_size(char, text_size, regular_path)[2]

        # For line level formatting
        # e.g. headers, regular text, full lines in italic or bold
        text_color = theme[4:]
        line_index = str(line_index)
        draw_lines[line_index] = (
            sub_line,
            line,
            font_id,
            text_size,
            text_color,
            offset_x,
            offset_y
        )

        offset_y += base_size + (base_size / 6)

    return draw_lines, sub_lines, offset_x, offset_y


# Function to setup Text drawing
def draw_text(self, context, draw_lines, sub_lines, offset_x, offset_y):
    if context.area.ui_type == 'DocumentViewer':
        x = context.region.x
        y = context.region.y
        view = context.region.view2d
        scroll = view.region_to_view(x, y)
        scroll_factor = 5

        lines = draw_lines
        sub = sub_lines

        for line_text in lines:
            if lines[line_text][0]:  # if sub_line is True
                for i in sub:
                    char = sub[i][0]
                    font_id = sub[i][1]
                    text_size = sub[i][2]
                    text_color = sub[i][3]
                    offset_x = sub[i][4]
                    offset_y = sub[i][5]

                    if scroll[0] > 0:
                        offset_x -= scroll[0] / scroll_factor
                    if scroll[1] < 0:
                        offset_y += scroll[1] / scroll_factor

    #                offset_x += context.scene.offset_x
    #                offset_y += context.scene.offset_y

                    blf.size(font_id, text_size)
                    blf.position(
                        font_id,
                        offset_x,
                        context.area.height - offset_y,
                        0
                    )
                    blf.color(font_id, *text_color)
                    blf.draw(font_id, char)
            else:
                line = lines[line_text][1]
                font_id = lines[line_text][2]
                text_size = lines[line_text][3]
                text_color = lines[line_text][4]
                offset_x = lines[line_text][5]
                offset_y = lines[line_text][6]

                if scroll[0] > 0:
                    offset_x -= scroll[0] / scroll_factor
                if scroll[1] < 0:
                    offset_y += scroll[1] / scroll_factor

    #            offset_x += context.scene.offset_x
    #            offset_y += context.scene.offset_y

                blf.size(font_id, text_size)
                blf.position(
                    font_id,
                    offset_x,
                    context.area.height - offset_y,
                    0
                )
                blf.color(font_id, *text_color)
                blf.draw(font_id, line)


class DocumentViewer(NodeTree):
    '''A Document Viewer'''
    bl_idname = 'DocumentViewer'
    bl_label = "Document Viewer"
    bl_icon = 'DOCUMENTS'


class DrawDocument(Operator):
    bl_idname = "docview.draw_document"
    bl_label = "Draw Document"

    def modal(self, context, event):
        remove_draw = context.space_data.draw_handler_remove
        if context.space_data is not None:
            if context.area.ui_type == 'DocumentViewer':
                context.area.tag_redraw()

                if event.type == 'ESC':
                    remove_draw(self.bg_handle, 'WINDOW')
                    remove_draw(self.text_handle, 'WINDOW')
                    return {'CANCELLED'}
#                if event.type == 'LEFTMOUSE':
#                    if event.value == 'PRESS':
#                        context.scene.base_size += 10

#                    x = event.mouse_prev_press_x - event.mouse_x
#                    y = event.mouse_prev_press_y - event.mouse_y
#                    context.scene.offset_x = x
#                    context.scene.offset_y = y
                return {'PASS_THROUGH'}  # do not block execution

        else:
            return {'PASS_THROUGH'}

    def invoke(self, context, event):
        props = context.scene.docview_props
        regular_path = props.regular_path
        italic_path = props.italic_path
        bold_path = props.bold_path
        internal = props.internal

        if context.area.ui_type == 'DocumentViewer':
            if os.path.exists(regular_path):
                regular = blf.load(regular_path)
            if os.path.exists(italic_path):
                italic = blf.load(italic_path)
            if os.path.exists(bold_path):
                bold = blf.load(bold_path)

            if regular is not None:
                font_id = regular
            else:
                font_id = regular = italic = bold = 0

            fonts = [regular, italic, bold]

            add_draw = context.space_data.draw_handler_add
            # remove_draw = context.space_data.draw_handler_remove
            add_modal = context.window_manager.modal_handler_add

            if not internal:
                # External File
                path = props.external_path
                with open(path) as file:
                    text = file.read()
                # To separate external text files into lines
                text_lines = text.split("\n")

            if internal:
                # Internal File
                for area in context.screen.areas:
                    if area.type == 'TEXT_EDITOR':
                        text_name = area.spaces[0].text.name
                        text = bpy.data.texts[text_name]
                        text_lines = [line.body for line in text.lines]

            draw_lines, sub_lines, offset_x, offset_y = format_text(context, text_lines, fonts)

            # Now we add the draw handler to the window
            self.bg_handle = add_draw(
                draw_bg,
                (),
                'WINDOW',
                'BACKDROP'
            )

            self.text_handle = add_draw(
                draw_text,
                (self, context, draw_lines, sub_lines, offset_x, offset_y),
                'WINDOW',
                'POST_PIXEL'  # BACKDROP or POST_PIXEL
            )

            add_modal(self)
            return {'RUNNING_MODAL'}
        else:
            return {'CANCELLED'}


class DocViewProps(PropertyGroup):
    base_size: IntProperty(default=24)
    offset_x: FloatProperty(default=0.0)
    offset_y: FloatProperty(default=0.0)
    internal: BoolProperty(default=False)

    folder = os.path.dirname(os.path.abspath(__file__))
    regular_path = os.path.join(folder, 'fonts/OpenSans-Regular.ttf')
    italic_path = os.path.join(folder, 'fonts/OpenSans-Italic.ttf')
    bold_path = os.path.join(folder, 'fonts/OpenSans-Bold.ttf')
    code_path = os.path.join(folder, 'fonts/CourierPrime-Regular.ttf')
    external_path = os.path.join(folder, 'sample.md')


classes = [
    DrawDocument,
    DocumentViewer,
    DocViewProps
]


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.docview_props = PointerProperty(type=DocViewProps)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Scene.docview_props


if __name__ == "__main__":
    register()
