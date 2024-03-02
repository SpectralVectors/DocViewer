import bpy
from PIL import ImageFont


# Function to calculate screen size of rendered characters
def get_pil_text_size(text, font_size, font_name):
    font = ImageFont.truetype(font_name, font_size)
    size = font.getbbox(text)
    return size


def update_func(self, context):
    bpy.ops.docview.draw_document('INVOKE_DEFAULT')


def menu_func(self, context):
    if context.area.ui_type == 'DocumentViewer':
        layout = self.layout
        props = context.scene.docview_props
        layout.operator('docview.draw_document', icon='FILE_TICK')
        layout.prop(props, 'base_size', text='Size')
        layout.prop(props, 'current_theme', text='Theme')
        layout.prop(props, 'internal', text='Use Blender Text Data')
