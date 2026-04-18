import ctypes
import json
import sys
import time
import traceback
import uiautomation as auto
from pywinauto import win32defines, win32functions, win32structures
from pywinauto import Desktop
from pywinauto.findwindows import ElementAmbiguousError, ElementNotFoundError
from pywinauto.uia_defines import NoPatternInterfaceError
from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.timings import Timings

element_obj = sys.argv[1]


def split_kwargs(kwargs, search_keys, additional_properties_keys):
    search_kwargs = {key: value for key, value in kwargs.items() if key in search_keys}
    additional_properties_kwargs = {key: value for key, value in kwargs.items() if key in additional_properties_keys}
    return search_kwargs, additional_properties_kwargs


search_keys = [
    "class_name", "class_name_re", "process", "title", "title_re",
    "top_level_only", "visible_only", "enabled_only", "handle",
    "ctrl_index", "found_index", "active_only", "control_id",
    "control_type", "auto_id", "framework_id", "backend"
]

# Список ключей для дополнительных свойств
additional_properties_keys = [
    "is_keyboard_focusable", "has_keyboard_focus", "is_dialog",
    "is_selected", "is_offscreen", "is_password", "help_text",
    "legacyI_accessible_role", "is_selection_pattern", "is_selection_required",
    "rectangle", "element_center_x", "element_center_y", "is_invoke_pattern"
]

# Список ключей для поиска элемента
ui_search_keys = [
    "Name",
    "SubName",
    "ClassName",
    "AutomationId",
    "ControlTypeName",
    "foundIndex",
    "searchDepth",
]

# Список ключей для дополнительных свойств
ui_additional_properties_keys = [
    'Culture',
    'FrameworkId',
    'HelpText',
    'HasKeyboardFocus',
    'LocalizedControlType',
    'IsContentElement',
    'IsControlElement',
    'IsDataValidForForm',
    'IsEnabled',
    'IsKeyboardFocusable',
    'IsOffscreen',
    'IsPassword',
    'IsRequiredForForm',
    'ItemStatus',
    'ItemType',
]


def draw_outline(
        cls,
        colour='green',
        thickness=2,
        fill=win32defines.BS_NULL,
        rect=None):
    """
    Draw an outline around the window.

    * **colour** can be either an integer or one of 'red', 'green', 'blue'
      (default 'green')
    * **thickness** thickness of rectangle (default 2)
    * **fill** how to fill in the rectangle (default BS_NULL)
    * **rect** the coordinates of the rectangle to draw (defaults to
      the rectangle of the control)
    """
    # don't draw if dialog is not visible
    if not cls.Exists():
        return

    colours = {
        "green": 0x00ff00,
        "blue": 0xff0000,
        "red": 0x0000ff,
    }

    # if it's a known colour
    if colour in colours:
        colour = colours[colour]

    if rect is None:
        rect = cls.BoundingRectangle

    # create the pen(outline)
    pen_handle = win32functions.CreatePen(
        win32defines.PS_SOLID, thickness, colour)

    # create the brush (inside)
    brush = win32structures.LOGBRUSH()
    brush.lbStyle = fill
    brush.lbHatch = win32defines.HS_DIAGCROSS
    brush_handle = win32functions.CreateBrushIndirect(ctypes.byref(brush))

    # get the Device Context
    dc = win32functions.CreateDC("DISPLAY", None, None, None)

    # push our objects into it
    win32functions.SelectObject(dc, brush_handle)
    win32functions.SelectObject(dc, pen_handle)

    # draw the rectangle to the DC
    win32functions.Rectangle(
        dc, rect.left, rect.top, rect.right, rect.bottom)

    # Delete the brush and pen we created
    win32functions.DeleteObject(brush_handle)
    win32functions.DeleteObject(pen_handle)

    # delete the Display context that we created
    win32functions.DeleteDC(dc)


def convert_str_to_bool(value):
    if isinstance(value, str) and value.lower() in ['true', 'false']:
        return value.lower() == 'true'
    return value


def check_element_properties(element_ui, expected_properties, check_visible=False, **kwargs):
    expected_properties_bool = {k: convert_str_to_bool(v) for k, v in expected_properties.items()}
    for prop, expected_value in expected_properties_bool.items():
        actual_value = None
        if prop == 'is_keyboard_focusable':
            actual_value = element_ui.is_keyboard_focusable()
        elif prop == 'has_keyboard_focus':
            actual_value = element_ui.has_keyboard_focus()
        elif prop == 'is_dialog':
            actual_value = element_ui.is_dialog()
        elif prop == 'is_selected':
            try:
                actual_value = True if element_ui.is_selected() == 1 else False
            except NoPatternInterfaceError as e:
                actual_value = False
        elif prop == 'is_offscreen':
            actual_value = True if element_ui.element_info._element.CurrentIsOffscreen == 1 else False
        elif prop == 'is_password':
            actual_value = True if element_ui.element_info._element.CurrentIsPassword == 1 else False
        elif prop == 'help_text':
            actual_value = element_ui.element_info._element.CurrentHelpText
        elif prop == 'legacyI_accessible_role':
            actual_value = element_ui.element_info._element.CurrentLocalizedControlType
        elif prop == 'is_invoke_pattern':
            try:
                actual_value = element_ui.iface_invoke
                actual_value = True
            except NoPatternInterfaceError as e:
                actual_value = False
        elif prop == 'is_selection_pattern':
            try:
                actual_value = element_ui.is_selected()
                actual_value = True
            except NoPatternInterfaceError as e:
                actual_value = False
        elif prop == 'is_selection_required':
            try:
                actual_value = True if element_ui.is_selection_required() == 1 else False
                actual_value = True
            except NoPatternInterfaceError as e:
                actual_value = False
        if actual_value != expected_value:
            if not check_visible:
                raise ElementNotFoundError(f"Не найден элемент: '{kwargs}'")
            else:
                return False
        else:
            continue
    return True


def find_element_by_recursion(element, properties, check_visible=False):
    """
    Рекурсивный поиск элемента на основе списка свойств.

    :param element: Начальный элемент для поиска.
    :param properties: Список словарей, содержащих свойства для сопоставления на каждом уровне.
    :return: Найденный элемент или None, если не найден.
    """
    if not properties:
        return element

    current_properties = properties[0]
    remaining_properties = properties[1:]
    search_kwargs, additional_properties_kwargs = split_kwargs(
        current_properties, search_keys, additional_properties_keys
    )

    try:
        # Фильтрация дочерних элементов на основе текущих свойств
        children = element.descendants(
            title=current_properties.get("title", ""),
            class_name=current_properties.get("class_name", ""),
            control_type=current_properties.get("control_type", ""),
            depth=current_properties.get("depth", 1),
        )

        for child in children:
            if check_element_properties(
                    child, additional_properties_kwargs,
                    check_visible=check_visible,
                    **search_kwargs
            ):
                result = find_element_by_recursion(child, remaining_properties)
                if result:
                    if str(result.element_info.rectangle) != '(L0, T0, R0, B0)':
                        return result

        return None

    except Exception as e:
        print(f"Произошла ошибка во время поиска: {e}")
        return None


def find_element_by_properties(json_obj_elem, set_focus=True, check_visible=False):
    """
    Поиск элемента на основе списка свойств.
    """
    dlg = None
    for i, obj in enumerate(json_obj_elem):
        search_kwargs, additional_properties_kwargs = split_kwargs(obj, search_keys, additional_properties_keys)
        if 'found_index' in search_kwargs:
            search_kwargs['found_index'] = int(search_kwargs['found_index'])
        if i == 0:
            search_kwargs['visible_only'] = False
            dlg = Desktop(backend='uia', allow_magic_lookup=False).window(**search_kwargs)
            if set_focus:
                dlg.set_focus()
        else:
            if len(search_kwargs) == 1:
                continue
            dlg = dlg.child_window(**search_kwargs)
        check_prop = check_element_properties(
            dlg, additional_properties_kwargs,
            check_visible=check_visible,
            **search_kwargs
        )
        if not check_prop:
            return None
    return dlg


def find_dialog_elem(element_string, check_visible=False, set_focus=True):
    json_obj_elem = element_string
    check_empty_properties = False
    if len(json_obj_elem) > 1:
        check_empty_properties = all(len(obj) == 1 for obj in json_obj_elem[1:])
    if check_empty_properties or len(json_obj_elem[-1]) == 1:
        json_obj_elem[-1]['found_index'] = 0
    index_count = sum(1 for obj in json_obj_elem if obj.get('found_index'))
    if index_count == 0 and json_obj_elem[-1].get('visible_only', False):
        search_kwargs, additional_properties_kwargs = split_kwargs(
            json_obj_elem[0],
            search_keys,
            additional_properties_keys
        )
        main_window = Desktop(backend='uia', allow_magic_lookup=False).window(**search_kwargs)
        if set_focus:
            main_window.set_focus()
        check_prop = check_element_properties(
            main_window, additional_properties_kwargs,
            check_visible=check_visible,
            **search_kwargs
        )
        if not check_prop:
            return None
        json_obj_elem.pop(0)
        dlg = find_element_by_recursion(main_window, json_obj_elem)
    else:
        dlg = find_element_by_properties(json_obj_elem, set_focus=set_focus, check_visible=check_visible)
    return dlg


def check_ui_auto_properties(element_ui, expected_properties, check_visible=False, **kwargs):
    """
    Проверяет, соответствуют ли свойства элемента ожидаемым значениям.

    :param element_ui: Элемент для проверки.
    :param expected_properties: Словарь с ожидаемыми свойствами и их значениями.
    :raises ElementNotFoundError: Если какое-либо свойство не совпадает.
    """
    for prop, expected_value in expected_properties.items():
        if isinstance(expected_value, str):
            if expected_value.lower() == "true":
                expected_value = True
            elif expected_value.lower() == "false":
                expected_value = False
        actual_value = None
        if prop == 'Culture':
            actual_value = element_ui.Culture
        elif prop == 'FrameworkId':
            actual_value = element_ui.FrameworkId
        elif prop == 'HelpText':
            actual_value = element_ui.HelpText
        elif prop == 'HasKeyboardFocus':
            actual_value = element_ui.HasKeyboardFocus
        elif prop == 'LocalizedControlType':
            actual_value = element_ui.LocalizedControlType
        elif prop == 'IsContentElement':
            actual_value = element_ui.IsContentElement
        elif prop == 'IsControlElement':
            actual_value = element_ui.IsControlElement
        elif prop == 'IsDataValidForForm':
            actual_value = element_ui.IsDataValidForForm
        elif prop == 'IsEnabled':
            actual_value = element_ui.IsEnabled
        elif prop == 'IsKeyboardFocusable':
            actual_value = element_ui.IsKeyboardFocusable
        elif prop == 'IsOffscreen':
            actual_value = element_ui.IsOffscreen
        elif prop == 'IsPassword':
            actual_value = element_ui.IsPassword
        elif prop == 'IsRequiredForForm':
            actual_value = element_ui.IsRequiredForForm
        elif prop == 'ItemStatus':
            actual_value = element_ui.ItemStatus
        elif prop == 'ItemType':
            actual_value = element_ui.ItemType

        elif prop == 'IsInvokePattern':
            try:
                element_ui.GetInvokePattern()
                actual_value = True
            except Exception as e:
                actual_value = False
        elif prop == 'IsSelectionPattern':
            try:
                element_ui.GetSelectionPattern()
                actual_value = True
            except Exception as e:
                actual_value = False
        if actual_value != expected_value:
            if not check_visible:
                raise ElementNotFoundError(f"Не найден элемент: '{kwargs}'")
            else:
                return False
        else:
            continue
    return True


def init_window(dct, main_window, check_visible):
    try:
        search_kwargs, additional_properties_kwargs = split_kwargs(
            dct, ui_search_keys,
            ui_additional_properties_keys
        )
        control_class = getattr(main_window, search_kwargs['ControlTypeName'])
        search_kwargs.pop('ControlTypeName')
        window = control_class(**search_kwargs)
        check_prop = check_ui_auto_properties(
            window,
            additional_properties_kwargs,
            check_visible=check_visible,
            **search_kwargs
        )
        if not check_prop:
            return False
        if not window.Exists(2):
            return False
        return window
    except Exception as e:
        return False


def find_dialog_elem_ui_auto(list_dicts, check_visible=False, set_focus=True, check_children=False):
    main_window = None
    if len(list_dicts[-1]) == 1:
        list_dicts[-1]['foundIndex'] = 1
    for idx, dct in enumerate(list_dicts):
        if 'foundIndex' in dct:
            dct['foundIndex'] = int(dct['foundIndex'])
        if idx == 0:
            dct['searchDepth'] = 1
            main_window = init_window(dct, auto, check_visible)
            if set_focus:
                try:
                    main_window.SetActive()
                except Exception as e:
                    pass
        else:
            if len(dct) == 1:
                continue
            main_window = init_window(dct, main_window, check_visible)
    if check_children:
        return [elem for elem in child_controls_generator(main_window)]
    else:
        return main_window


def child_controls_generator(element):
    child = element.GetFirstChildControl()
    while child:
        yield child
        child = child.GetNextSiblingControl()


with open(file=element_obj, mode='r', encoding='utf-8') as f:
    json_obj_elem = json.load(f)


def replace_chars_in_json(data):
    """
    Рекурсивно проходит по словарю и заменяет все вхождения '\\\\xa0' на '\\xa0'.
    
    :param data: Словарь или список для обработки.
    :return: Обработанный словарь или список.
    """
    if isinstance(data, dict):
        return {k: replace_chars_in_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_chars_in_json(item) for item in data]
    elif isinstance(data, str):
        # Замена символов в строках
        return data.replace('\\xa0', '\xa0')
    else:
        # Для других типов данных просто возвращаем их без изменений
        return data


json_obj_elem = replace_chars_in_json(json_obj_elem)

dlg = None
if json_obj_elem[0].get('ControlTypeName'):
    try:
        dlg = find_dialog_elem_ui_auto(json_obj_elem, set_focus=True, check_visible=True, check_children=False)
    except Exception as e:
        traceback_str = traceback.format_exc().splitlines()
        line_description = traceback_str[-1] if traceback_str else str(e)
        print(json.dumps({"traceback": e, "count": -1, "status": False, "line_description": str(line_description)}))

    if not dlg:
        print(json.dumps({"count": 0, "status": False}))
    else:
        try:
            if not isinstance(dlg, list):
                draw_outline(cls=dlg, thickness=4)
                time.sleep(3)
                print(json.dumps({"count": 1, "status": True}))
            elif isinstance(dlg, list):
                for element in dlg:
                    draw_outline(cls=element, thickness=4, colour='red')
                time.sleep(3)
                print(json.dumps({"count": len(dlg), "status": True}))

        except Exception as e:
            traceback_str = traceback.format_exc().splitlines()
            line_description = traceback_str[-1] if traceback_str else str(e)
            print(
                json.dumps({"traceback": e, "count": -1, "status": False, "line_description": str(line_description)}))
else:
    Timings.window_find_timeout = 2.0
    dlg = find_dialog_elem(json_obj_elem, set_focus=True, check_visible=True)

    if not dlg:
        print(json.dumps({"count": 0, "status": False}))
    else:
        try:
            dlg.draw_outline(thickness=4)
            time.sleep(3)
            print(json.dumps({"count": 1, "status": True}))
        except ElementAmbiguousError as e:

            for element in e.elements:
                element = UIAWrapper(element)
                element.draw_outline(thickness=4, colour='red')
            time.sleep(3)
            print(json.dumps({"count": len(e.elements), "status": True}))
        except ElementNotFoundError:
            print(json.dumps({"count": 0, "status": False}))

        except Exception as e:
            traceback_str = traceback.format_exc().splitlines()
            line_description = traceback_str[-1] if traceback_str else str(e)
            print(json.dumps({"traceback": e, "count": -1, "status": False, "line_description": str(line_description)}))
