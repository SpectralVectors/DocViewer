import blf
import gpu
from gpu_extras.batch import batch_for_shader


# Function to set up Background drawing
def draw_bg(self, context):
    if context.area.ui_type == 'DocumentViewer':
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


# Function to set up Code and Quote block drawing
def draw_block(self, context, code_blocks, quote_blocks):
    if context.area.ui_type == 'DocumentViewer':
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
            code_block_vertices = (
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
            code_block_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            batch = batch_for_shader(
                code_block_shader,
                'TRIS',
                {"pos": code_block_vertices},
                indices=indices
            )
            # This is where we define the background color
            code_block_shader.uniform_float(
                "color",
                block_color
            )
            batch.draw(code_block_shader)

        for block in quote_blocks:
            offset_x = quote_blocks[block][0]
            offset_y = height - quote_blocks[block][1] + base_size / 4

            if scroll[0] > 0:
                offset_x -= scroll[0] / scroll_factor
            if scroll[1] < 0:
                offset_y -= scroll[1] / scroll_factor

            quarter = base_size / 4
            three_quarters = base_size - quarter
            bottom = offset_y - three_quarters
            top = offset_y + three_quarters
            width = offset_x + (base_size / 2)
            # Here we define the positions of the vertices of the blocks
            quote_block_vertices = (
                (offset_x, bottom),  # Bottom Left
                (width, bottom),  # Bottom Right
                (offset_x, top),  # Top Left
                (width, top)  # Top Right
            )

            # This defines the order in which we connect the vertices,
            # creating two triangles
            indices = (
                (0, 1, 2),  # _ \
                (2, 1, 3)  # \ |
            )

            # Creating the shader to fill in the faces we created above
            quote_block_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            batch = batch_for_shader(
                quote_block_shader,
                'TRIS',
                {"pos": quote_block_vertices},
                indices=indices
            )
            # This is where we define the background color
            quote_block_shader.uniform_float(
                "color",
                block_color
            )
            batch.draw(quote_block_shader)


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
