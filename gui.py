import dearpygui.dearpygui as dpg
import ctypes
import editor, opcode

ctypes.windll.shcore.SetProcessDpiAwareness(2)



def print_me(sender):
    print(f"Menu Item: {sender}")


code = editor.code2custom(compile("print(1)\n" * 100, "", "exec"))


def save_callback():
    print("Save Clicked")


dpg.create_context()

with dpg.font_registry():
    default_font = dpg.add_font("Roboto-Medium.ttf", 20 * 2)
    co_code_font = dpg.add_font("Roboto-Medium.ttf", 30 * 2)
    co_consts_font = dpg.add_font("Roboto-Medium.ttf", 25 * 2)
    co_names_font = co_consts_font

with dpg.viewport_menu_bar():
    with dpg.menu(label="File"):
        dpg.add_menu_item(label="Save", callback=print_me)
        dpg.add_menu_item(label="Save As", callback=print_me)

        with dpg.menu(label="Settings"):
            dpg.add_menu_item(label="Setting 1", callback=print_me, check=True)
            dpg.add_menu_item(label="Setting 2", callback=print_me)

    dpg.add_menu_item(label="Help", callback=print_me)

    with dpg.menu(label="Widget Items"):
        dpg.add_checkbox(label="Pick Me", callback=print_me)
        dpg.add_button(label="Press Me", callback=print_me)
        dpg.add_color_picker(label="Color Me", callback=print_me)

with dpg.window(label="Instructions", tag="co_code_window", no_close=True):
    with dpg.table(label="co_code_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True) as table:
        dpg.add_table_column(label="Opcode")
        dpg.add_table_column(label="Argument")

        for inst in code.co_code:
            with dpg.table_row():
                dpg.add_text(opcode.opname[inst.opcode])
                dpg.add_text(inst.arg)

    dpg.bind_item_font(table, co_code_font)

with dpg.window(label="Constants", tag="co_consts_window", no_close=True):
    with dpg.table(label="co_consts_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Value")

        for index, value in enumerate(code.co_consts):
            with dpg.table_row():
                dpg.add_text(index)
                dpg.add_text(value)

    dpg.bind_item_font(table, co_consts_font)

with dpg.window(label="Names", tag="co_names_window", no_close=True):
    with dpg.table(label="co_names_table", header_row=True, row_background=False, policy=dpg.mvTable_SizingFixedFit,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True) as table:
        dpg.add_table_column(label="Index")
        dpg.add_table_column(label="Value")

        for index, value in enumerate(code.co_names):
            with dpg.table_row():
                dpg.add_text(index)
                dpg.add_text(value)

    dpg.bind_item_font(table, co_names_font)

dpg.bind_font(default_font)
dpg.set_global_font_scale(0.5)

dpg.configure_app(docking=True, docking_space=True)
dpg.create_viewport()
dpg.setup_dearpygui()
dpg.show_viewport()

dpg.start_dearpygui()
dpg.destroy_context()
