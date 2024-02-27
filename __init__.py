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
    "version": (0, 1, 1),
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
    'light': (0.8, 0.8, 0.8, 1, 0, 0, 0, 1),  # BG White, Text Black
    'dark': (0.1, 0.1, 0.1, 1, 0.6, 0.6, 0.6, 1),  # BG Grey, Text Grey
    'blender': (*back, 1, *text, 1),  # BG Grey, Text Off White
    'paperback': (0.7, 0.7, 0.6, 1, 0.25, 0.25, 0.25, 1),  # BG Tan, Text Grey
    'c64': (0, 0, 0.66, 1, 0, 0.53, 1, 1)  # Dark Blue BG, Light Blue Text
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


def draw_image(self, context, images):
    if context.area.ui_type == 'DocumentViewer':
        x = context.region.x
        y = context.region.y
        view = context.region.view2d
        scroll = view.region_to_view(x, y)
        scroll_factor = 5

    for image in images:
        image = images[image][0]
        texture = images[image][1]
        width = images[image][2]
        height = images[image][3]
        offset_x = images[image][4]
        offset_y = images[image][5]

        if scroll[0] > 0:
            offset_x -= scroll[0] / scroll_factor
        if scroll[1] < 0:
            offset_y -= scroll[1] / scroll_factor

        try:
            shader = gpu.shader.from_builtin('IMAGE')
        except NameError:
            shader = gpu.shader.from_builtin('2D_IMAGE')

        batch = batch_for_shader(
            shader, 'TRI_FAN',
            {
                "pos": (
                    (offset_x, offset_y),
                    (offset_x + width, offset_y),
                    (offset_x + width, offset_y + height),
                    (offset_x, offset_y + height)
                ),
                "texCoord": (
                    (0, 0),
                    (1, 0),
                    (1, 1),
                    (0, 1)
                ),
            },
        )
        shader.bind()
        shader.uniform_sampler("image", texture)
        batch.draw(shader)


# Format the text before passing it onto the draw function
def format_text(context, text_lines, fonts):
    props = context.scene.docview_props
    regular_path = props.regular_path
    base_size = props.base_size

    # Derive all scale elements from the base font size
    double = base_size * 2
    half = base_size / 2
    third = base_size / 3
    quarter = base_size / 4
    sixth = base_size / 6
    eigth = base_size / 8

    draw_lines = {}  # '0': (sub_line, text, font_id, size, color, position)
    sub_lines = {}  # '0_0': (char, font_id, size, color, position, start, end)
    images = {}

    regular = fonts[0]
    italic = fonts[1]
    bold = fonts[2]

    offset_x = half
    offset_y = base_size + half + quarter

    for line_index, line in enumerate(text_lines):

        # Shorten line.startswith to first: 1st character in line
        first = line.startswith

        # Define line types
        header = first('#')
        bullet = line.lstrip().startswith('-')
        italicized = first('_') or first('*')
        italicized = italicized and not first('**') or first('__')
        bolded = first('__') or first('**')

        # Format Headers
        if header:
            # Header 1
            if first('# '):
                text_size = double + sixth
                font_id = bold
            # Header 2
            elif first('## '):
                text_size = double
                font_id = bold
            # Header 3
            elif first('### '):
                text_size = base_size + half + third
                font_id = bold
            # Header 4
            elif first('#### '):
                text_size = base_size + half + sixth
            # Header 5
            elif first('##### '):
                text_size = base_size + third
            # Header 6
            elif first('####### '):
                text_size = base_size + eigth
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
                b1 = int(sixth)
                text_size = base_size
                font_id = regular
                line = line.lstrip().replace('-', '◦')
                line = f"{' '*b1}{line}"
            elif first('  -'):
                b2 = int(third)
                text_size = base_size
                font_id = regular
                line = line.lstrip().replace('-', '•')
                line = f"{' '*b2}{line}"
            elif first('    -'):
                b3 = int(half)
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
            offset_y += sixth
            offset_x = base_size + sixth
        else:
            offset_x = half

        # Format Links and Images
        sub_line = False
        image_line = False
        regex = r'(?:\[(?P<name>.*?)\])\((?P<url>.*?)\)'  # r'\[([^\[]+)]\(\s*(http[s]?:\/\/.+)\s*\)' # noqa E501
        brackets = ['[', ']', '(', ')']
        extensions = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']

        for name, url in re.findall(regex, line):
            sub_line = True
            # Detect Images
            for ext in extensions:
                if url.lower().endswith(ext):
                    url = url.replace('/', '\\')
                    # line.replace(name, '')
                    folder = props.folder
                    filepath = f'{folder}{url}'
                    bpy.ops.image.open(filepath=filepath)
                    bpy.ops.image.pack()

                    image_name = bpy.path.basename(filepath)
                    image = bpy.data.images[image_name]
                    texture = gpu.texture.from_image(image)

                    width = image.size[0] * (base_size / 24)
                    height = image.size[1] * (base_size / 24)
                    offset_x = offset_x * (base_size / 24)
                    offset_y = offset_y * (base_size / 24)
                    offset_y += height * 7
                    images[image] = (
                        image,     # 0 : blender image data block
                        texture,   # 1 : gpu texture from image
                        width,     # 2 : image width
                        height,    # 3 : image height
                        offset_x,  # 4 : image x start position
                        offset_y,  # 5 : image y start position
                    )
                    image_line = True
                    line = ''
                    offset_y -= (height * 6) + base_size

            # Common formatting for links and images
            for brace in brackets:
                line = line.replace(brace, '')
            line = line.replace(url, '')

            link = re.search(name, line)
            start = link.start()
            start = start - 1
            end = link.end()

        # For sub-line formatting
        # e.g. links, images
        if sub_line:
            for sub_index, char in enumerate(line):
                if sub_index in range(start, end):
                    text_color = (0, 0, 1, 1)
                else:
                    text_color = theme[4:]
                sub_index = str(sub_index)
                sub_index = f'{line_index}_{sub_index}'
                sub_lines[sub_index] = (
                    char,        # 0 : single character from line
                    font_id,     # 1 : blf loaded font file
                    text_size,   # 2 : font size of the text
                    text_color,  # 3 : color of the text
                    offset_x,    # 4 : horizontal offset of each character
                    offset_y,    # 5 : vertical offset of the line
                )
                offset_x += get_pil_text_size(char, text_size, regular_path)[2]

        # For line level formatting
        # e.g. headers, regular text, full lines in italic or bold
        text_color = theme[4:]
        line_index = str(line_index)
        draw_lines[line_index] = (
            line,        # 0 : the text of the line
            font_id,     # 1 : blf loaded font file
            text_size,   # 2 : font size of the text
            text_color,  # 3 : color of the text
            offset_x,    # 4 : horizontal offset of the line
            offset_y,    # 5 : vertical offset of the line
            sub_line,    # 6 : boolean, true if a link is found
            image_line   # 7 : boolean, true if an image is found
        )
        offset_y += base_size + sixth

    return draw_lines, sub_lines, offset_x, offset_y, images


# Function to setup Text drawing
def draw_text(
        self,
        context,
        draw_lines,
        sub_lines,
        offset_x,
        offset_y):
    if context.area.ui_type == 'DocumentViewer':
        x = context.region.x
        y = context.region.y
        view = context.region.view2d
        scroll = view.region_to_view(x, y)
        scroll_factor = 5

        lines = draw_lines
        sub = sub_lines

        for line_text in lines:
            if lines[line_text][6] and not lines[line_text][7]:  # if sub_line
                for sub_index in sub:
                    char = sub[sub_index][0]
                    font_id = sub[sub_index][1]
                    text_size = sub[sub_index][2]
                    text_color = sub[sub_index][3]
                    offset_x = sub[sub_index][4]
                    offset_y = sub[sub_index][5]

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
                line = lines[line_text][0]
                font_id = lines[line_text][1]
                text_size = lines[line_text][2]
                text_color = lines[line_text][3]
                offset_x = lines[line_text][4]
                offset_y = lines[line_text][5]

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


def update_func(self, context):
    bpy.ops.docview.draw_document('INVOKE_DEFAULT')


class DocumentViewer(NodeTree):
    '''A Document Viewer'''
    bl_idname = 'DocumentViewer'
    bl_label = "Document Viewer"
    bl_icon = 'DOCUMENTS'


class DrawDocument(Operator):
    bl_idname = "docview.draw_document"
    bl_label = "Draw Document"

    def remove_handle(self):
        try:
            try:
                bg_handle = bpy.app.driver_namespace['bg_handle']
                text_handle = bpy.app.driver_namespace['text_handle']
                image_handle = bpy.app.driver_namespace['image_handle']

                space = bpy.types.SpaceNodeEditor
                space.draw_handler_remove(bg_handle, 'WINDOW')
                space.draw_handler_remove(text_handle, 'WINDOW')
                space.draw_handler_remove(image_handle, 'WINDOW')
                return {'FINISHED'}
            except AttributeError:
                print('No draw handlers found!')
        except ValueError:
            print('Null pointer!')

    def modal(self, context, event):
        # draw_handlers = bpy.app.driver_namespace
        # remove_draw = context.space_data.draw_handler_remove
        if context.space_data is not None:
            if context.area.ui_type == 'DocumentViewer':
                context.area.tag_redraw()

                if event.type == 'ESC':
                    self.remove_handle()
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
                font_id = regular = italic = bold = 0 # noqa F841

            fonts = [regular, italic, bold]

            add_draw = bpy.types.SpaceNodeEditor.draw_handler_add
            # remove_draw = bpy.types.SpaceNodeEditor.draw_handler_remove
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
                try:
                    text = bpy.data.texts[0]
                except IndexError:
                    bpy.ops.text.new()
                    text = bpy.data.texts['Text']
                    text.lines[0].body = '# Check out Markdown in Blender!'
                text_lines = [line.body for line in text.lines]

            draw_lines, sub_lines, offset_x, offset_y, images = format_text(context, text_lines, fonts)  # noqa F458

            if 'bg_handle' in bpy.app.driver_namespace:
                self.remove_handle()

            # Now we add the draw handler to the window
            bpy.app.driver_namespace['bg_handle'] = add_draw(
                draw_bg,
                (),
                'WINDOW',
                'BACKDROP'
            )

            bpy.app.driver_namespace['image_handle'] = add_draw(
                draw_image,
                (self, context, images),
                'WINDOW',
                'POST_PIXEL'
            )

            bpy.app.driver_namespace['text_handle'] = add_draw(
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
    base_size: IntProperty(
        default=24,
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


classes = [
    DrawDocument,
    DocumentViewer,
    DocViewProps
]


def menu_func(self, context):
    if context.area.ui_type == 'DocumentViewer':
        layout = self.layout
        props = context.scene.docview_props
        layout.operator('docview.draw_document', icon='FILE_TICK')
        layout.prop(props, 'base_size', text='Size')
        layout.prop(props, 'internal', text='Use Blender Text Data')


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.docview_props = PointerProperty(type=DocViewProps)
    bpy.types.NODE_MT_editor_menus.append(menu_func)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Scene.docview_props
    bpy.types.NODE_MT_editor_menus.remove(menu_func)


if __name__ == "__main__":
    register()
