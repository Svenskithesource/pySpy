import dis
import types

import dearpygui.dearpygui as dpg

import editor
import marshal
import opcode

FORMAT_VALUE_CONVERTERS = (
    (None, ''),
    (str, 'str'),
    (repr, 'repr'),
    (ascii, 'ascii'),
)

MAKE_FUNCTION_FLAGS = ('defaults', 'kwdefaults', 'annotations', 'closure')


def save_init(sender):
    dpg.save_init_file("dpg.ini")


def apply_changes(sender):
    pass


def get_repr(inst, code):
    if inst.opcode in dis.hasconst:
        try:
            value = repr(code.co_consts[inst.arg])
        except IndexError:
            value = "Invalid constant index"
    elif inst.opcode in dis.hasname:
        try:
            value = repr(code.co_names[inst.arg])
        except IndexError:
            value = "Invalid names index"
    elif inst.opcode in dis.hascompare:
        try:
            value = dis.cmp_op[inst.arg]
        except IndexError:
            value = "Invalid compare argument"
    elif inst.opcode == opcode.opmap["MAKE_FUNCTION"]:
        value = ', '.join(s for i, s in enumerate(MAKE_FUNCTION_FLAGS)
                          if inst.arg & (1 << i))

        if value == "":
            value = None

    elif inst.opcode == opcode.opmap["FORMAT_VALUE"]:
        try:
            value = FORMAT_VALUE_CONVERTERS[inst.arg & 0x3]
        except IndexError:
            value = "Invalid format argument"
    else:
        value = None

    if value is None:
        value = inst.arg
    else:
        value = f"{inst.arg:<5}({value})"

    return value


def refresh_code(code):
    for i, inst in enumerate(code.co_code):
        dpg.set_value(f"index_{i * 2}", opcode.opname[inst.opcode])
        if inst.opcode >= opcode.HAVE_ARGUMENT:
            dpg.set_value(f"index_{i * 2}", get_repr(inst, code))


def create_node(code, tree, parent, expand=False):
    tag = "tree_" + str(code.uid)
    node_handlers = dpg.add_item_handler_registry()
    dpg.add_item_clicked_handler(tag=tag, parent=node_handlers, callback=lambda ok: print(ok))

    with dpg.tree_node(label=code.co_name, tag=tag, parent=parent, default_open=expand) as cur_tree:
        dpg.bind_item_handler_registry(cur_tree, node_handlers, )
        if tree:
            for obj, obj_tree in tree.items():
                create_node(obj, obj_tree, tag)


def load_code(code):
    dpg.delete_item("co_code_table")
    with dpg.table(tag="co_code_table", header_row=True, row_background=False,
                   policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True, parent="co_code_window", scrollX=True) as table:
        dpg.add_table_column(label="Opcode")
        dpg.add_table_column(label="Argument")

        for i, inst in enumerate(code.co_code):
            with dpg.table_row():
                dpg.add_text(opcode.opname[inst.opcode], tag=f"index_{i * 2}")

                if inst.opcode >= opcode.HAVE_ARGUMENT:
                    value = get_repr(inst, code)
                    dpg.add_text(value, tag=f"index_{(i * 2) + 1}")

    dpg.bind_item_font(table, co_code_font)

    dpg.delete_item("co_consts_table")
    with dpg.table(tag="co_consts_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True, parent="co_consts_window", scrollX=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Value")

        for index, value in enumerate(code.co_consts):
            with dpg.table_row():
                dpg.add_text(index)
                dpg.add_text(repr(value))

    dpg.bind_item_font(table, co_consts_font)

    dpg.delete_item("co_names_table")
    with dpg.table(tag="co_names_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True, parent="co_names_window", scrollX=True) as table:
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
    co_code_font = dpg.add_font("RobotoMono-Medium.ttf", 30 * 2)
    co_consts_font = dpg.add_font("Roboto-Medium.ttf", 25 * 2)
    co_names_font = co_consts_font


def open_file(sender, app_data, user_data):
    file = open(app_data['file_path_name'], "rb")
    file.seek(16)  # Skip the pyc header
    code = marshal.loads(file.read())

    code = editor.code2custom(code)

    dpg.delete_item("code_objects_tree")

    create_node(code, code.tree, "code_objects_window", True)

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
    with dpg.menu_bar():
        dpg.add_button(label="Apply changes", tag="co_names_apply")

    with dpg.table(tag="co_names_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Value")

    dpg.bind_item_font(table, co_names_font)

with dpg.window(label="Code Objects", tag="code_objects_window", no_close=True):
    tree = dpg.add_tree_node(tag="code_objects_tree")

    dpg.bind_item_font(tree, default_font)

dpg.bind_font(default_font)
dpg.set_global_font_scale(0.5)

dpg.configure_app(docking=True, docking_space=True, init_file="dpg.ini")
dpg.create_viewport()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_viewport_title("pySpy")

dpg.start_dearpygui()
dpg.destroy_context()
