import dearpygui.dearpygui as dpg
import editor, opcode, marshal


def save_init(sender):
    dpg.save_init_file("dpg.ini")


def load_code(code):
    code = editor.code2custom(code)

    dpg.delete_item("co_code_table")
    with dpg.table(tag="co_code_table", header_row=True, row_background=False,
                   policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True, parent="co_code_window") as table:
        dpg.add_table_column(label="Opcode")
        dpg.add_table_column(label="Argument")

        for inst in code.co_code:
            with dpg.table_row():
                dpg.add_text(opcode.opname[inst.opcode])
                dpg.add_text(inst.arg)

    dpg.bind_item_font(table, co_code_font)

    dpg.delete_item("co_consts_table")
    with dpg.table(tag="co_consts_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True, parent="co_consts_window") as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Value")

        for index, value in enumerate(code.co_consts):
            with dpg.table_row():
                dpg.add_text(index)
                dpg.add_text(value)

    dpg.bind_item_font(table, co_consts_font)

    dpg.delete_item("co_names_table")
    with dpg.table(tag="co_names_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True, parent="co_names_window") as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Value")

        for index, value in enumerate(code.co_names):
            with dpg.table_row():
                dpg.add_text(index)
                dpg.add_text(value)

    dpg.bind_item_font(table, co_names_font)


dpg.create_context()

with dpg.font_registry():
    default_font = dpg.add_font("Roboto-Medium.ttf", 20 * 2)
    co_code_font = dpg.add_font("Roboto-Medium.ttf", 30 * 2)
    co_consts_font = dpg.add_font("Roboto-Medium.ttf", 25 * 2)
    co_names_font = co_consts_font


def open_file(sender, app_data, user_data):
    file = open(app_data['file_path_name'], "rb")
    file.seek(16)  # Skip the pyc header
    code = marshal.loads(file.read())

    load_code(code)


with dpg.file_dialog(directory_selector=False, show=False, file_count=1, callback=open_file, id="select_file"):
    dpg.add_file_extension(".pyc", color=(0, 255, 0, 255))

with dpg.viewport_menu_bar():
    with dpg.menu(label="File"):
        dpg.add_menu_item(label="Open", callback=lambda: dpg.show_item("select_file"))
        dpg.add_menu_item(label="Save layout", callback=save_init)

with dpg.window(label="Instructions", tag="co_code_window", no_close=True):
    with dpg.table(tag="co_code_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True) as table:
        dpg.add_table_column(label="Opcode")
        dpg.add_table_column(label="Argument")

    dpg.bind_item_font(table, co_code_font)

with dpg.window(label="Constants", tag="co_consts_window", no_close=True):
    with dpg.table(tag="co_consts_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Value")

    dpg.bind_item_font(table, co_consts_font)

with dpg.window(label="Names", tag="co_names_window", no_close=True):
    with dpg.table(tag="co_names_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Value")

    dpg.bind_item_font(table, co_names_font)

dpg.bind_font(default_font)
dpg.set_global_font_scale(0.5)

dpg.configure_app(docking=True, docking_space=True, init_file="dpg.ini")
dpg.create_viewport()
dpg.setup_dearpygui()
dpg.show_viewport()

dpg.start_dearpygui()
dpg.destroy_context()
