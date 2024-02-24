import bpy
from bpy.types import NodeTree
import blf
import gpu
from gpu_extras.batch import batch_for_shader
import os
# import math
import re
from PIL import ImageFont

# Parent folder for the fonts
font_folder = os.path.expanduser('~\\Downloads\\Open_Sans\\static')

# Path to each of 3 fonts: Regular, Italic & Bold
regular_path = os.path.join(font_folder, 'OpenSans-Regular.ttf')
italic_path = os.path.join(font_folder, 'OpenSans-Italic.ttf')
bold_path = os.path.join(font_folder, 'OpenSans-Bold.ttf')

# Use the active text file in the Text Editor
# or a file from a user defined path
internal = False

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

# def index_of_substring(string, sub_string):
#     word = range(len(string))
#     return [index for index in word if string.startswith(sub_string, index)]

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


#### Pass to draw:
# text, sub_line, font, text_size, text_color, text_position
def format_text(context, text_lines, fonts):
    draw_lines = {}  # '0': (sub_line, text, font_id, size, color, position)
    sub_lines = {}  # '0': (char, font_id, size, color, position, start, end)

    regular = fonts[0]
    italic = fonts[1]
    bold = fonts[2]

    offset_x = 12
    offset_y = 42

    for l, line in enumerate(text_lines):
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

        # Determine X, Y offsets for drawing lines
        if text_size == 24:
            offset_y += 4
            offset_x = 28
        else:
            offset_x = 12

        line = line.replace('#', '').replace('-', '•')

        # Format Links
        sub_line = False

        link_name = r"[^\[]+"
        link_url = r"http[s]?://.+"
        markup_regex = f'\[({link_name})]\(\s*({link_url})\s*\)'

        for name, url in re.findall(markup_regex, line):
            sub_line = True
            line = re.sub(
                repl='',
                pattern=url,
                string=line
            ).replace('[', '').replace(']', '')
            line = line.replace('(', '').replace(')', '')
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
                sub_lines[i] = (char, font_id, text_size, text_color, offset_x, offset_y)
                offset_x += get_pil_text_size(char, text_size, regular_path)[2]

        # For line level formatting
        # e.g. headers, regular text, full lines in italic or bold
        text_color = theme[4:]
        l = str(l)
        draw_lines[l] = (sub_line, line, font_id, text_size, text_color, offset_x, offset_y)

        offset_y += 28

    return draw_lines, sub_lines, offset_x, offset_y


# Function to setup Text drawing
def draw_text(self, context, draw_lines, sub_lines, offset_x, offset_y):

    x = context.region.x
    y = context.region.y
    view = context.region.view2d
    scroll = view.region_to_view(x, y)
    scroll_factor = 5
    
    lines = draw_lines  
    sub = sub_lines 

    for l in lines:  # (sub_line, line, font_id, text_size, text_color, offset_x, offset_y)
        if lines[l][0]:  # if sub_line is True
            for i in sub:  # (char, font_id, text_size, text_color, offset_x, offset_y)
                font_id = sub[i][1]
                text_size = sub[i][2]
                text_color = sub[i][3]
                offset_x = sub[i][4]
                offset_y = sub[i][5]
                char = sub[i][0]

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
            font_id = lines[l][2]
            text_size = lines[l][3]
            offset_x = lines[l][5]
            offset_y = lines[l][6]
            text_color = lines[l][4]
            line = lines[l][1]

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


class DrawDocument(bpy.types.Operator):
    bl_idname = "docview.draw_document"
    bl_label = "Draw Document"

    def modal(self, context, event):
        if context.space_data is not None:
            if context.area.ui_type == 'DocumentViewer':
                context.area.tag_redraw()
#                if event.type == 'MIDDLEMOUSE':
#                    if event.value == 'PRESS':
#                        context.scene.offset_y += 10
#                        print(context.scene.offset_y)
#                        x = event.mouse_prev_press_x - event.mouse_x
#                        y = event.mouse_prev_press_y - event.mouse_y
#                        print(x, y)
                return {'PASS_THROUGH'}  # do not block execution
        else:
            return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.area.ui_type == 'DocumentViewer':
            if os.path.exists(regular_path):
                regular = blf.load(regular_path)
            if os.path.exists(italic_path):
                italic = blf.load(italic_path)
            if os.path.exists(bold_path):
                bold = blf.load(bold_path)

            if regular:
                font_id = regular
            else:
                font_id = regular = italic = bold = 0
                
            fonts = [regular, italic, bold]

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

            draw_lines = format_text(context, text_lines, fonts)[0]
            sub_lines = format_text(context, text_lines, fonts)[1]
            offset_x = format_text(context, text_lines, fonts)[2]
            offset_y = format_text(context, text_lines, fonts)[3]

            # Now we add the draw handler to the window
            self.bg_handle = draw_handler_add(
                draw_bg,
                (),
                'WINDOW',
                'BACKDROP'
            )

            self.text_handle = draw_handler_add(
                draw_text,
                (self, context, draw_lines, sub_lines, offset_x, offset_y),
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
        
    bpy.types.Scene.offset_x = bpy.props.FloatProperty(0.0)
    bpy.types.Scene.offset_y = bpy.props.FloatProperty(0.0)


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
