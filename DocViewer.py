import bpy
from bpy.types import NodeTree
import blf
import gpu
from gpu_extras.batch import batch_for_shader
import os
# import math
import re

font_folder = os.path.expanduser('~\\Downloads\\Open_Sans\\static')

regular_path = os.path.join(font_folder, 'OpenSans-Regular.ttf')
italic_path = os.path.join(font_folder, 'OpenSans-Italic.ttf')
bold_path = os.path.join(font_folder, 'OpenSans-Bold.ttf')

internal = False

blender_theme = bpy.context.preferences.themes['Default']
back = blender_theme.text_editor.space.back
text = blender_theme.text_editor.space.text
themes = {
    # Format is bg color, then text, both in RGBA
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

theme = themes['c64']
bg_color = theme[:4]
text_color = theme[4:]


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


def draw_text(self, context, text_lines):
    #    if os.path.exists(regular_path):
    regular = blf.load(regular_path)
    #    if os.path.exists(italic_path):
    italic = blf.load(italic_path)
    #    if os.path.exists(bold_path):
    bold = blf.load(bold_path)

    if regular:
        font_id = regular
    else:
        font_id = 0

    x = context.region.x
    y = context.region.y
    view = context.region.view2d
    scroll = view.region_to_view(x, y)
    delta = scroll

    offset_y = 42
    if scroll[1] < 0:
        offset_y += (scroll[1] + delta[1]) / 5

    for line in text_lines:
        link_found = False

        # Format Links
        link_name = "[^\[]+"
        link_url = "http[s]?://.+"
        markup_regex = f'\[({link_name})]\(\s*({link_url})\s*\)'

        for name, url in re.findall(markup_regex, line):
            link_found = True
            line = re.sub(
                repl='',
                pattern=url,
                string=line
            ).replace('[', '').replace(']', '')
            line = line.replace('(', '').replace(')', '')
            # link = re.search(name, line)
            # start = link.start()
            # end = link.end()

        # Format Headers
        if line.startswith('#'):
            # Header 1
            if line.startswith('# '):
                text_size = 52
                font_id = bold
            # Header 2
            elif line.startswith('## '):
                text_size = 48
                font_id = bold
            # Header 3
            elif line.startswith('### '):
                text_size = 44
                font_id = bold
            # Header 4
            elif line.startswith('#### '):
                text_size = 40
            # Header 5
            elif line.startswith('##### '):
                text_size = 36
            # Header 6
            elif line.startswith('####### '):
                text_size = 32
            offset_y += text_size

        # Format Italic
        elif line.startswith('_'):
            line = line.replace('_', '')
            text_size = 24
            font_id = italic

        # Format Bullets
        elif line.startswith('-'):
            line = f'    {line}'
            text_size = 24
            font_id = regular
        elif line.startswith('  -'):
            text_size = 24
            font_id = regular
            line = f'        {line}'
        elif line.startswith('    -'):
            text_size = 24
            font_id = regular
            line = f'            {line}'

        # Format Regular Text
        else:
            text_size = 24
            font_id = regular

        if text_size == 24:
            offset_y += 4
            offset_x = 28
        else:
            offset_x = 12

        if scroll[0] > 0:
            offset_x -= scroll[0] / 5

        if link_found:
            text_color = (0, 0, 1, 1)
        else:
            text_color = theme[4:]

        blf.color(font_id, *text_color)
        blf.size(font_id, text_size)

        line = line.replace('#', '').replace('-', '•')

        blf.position(
            font_id,
            offset_x,
            context.area.height - offset_y,
            0
        )

        blf.draw(font_id, line)

        offset_y += 28


class DocumentViewer(NodeTree):
    '''A Document Viewer'''
    bl_idname = 'DocumentViewer'
    bl_label = "Document Viewer"
    bl_icon = 'DOCUMENTS'


class DrawDocument(bpy.types.Operator):
    bl_idname = "docview.draw_document"
    bl_label = "Draw Document"

    def modal(self, context, event):
        if context.space_data is not None:
            if context.area.ui_type == 'DocumentViewer':
                context.area.tag_redraw()
#                if event.type == 'MIDDLEMOUSE':
#                    if event.value == 'PRESS':
#                        x = event.mouse_prev_press_x - event.mouse_x
#                        y = event.mouse_prev_press_y - event.mouse_y
#                        print(x, y)
                return {'PASS_THROUGH'}  # do not block execution
        else:
            return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.area.ui_type == 'DocumentViewer':
            draw_handler_add = context.space_data.draw_handler_add
            draw_handler_remove = context.space_data.draw_handler_remove
            modal_handler_add = context.window_manager.modal_handler_add

            if not internal:
                # External File
                path = '~\\Documents\\sample.py'
                full_path = os.path.expanduser(path)

                with open(full_path) as file:
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

            # Now we add the draw handler to the window
            self.bg_handle = draw_handler_add(
                draw_bg,
                (),
                'WINDOW',
                'BACKDROP'
            )

            self.text_handle = draw_handler_add(
                draw_text,
                (self, context, text_lines),
                'WINDOW',
                'POST_PIXEL'  # BACKDROP or POST_PIXEL
            )

            modal_handler_add(self)
            return {'RUNNING_MODAL'}

        if event.type == 'ESC':
            draw_handler_remove(self.bg_handle, 'WINDOW')
            draw_handler_remove(self.text_handle, 'WINDOW')
            return {'FINISHED'}
        else:
            return {'CANCELLED'}


classes = [
    DrawDocument,
    DocumentViewer
]


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)


if __name__ == "__main__":
    register()


areas = bpy.context.screen.areas

try:
    area = [area for area in areas if area.ui_type == 'DocumentViewer'][0]
    with bpy.context.temp_override(area=area):
        bpy.ops.docview.draw_document("INVOKE_DEFAULT")
except IndexError:
    print('OH SHIT!')
