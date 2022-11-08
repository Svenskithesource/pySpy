import os.path
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

current_file = None
current_code_id = None
file_codes = []
last_directory = None


def export(sender, data):
    load_file_dialogs(data['current_path'])

    file = open(data['file_path_name'], "wb")
    header = bytes(importlib.util.MAGIC_NUMBER).ljust(16, b"\x00")

    file.write(header + marshal.dumps(current_file.to_native()))


def get_new_values(prefix):
    new_values = []
    i = 0
    while True:
        value = dpg.get_value(f"{prefix}_{i}")
        if value is None:
            break

        new_values.append(value)
        i += 1

    return new_values


def get_literal_const(value, index):
    return current_file.co_consts[index] if '<Code object' in value else ast.literal_eval(value)


def apply_name_changes():
    global current_file
    new_names = get_new_values("name")

    current_file.co_names = tuple(new_names)
    refresh_co_code()


def apply_const_changes():
    global current_file
    new_consts = get_new_values("const")

    new_consts = [get_literal_const(value, index)
                  for index, value in enumerate(new_consts)]
                  
    current_file.co_consts = tuple(new_consts)
    refresh_co_code()


def apply_code_changes(sender, data):
    global current_file
    index = int(sender.replace("code_", "")) if "code_" in sender else int(
        sender.replace("arg_", ""))
    if index % 2 == 0:  # If it's an index
        if str(current_code_id) == str(current_file.uid):
            current_file.co_code[index // 2].opcode = opcode.opmap[data]
        else:
            i, code = find_code(current_code_id)
            code.co_code[index // 2].opcode = opcode.opmap[data]
            current_file.code_objects[i] = code
    else:
        if str(current_code_id) == str(current_file.uid):
            current_file.co_code[(index - 1) // 2].arg = data
        else:
            i, code = find_code(current_code_id)
            code.co_code[(index - 1) // 2].arg = data
            current_file.code_objects[i] = code

    refresh_co_code()


def co_names_add():
    if current_file is None:
        return

    value = ""
    names = list(current_file.co_names)
    names.append(value)

    current_file.co_names = tuple(names)
    index = len(current_file.co_names) - 1

    with dpg.table_row(parent="co_names_table"):
        dpg.add_text(index)
        dpg.add_input_text(default_value=value, tag=f"name_{index}", width=400,
                           callback=apply_name_changes, on_enter=True)


def co_consts_add():
    if current_file is None:
        return

    value = ""
    consts = list(current_file.co_consts)
    consts.append(value)

    current_file.co_consts = tuple(consts)
    index = len(current_file.co_consts) - 1

    with dpg.table_row(parent="co_consts_table"):
        dpg.add_text(index)
        dpg.add_input_text(default_value=value, tag=f"const_{index}", width=400,
                           callback=apply_const_changes, on_enter=True)


def set_color(item, kind):
    if kind == str:
        dpg.bind_item_theme(item, str_theme)
    elif kind in [int, float]:
        dpg.bind_item_theme(item, int_theme)
    elif kind == Exception:
        dpg.bind_item_theme(item, exception_theme)
    else:
        dpg.bind_item_theme(item, unknown_theme)


def get_repr(inst, code):
    if inst.opcode in dis.hasconst:
        try:
            kind = type(code.co_consts[inst.arg])
            value = repr(code.co_consts[inst.arg])
        except IndexError:
            kind = Exception
            value = "Invalid constant index"
    elif inst.opcode in dis.hasname:
        try:
            kind = type(code.co_names[inst.arg])
            value = repr(code.co_names[inst.arg])
        except IndexError:
            kind = Exception
            value = "Invalid names index"
    elif inst.opcode in dis.hascompare:
        try:
            kind = str
            value = dis.cmp_op[inst.arg]
        except IndexError:
            kind = Exception
            value = "Invalid compare argument"
    elif inst.opcode == opcode.opmap["MAKE_FUNCTION"]:
        kind = str
        value = ', '.join(s for i, s in enumerate(MAKE_FUNCTION_FLAGS)
                          if inst.arg & (1 << i))

        if value == "":
            value = None

    elif inst.opcode == opcode.opmap["FORMAT_VALUE"]:
        try:
            kind = str
            value = FORMAT_VALUE_CONVERTERS[inst.arg & 0x3][1]
        except IndexError:
            kind = Exception
            value = "Invalid format argument"
    else:
        kind = None
        value = ""

    return kind, value


def get_file_code_by_id(uid):
    for file in file_codes:
        if str(uid) == str(file.uid):
            return file


def search_code_recursively(child_uid):
    for file in file_codes:
        codes = [(i, e) for i, e in enumerate(
            file.code_objects) if str(e.uid) == str(child_uid)]

        if len(codes) != 1:
            continue

        global current_file
        current_file = file

        return codes[0]


def find_code(uid, is_file=False):
    if is_file or str(current_file.uid) == str(uid):
        return 0, get_file_code_by_id(uid)

    codes_found = [(i, e) for i, e in enumerate(
        current_file.code_objects) if str(e.uid) == str(uid)]

    if len(codes_found) == 1:
        return codes_found[0]

    if len(codes_found) == 0:
        return search_code_recursively(uid)

    print(f"UID ({uid}) was found {len(codes_found)} times")


def open_code_handler(sender, data):
    # Ignore when it's not left-click
    if not data[0]:

        object_id = data[1]

        # Ignore when clicked in the arrow
        if dpg.get_item_configuration(object_id)["user_data"] == dpg.get_value(object_id):

            global current_file
            uid = object_id.split('tree_')[1]
            is_file = "code_objects_tree" in object_id
            _, code = find_code(uid, is_file)

            if is_file:
                current_file = code

            global current_code_id
            current_code_id = code.uid
            load_code(code)

        dpg.configure_item(data[1], user_data=dpg.get_value(data[1]))


def create_node(code, tree, parent, expand=False, tag=None, name=None):
    if tag is None:
        tag = "tree_" + str(code.uid)

    skip = dpg.does_item_exist(tag + "_handler")
    if not skip:
        node_handlers = dpg.add_item_handler_registry()

        dpg.add_item_clicked_handler(
            tag=tag + "_handler", parent=node_handlers, callback=open_code_handler)
    else:
        node_handlers = dpg.get_item_parent(tag + "_handler")

    with dpg.tree_node(label=name if name else code.co_name, tag=tag, parent=parent, default_open=expand,
                       open_on_arrow=True,
                       user_data=expand, leaf=True if not tree else False) as cur_tree:

        dpg.bind_item_handler_registry(cur_tree, node_handlers)
        if tree:
            for obj, obj_tree in tree.items():
                create_node(obj, obj_tree, tag)


# The differences with load_ and refresh_ is that refresh_ actually updates the items inplace and load_ resets and
# re-adds
def refresh_co_code():
    _, code = find_code(current_code_id)
    for i, inst in enumerate(code.co_code):
        dpg.set_value(f"code_{i * 2}", opcode.opname[inst.opcode])

        if inst.opcode >= opcode.HAVE_ARGUMENT:
            dpg.set_value(f"arg_{(i * 2) + 1}", inst.arg)
            kind, value = get_repr(inst, code)
            dpg.set_value(f"code_{(i * 2) + 1}", value)

            set_color(f"code_{(i * 2) + 1}", kind)


def load_co_code(code):
    dpg.delete_item("co_code_table")
    with dpg.table(tag="co_code_table", header_row=True, row_background=False,
                   policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True, parent="co_code_window", scrollX=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Opcode", init_width_or_weight=250)
        dpg.add_table_column(label="Argument")

        for i, inst in enumerate(code.co_code):
            with dpg.table_row():
                index = dpg.add_text(i * 2)
                dpg.bind_item_theme(index, index_theme)
                op = dpg.add_combo(list(sorted(opcode.opmap.keys())), default_value=opcode.opname[inst.opcode],
                                   tag=f"code_{i * 2}", callback=apply_code_changes, width=250)
                dpg.bind_item_theme(op, opcode_theme)

                if inst.opcode >= opcode.HAVE_ARGUMENT:
                    kind, value = get_repr(inst, code)

                    with dpg.group(horizontal=True, horizontal_spacing=30):
                        arg = dpg.add_input_int(default_value=inst.arg, tag=f"arg_{(i * 2) + 1}",
                                                callback=apply_code_changes, on_enter=True, width=250)
                        dpg.bind_item_theme(arg, arg_theme)

                        text = dpg.add_text(value, tag=f"code_{(i * 2) + 1}")

                        set_color(text, kind)

    dpg.bind_item_font(table, co_code_font)


def load_co_consts(code):
    dpg.delete_item("co_consts_table")
    with dpg.table(tag="co_consts_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True, parent="co_consts_window", scrollX=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Value")

        for index, value in enumerate(code.co_consts):
            can_edit = not isinstance(
                value, types.CodeType) and not isinstance(value, editor.Code)

            with dpg.table_row():
                dpg.add_text(index)
                dpg.add_input_text(default_value=repr(value), tag=f"const_{index}", width=400, enabled=can_edit,
                                   user_data="co_consts_apply", callback=apply_const_changes, on_enter=True)

    dpg.bind_item_font(table, co_consts_font)


def load_co_names(code):
    dpg.delete_item("co_names_table")
    with dpg.table(tag="co_names_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True, parent="co_names_window", scrollX=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Value")

        for index, value in enumerate(code.co_names):
            with dpg.table_row() as row:
                dpg.add_text(index)
                dpg.add_input_text(default_value=value, tag=f"name_{index}", width=400, user_data="co_names_apply",
                                   callback=apply_name_changes, on_enter=True)

    dpg.bind_item_font(table, co_names_font)


def load_code(code):
    load_co_code(code)

    load_co_consts(code)

    load_co_names(code)


def create_file_dialog(id, path, callback):
    try:
        dpg.delete_item(id)
    except SystemError:
        pass

    with dpg.file_dialog(directory_selector=False, default_path=path, show=False, callback=callback, tag=id, id=id,
                         width=800, height=400):
        dpg.add_file_extension(".pyc", color=(0, 255, 0, 255))


def load_file_dialogs(path):
    global last_directory
    if path == last_directory:
        return

    last_directory = path
    create_file_dialog('select_file', path, open_file)
    create_file_dialog('save_file', path, export)


dpg.create_context()

with dpg.font_registry():
    default_font = dpg.add_font("resources/Roboto-Medium.ttf", 20 * 2)
    co_code_font = dpg.add_font("resources/RobotoMono-Medium.ttf", 30 * 2)
    co_consts_font = dpg.add_font("resources/Roboto-Medium.ttf", 25 * 2)
    co_names_font = co_consts_font

with dpg.theme() as opcode_theme:
    with dpg.theme_component(dpg.mvText):
        dpg.add_theme_color(dpg.mvThemeCol_Text, (152, 92, 133))

with dpg.theme() as index_theme:
    with dpg.theme_component(dpg.mvText):
        dpg.add_theme_color(dpg.mvThemeCol_Text, (128, 111, 77))

with dpg.theme() as str_theme:
    with dpg.theme_component(dpg.mvText):
        dpg.add_theme_color(dpg.mvThemeCol_Text, (214, 157, 133))

with dpg.theme() as int_theme:
    with dpg.theme_component(dpg.mvText):
        dpg.add_theme_color(dpg.mvThemeCol_Text, (128, 111, 77))

with dpg.theme() as arg_theme:
    with dpg.theme_component(dpg.mvText):
        dpg.add_theme_color(dpg.mvThemeCol_Text, (153, 101, 0))

with dpg.theme() as exception_theme:
    with dpg.theme_component(dpg.mvText):
        dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 85, 85))

with dpg.theme() as unknown_theme:
    with dpg.theme_component(dpg.mvText):
        dpg.add_theme_color(dpg.mvThemeCol_Text, (86, 156, 214))


def open_file(sender, app_data, user_data):
    global current_file
    global current_code_id

    load_file_dialogs(app_data['current_path'])
    selected_files = list(app_data['selections'].values())

    existing_files = [os.path.basename(file.co_filename)
                      for file in file_codes]

    for file_name in selected_files:
        if os.path.basename(file_name) not in existing_files:
            file = open(file_name, "rb")
            file.seek(16)  # Skip the pyc header
            code = marshal.loads(file.read())

            code = editor.code2custom(code)

            file_codes.append(code)
            current_file = code
            current_code_id = code.uid

            create_node(code, code.tree, "code_objects_window", expand=True, tag=f"code_objects_tree_{code.uid}",
                        name=os.path.basename(file_name))

            load_code(code)


load_file_dialogs(os.path.dirname(__file__))

with dpg.viewport_menu_bar():
    with dpg.menu(label="File"):
        dpg.add_menu_item(
            label="Open", callback=lambda: dpg.show_item("select_file"))
        dpg.add_menu_item(label="Export .pyc file",
                          callback=lambda: dpg.show_item("save_file"))

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
        dpg.add_button(label="Add", tag="co_consts_add",
                       callback=co_consts_add)
    with dpg.table(tag="co_consts_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Value")

    dpg.bind_item_font(table, co_consts_font)

with dpg.window(label="Names", tag="co_names_window", no_close=True):
    with dpg.menu_bar():
        dpg.add_button(label="Add", tag="co_names_add", callback=co_names_add)
    with dpg.table(tag="co_names_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Value")

    dpg.bind_item_font(table, co_names_font)

with dpg.window(label="Code Objects", tag="code_objects_window", no_close=True):
    tree = dpg.add_tree_node(tag="code_objects_tree", show=False)

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
