import types

import dearpygui.dearpygui as dpg

import editor
import marshal
import opcode
import dis

import ast
import importlib.util

FORMAT_VALUE_CONVERTERS = (
    (None, ''),
    (str, 'str'),
    (repr, 'repr'),
    (ascii, 'ascii'),
)

MAKE_FUNCTION_FLAGS = ('defaults', 'kwdefaults', 'annotations', 'closure')

main_code = None
current_code = None


def save_init(sender):
    dpg.save_init_file("dpg.ini")


def export(sender, data):
    file = open(data['file_path_name'], "wb")
    header = bytes(importlib.util.MAGIC_NUMBER).ljust(16, b"\x00")

    file.write(header + marshal.dumps(main_code.to_native()))


def apply_changes(sender):
    global main_code
    if sender == "co_names_apply":
        new_names = []

        i = 0
        while True:
            value = dpg.get_value(f"name_{i}")
            if value is None:
                break

            new_names.append(value)
            i += 1

        if current_code == main_code.uid:
            main_code.co_names = tuple(new_names)
        else:
            i, code = find_code(current_code)
            code.co_names = tuple(new_names)
            main_code.code_objects[i] = code

        refresh_co_code()

    elif sender == "co_consts_apply":
        new_consts = []

        i = 0
        while True:
            value = dpg.get_value(f"const_{i}")
            if value is None:
                break

            new_consts.append(ast.literal_eval(value))
            i += 1

        if current_code == main_code.uid:
            main_code.co_consts = tuple(new_consts)
        else:
            i, code = find_code(current_code)
            code.co_names = tuple(new_consts)
            main_code.code_objects[i] = code

        refresh_co_code()


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


def find_code(uid):
    if uid == main_code.uid:
        return 0, main_code
    code = [(i, e) for i, e in enumerate(main_code.code_objects) if str(e.uid) == uid]

    if len(code) != 1:
        print(f"UID ({uid}) was found {len(code)} times")
    else:
        return code[0]


def open_code_handler(sender, data):
    if not data[0]:  # Only when left-clicked
        global current_code
        if dpg.get_item_configuration(data[1])["user_data"] == dpg.get_value(
                data[1]):  # Only trigger if the element was clicked without the arrow
            uid = main_code.uid if "code_objects_tree" in data[1] else data[1].replace("tree_", "")
            _, code = find_code(uid)
            current_code = code.uid
            load_code(code)

        dpg.configure_item(data[1], user_data=dpg.get_value(data[1]))


def create_node(code, tree, parent, expand=False, tag=None):
    if tag is None:
        tag = "tree_" + str(code.uid)
    node_handlers = dpg.add_item_handler_registry()

    dpg.add_item_clicked_handler(tag=tag + "_handler", parent=node_handlers, callback=open_code_handler)

    with dpg.tree_node(label=code.co_name, tag=tag, parent=parent, default_open=expand, open_on_arrow=True,
                       user_data=expand) as cur_tree:
        dpg.bind_item_handler_registry(cur_tree, node_handlers)
        if tree:
            for obj, obj_tree in tree.items():
                create_node(obj, obj_tree, tag)


def load_co_code(code):
    dpg.delete_item("co_code_table")
    with dpg.table(tag="co_code_table", header_row=True, row_background=False,
                   policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True, parent="co_code_window", scrollX=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Opcode")
        dpg.add_table_column(label="Argument")

        for i, inst in enumerate(code.co_code):
            with dpg.table_row():
                dpg.add_text(i * 2)
                dpg.add_text(opcode.opname[inst.opcode], tag=f"code_{i * 2}")

                if inst.opcode >= opcode.HAVE_ARGUMENT:
                    value = get_repr(inst, code)
                    dpg.add_text(value, tag=f"code_{(i * 2) + 1}")

    dpg.bind_item_font(table, co_code_font)


# The differences with load_ and refresh_ is that refresh_ actually updates the items inplace and load_ resets and re-adds
def refresh_co_code():
    _, code = find_code(current_code)
    for i, inst in enumerate(code.co_code):
        dpg.set_value(f"code_{i * 2}", opcode.opname[inst.opcode])

        if inst.opcode >= opcode.HAVE_ARGUMENT:
            value = get_repr(inst, code)
            dpg.set_value(f"code_{(i * 2) + 1}", value)


def load_co_consts(code):
    dpg.delete_item("co_consts_table")
    with dpg.table(tag="co_consts_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True, parent="co_consts_window", scrollX=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Value")

        for index, value in enumerate(code.co_consts):
            if not isinstance(value, types.CodeType) and not isinstance(value, editor.Code):
                with dpg.table_row():
                    dpg.add_text(index)
                    dpg.add_input_text(default_value=repr(value), tag=f"const_{index}", width=400)

    dpg.bind_item_font(table, co_consts_font)


def load_co_names(code):
    dpg.delete_item("co_names_table")
    with dpg.table(tag="co_names_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True, parent="co_names_window", scrollX=True) as table:
        dpg.add_table_column(label="Index")
        value_col = dpg.add_table_column(label="Value")

        for index, value in enumerate(code.co_names):
            with dpg.table_row() as row:
                dpg.add_text(index)
                dpg.add_input_text(default_value=value, tag=f"name_{index}", width=400)

    dpg.bind_item_font(table, co_names_font)


def load_code(code):
    load_co_code(code)

    load_co_consts(code)

    load_co_names(code)


dpg.create_context()

with dpg.font_registry():
    default_font = dpg.add_font("Roboto-Medium.ttf", 20 * 2)
    co_code_font = dpg.add_font("RobotoMono-Medium.ttf", 30 * 2)
    co_consts_font = dpg.add_font("Roboto-Medium.ttf", 25 * 2)
    co_names_font = co_consts_font


def open_file(sender, app_data, user_data):
    global main_code
    global current_code
    file = open(app_data['file_path_name'], "rb")
    file.seek(16)  # Skip the pyc header
    code = marshal.loads(file.read())

    code = editor.code2custom(code)

    main_code = code
    current_code = code.uid

    dpg.delete_item("code_objects_tree")

    create_node(code, code.tree, "code_objects_window", expand=True, tag="code_objects_tree")

    load_code(code)


with dpg.file_dialog(directory_selector=False, show=False, file_count=1, callback=open_file, id="select_file",
                     width=800, height=400):
    dpg.add_file_extension(".pyc", color=(0, 255, 0, 255))

with dpg.file_dialog(directory_selector=False, show=False, file_count=1, callback=export, id="save_file",
                     width=800, height=400):
    dpg.add_file_extension(".pyc", color=(0, 255, 0, 255))

with dpg.viewport_menu_bar():
    with dpg.menu(label="File"):
        dpg.add_menu_item(label="Open", callback=lambda: dpg.show_item("select_file"))
        dpg.add_menu_item(label="Save layout", callback=save_init)
        dpg.add_menu_item(label="Export .pyc file", callback=lambda: dpg.show_item("save_file"))

with dpg.window(label="Instructions", tag="co_code_window", no_close=True):
    with dpg.table(tag="co_code_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Opcode")
        dpg.add_table_column(label="Argument")

    dpg.bind_item_font(table, co_code_font)

with dpg.window(label="Constants", tag="co_consts_window", no_close=True):
    with dpg.menu_bar():
        dpg.add_button(label="Apply changes", tag="co_consts_apply", callback=apply_changes)
    with dpg.table(tag="co_consts_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Value")

    dpg.bind_item_font(table, co_consts_font)

with dpg.window(label="Names", tag="co_names_window", no_close=True):
    with dpg.menu_bar():
        dpg.add_button(label="Apply changes", tag="co_names_apply", callback=apply_changes)

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
