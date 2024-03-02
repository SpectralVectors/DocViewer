import bpy
from bpy.types import NodeTree
from bpy.types import Operator
from bpy.types import PropertyGroup
from bpy.props import PointerProperty
from bpy.props import FloatProperty
from bpy.props import IntProperty
from bpy.props import BoolProperty
from bpy.props import EnumProperty
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
    "version": (0, 1, 6),
    "blender": (2, 80, 0),
    "location": "Document Viewer Editor",
    "description": "Read and render Markdown files in a custom Editor",
    "warning": "",
    "doc_url": "https://github.com/SpectralVectors/DocViewer",
    "category": "Interface",
}


# Function to calculate screen size of rendered characters
def get_pil_text_size(text, font_size, font_name):
    font = ImageFont.truetype(font_name, font_size)
    size = font.getbbox(text)
    return size


# Function to set up Background drawing
def draw_bg(self, context):
    props = context.scene.docview_props
    current_theme = props.current_theme
    themes = props.themes
    theme = themes[current_theme]
    bg_color = theme[:4]

    width = context.area.width
    height = context.area.height

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


# Function to set up Background drawing
def draw_block(self, context, code_blocks):
    props = context.scene.docview_props
    base_size = props.base_size

    current_theme = props.current_theme
    themes = props.themes
    theme = themes[current_theme]
    block_color = theme[4:8]

    x = context.region.x
    y = context.region.y
    view = context.region.view2d
    scroll = view.region_to_view(x, y)
    scroll_factor = 5

    #  width = context.area.width
    height = context.area.height

    length = 0
    for block in code_blocks:
        if code_blocks[block][2] > length:
            length = code_blocks[block][2]
    length = length * base_size * 0.7

    for block in code_blocks:
        offset_x = code_blocks[block][0]
        offset_y = height - code_blocks[block][1] + base_size / 8

        if scroll[0] > 0:
            offset_x -= scroll[0] / scroll_factor
        if scroll[1] < 0:
            offset_y -= scroll[1] / scroll_factor

        quarter = base_size / 4
        three_quarters = base_size - quarter
        bottom = offset_y - three_quarters
        top = offset_y + three_quarters

        # Here we define the positions of the vertices of the blocks
        block_vertices = (
            (offset_x, bottom),  # Bottom Left
            (length, bottom),  # Bottom Right
            (offset_x, top),  # Top Left
            (length, top)  # Top Right
        )

        # This defines the order in which we connect the vertices,
        # creating two triangles
        indices = (
            (0, 1, 2),  # _ \
            (2, 1, 3)  # \ |
        )

        # Creating the shader to fill in the faces we created above
        block_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(
            block_shader,
            'TRIS',
            {"pos": block_vertices},
            indices=indices
        )
        # This is where we define the background color
        block_shader.uniform_float(
            "color",
            block_color
        )
        batch.draw(block_shader)


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
        image_x = images[image][4]
        image_y = images[image][5]

        if scroll[0] > 0:
            image_x -= scroll[0] / scroll_factor
        if scroll[1] < 0:
            image_y -= scroll[1] / scroll_factor

        try:
            shader = gpu.shader.from_builtin('IMAGE_COLOR')
        except NameError:
            shader = gpu.shader.from_builtin('2D_IMAGE')

        batch = batch_for_shader(
            shader, 'TRI_FAN',
            {
                "pos": (
                    (image_x, image_y),
                    (image_x + width, image_y),
                    (image_x + width, image_y + height),
                    (image_x, image_y + height)
                ),
                "texCoord": (
                    (0, 0),
                    (1, 0),
                    (1, 1),
                    (0, 1)
                ),
            },
        )
        gpu.state.blend_set("ALPHA")
        shader.bind()
        shader.uniform_sampler("image", texture)
        batch.draw(shader)


# Format the text before passing it onto the draw function
def format_text(context, text_lines, fonts):
    props = context.scene.docview_props

    current_theme = props.current_theme
    themes = props.themes
    theme = themes[current_theme]
    text_color = theme[8:12]
    link_color = theme[12:]

    regular_path = props.regular_path

    # The base size for all drawing: font, offset, image
    base_size = props.base_size

    # Derive all scale elements from the base font size
    double = base_size * 2
    half = base_size / 2
    third = base_size / 3
    quarter = base_size / 4
    sixth = base_size / 6
    eigth = base_size / 8

    # Create dictionaries to hold all the line, link and image data
    # These are returned and passed to the draw function
    draw_lines = {}
    # key : value
    # line_index : line data
    # '0' : (sub_line, text, font_id, size, color, position)

    sub_lines = {}
    # key : value
    # line_index _ sub_index : sub_line data
    # '0_0' : (char, font_id, size, color, position, start, end)

    images = {}
    # key : value
    # bpy.data.images[image] : image data
    # 'image' : (image, texture, width, height, offset_x, offset_y)

    code_blocks = {}
    quote_blocks = {}

    regular = fonts[0]
    italic = fonts[1]
    bold = fonts[2]
    code = fonts[3]

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
        code_block = first('`')
        quote_block = first('>')

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
                b1 = 0
                text_size = base_size
                font_id = regular
                line = line.lstrip().replace('-', '◦')
                line = f"{' '*b1}{line}"
            elif first('  -'):
                b2 = int(sixth)
                text_size = base_size
                font_id = regular
                line = line.lstrip().replace('-', '•')
                line = f"{' '*b2}{line}"
            elif first('    -'):
                b3 = int(third)
                text_size = base_size
                font_id = regular
                line = line.lstrip().replace('-', '∙')
                line = f"{' '*b3}{line}"

        elif code_block:
            line = line.replace('`', '')
            line = f' {line}'
            length = len(line)
            text_size = base_size
            offset_x = base_size
            if len(code_blocks) < 1:
                offset_y += sixth
            font_id = code
            code_blocks[line_index] = (
                offset_x,
                offset_y,
                length
            )

        elif quote_block:
            line = line.replace('>', '')
            text_size = base_size
            offset_x = half
            font_id = regular
            quote_blocks[line_index] = (
                offset_x,
                offset_y
            )

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
        regex = r'(?:\[(?P<name>.*?)\])\((?P<url>.*?)\)'
        brackets = ['[', ']', '(', ')']
        extensions = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']

        for name, url in re.findall(regex, line):
            sub_line = True
            # Detect Images
            for ext in extensions:
                if url.lower().endswith(ext):
                    url = url.replace('/', '\\')
                    folder = props.folder
                    filepath = f'{folder}{url}'
                    bpy.ops.image.open(filepath=filepath)
                    bpy.ops.image.pack()

                    image_name = bpy.path.basename(filepath)
                    image = bpy.data.images[image_name]
                    texture = gpu.texture.from_image(image)

                    width = image.size[0] * (base_size / 24)
                    height = image.size[1] * (base_size / 24)
                    area_height = context.area.height
                    image_x = offset_x
                    image_y = area_height - height - offset_y

                    images[image] = (
                        image,     # 0 : blender image data block
                        texture,   # 1 : gpu texture from image
                        width,     # 2 : image width
                        height,    # 3 : image height
                        image_x,   # 4 : image x start position
                        image_y,   # 5 : image y start position
                    )
                    image_line = True
                    line = ''
                    offset_y += height

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
                    char_color = link_color
                else:
                    char_color = text_color
                sub_index = str(sub_index)
                sub_index = f'{line_index}_{sub_index}'
                sub_lines[sub_index] = (
                    char,        # 0 : single character from line
                    font_id,     # 1 : blf loaded font file
                    text_size,   # 2 : font size of the text
                    char_color,  # 3 : color of the text
                    offset_x,    # 4 : horizontal offset of each character
                    offset_y,    # 5 : vertical offset of the line
                )
                offset_x += get_pil_text_size(char, text_size, regular_path)[2]

        # For line level formatting
        # e.g. headers, regular text, full lines in italic or bold
        line_color = text_color
        line_index = str(line_index)
        draw_lines[line_index] = (
            line,        # 0 : the text of the line
            font_id,     # 1 : blf loaded font file
            text_size,   # 2 : font size of the text
            line_color,  # 3 : color of the text
            offset_x,    # 4 : horizontal offset of the line
            offset_y,    # 5 : vertical offset of the line
            sub_line,    # 6 : boolean, true if a link is found
            image_line   # 7 : boolean, true if an image is found
        )
        offset_y += base_size + sixth

    return draw_lines, sub_lines, offset_x, offset_y, images, code_blocks  # noqa


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

            link = lines[line_text][6]
            image = lines[line_text][7]

            if link and not image:
                for sub_index in sub:
                    char = sub[sub_index][0]
                    font_id = sub[sub_index][1]
                    text_size = sub[sub_index][2]
                    char_color = sub[sub_index][3]
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
                    blf.color(font_id, *char_color)
                    blf.draw(font_id, char)
            else:
                line = lines[line_text][0]
                font_id = lines[line_text][1]
                text_size = lines[line_text][2]
                line_color = lines[line_text][3]
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
                blf.color(font_id, *line_color)
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
                block_handle = bpy.app.driver_namespace['block_handle']

                handles = [bg_handle, text_handle, image_handle, block_handle]

                space = bpy.types.SpaceNodeEditor
                remove = space.draw_handler_remove

                for handle in handles:
                    remove(handle, 'WINDOW')

                return {'FINISHED'}
            except AttributeError:
                print('No draw handlers found!')
        except ValueError:
            print('Null pointer!')

    def modal(self, context, event):
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
        code_path = props.code_path
        internal = props.internal

        if context.area.ui_type == 'DocumentViewer':
            if os.path.exists(regular_path):
                regular = blf.load(regular_path)
            if os.path.exists(italic_path):
                italic = blf.load(italic_path)
            if os.path.exists(bold_path):
                bold = blf.load(bold_path)
            if os.path.exists(code_path):
                code = blf.load(code_path)

            if regular is not None:
                font_id = regular
            else:
                font_id = regular = italic = bold = code = 0 # noqa F841

            fonts = [regular, italic, bold, code]

            add_draw = bpy.types.SpaceNodeEditor.draw_handler_add
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

            draw_lines, sub_lines, offset_x, offset_y, images, code_blocks = format_text(context, text_lines, fonts)  # noqa F458

            if 'bg_handle' in bpy.app.driver_namespace:
                self.remove_handle()

            # Now we add the draw handlers to the window
            bpy.app.driver_namespace['bg_handle'] = add_draw(
                draw_bg,
                (self, context),
                'WINDOW',
                'BACKDROP'
            )

            bpy.app.driver_namespace['block_handle'] = add_draw(
                draw_block,
                (self, context, code_blocks),
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
        layout.prop(props, 'current_theme', text='Theme')
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
