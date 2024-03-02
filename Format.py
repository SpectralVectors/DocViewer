import bpy
import gpu
import re
from . Helpers import get_pil_text_size


# Format the text before passing it onto the draw function
def format_text(context, text_lines, fonts):
    props = context.scene.docview_props

    current_theme = props.current_theme
    themes = props.themes
    theme = themes[current_theme]
    # block_color = theme[4:8]
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
            line_color = text_color

        # Format Italic
        elif italicized:
            text_size = base_size
            font_id = italic
            line = line.replace('_', '').replace('*', '')
            line_color = text_color

        # Format Bold
        elif bolded:
            text_size = base_size
            font_id = bold
            line = line.replace('__', '').replace('**', '')
            line_color = text_color

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
            line_color = text_color

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
            line_color = text_color

        elif quote_block:
            line = line.replace('>', '')
            line = f'  {line}'
            text_size = base_size
            offset_x = base_size
            font_id = regular
            quote_blocks[line_index] = (
                offset_x,
                offset_y
            )
            line_color = text_color

        # Format Regular Text
        else:
            text_size = base_size
            font_id = regular
            line_color = text_color

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

    return draw_lines, sub_lines, offset_x, offset_y, images, code_blocks, quote_blocks  # noqa
