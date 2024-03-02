import bpy
from bpy.types import NodeTree
from bpy.types import Operator
from bpy.props import PointerProperty
import blf
import os

from . Helpers import menu_func
from . Properties import DocViewProps
from . Format import format_text
from . Draw import draw_bg, draw_block, draw_image, draw_text


bl_info = {
    "name": "Document Viewer",
    "author": "Spectral Vectors",
    "version": (0, 1, 8),
    "blender": (2, 80, 0),
    "location": "Document Viewer Editor",
    "description": "Read and render Markdown files in a custom Editor",
    "warning": "",
    "doc_url": "https://github.com/SpectralVectors/DocViewer",
    "category": "Interface",
}


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

            draw_lines, sub_lines, offset_x, offset_y, images, code_blocks, quote_blocks = format_text(context, text_lines, fonts)  # noqa F458

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
                (self, context, code_blocks, quote_blocks),
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
    bpy.types.NODE_MT_editor_menus.append(menu_func)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Scene.docview_props
    bpy.types.NODE_MT_editor_menus.remove(menu_func)


if __name__ == "__main__":
    register()
