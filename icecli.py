#!/usr/bin/env python3
import curses
import subprocess
import shlex
import sys
import argparse
import os
import json
import platform
import ast
import math
import operator
from time import sleep

PROGNAME = "IceCli"
PROGVER = "0.1"
FOOTER = "ESC/<:Exit|Enter/>Sel.|\\:Edit"
DEFAULT_EDITOR = "nano"
GUICMD = "xfce4-terminal --tab -e "
HISTORY = []

THEME_MONOKAI_256 = {
    "title":      (172, 16, curses.A_BOLD),
    "filter":     (148, -1, curses.A_BOLD),
    "normal":     (188, -1),
    "selected":   (16, 186, curses.A_BOLD),
    "menu":       (148, -1),
    "separator":  (101, -1),
    "path":       (116, -1),
    "bg":         (188, 16),
    "status":     (101, 16),
    "error":      (124, -1),
}

THEME_DARK_256 = {
    "title":      (180, 17, curses.A_BOLD),
    "filter":     (73, -1, curses.A_BOLD),
    "normal":     (145, -1),
    "selected":   (17, 108, curses.A_BOLD),
    "menu":       (73, -1),
    "separator":  (60, -1),
    "path":       (108, -1),
    "bg":         (145, 17),
    "status":     (60, 17),
    "error":      (124, -1),
}

THEME_DRACULA_256 = {
    "title":      (186, 140, curses.A_BOLD),
    "filter":     (116, 17, curses.A_BOLD),
    "normal":     (188, -1),
    "selected":   (17, 78, curses.A_BOLD),
    "menu":       (116, -1),
    "separator":  (67, -1),
    "path":       (78, -1),
    "bg":         (188, 17),
    "status":     (67, 17),
}

THEME_NORD_256 = {
    "title":      (188, 110, curses.A_BOLD),
    "filter":     (110, -1, curses.A_BOLD),
    "normal":     (188, -1),
    "selected":   (23, 110, curses.A_BOLD),
    "menu":       (110, -1),
    "separator":  (60, -1),
    "path":       (144, -1),
    "bg":         (188, 23),
    "status":     (60, 23),
    "error":      (124, -1),
}


THEME_16 = {
    "title":      (curses.COLOR_BLUE, curses.COLOR_WHITE),
    "filter":     (curses.COLOR_YELLOW, curses.COLOR_CYAN, curses.A_BOLD),
    "normal":     (curses.COLOR_WHITE, -1),
    "selected":   (curses.COLOR_YELLOW, curses.COLOR_BLUE, curses.A_BOLD),
    "menu":       (curses.COLOR_CYAN, -1),
    "separator":  (curses.COLOR_BLUE, -1),
    "path":       (curses.COLOR_GREEN, -1),
    "bg":         (curses.COLOR_BLACK, -1),
    "status":     (curses.COLOR_BLACK, curses.COLOR_WHITE),
    "error":      (curses.COLOR_RED, -1),
}

THEME_256 = {
    "title":      (226, 235, curses.A_BOLD),
    "filter":     (255, 235, curses.A_BOLD),
    "normal":     (252, 235),
    "selected":   (0, 214),
    "menu":       (3, 235),
    "separator":  (237, 235),
    "path":       (34, 235),
    "bg":         (7, 0),
    "status":     (240, 233),
    "error":      (124, 235),
}

THEME = THEME_16
COLOR = {}

# Calculator safe evaluation
def safe_eval(expression):
    """
    Safely evaluate mathematical expressions.
    Returns the result or None if evaluation fails.
    """
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
    }
    
    allowed_functions = {
        'abs': abs, 'round': round, 'min': min, 'max': max,
        'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
        'tan': math.tan, 'log': math.log, 'exp': math.exp,
        'pi': math.pi, 'e': math.e,
    }
    
    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            return allowed_operators[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.USub):
                return -operand
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in allowed_functions:
                    args = [_eval(arg) for arg in node.args]
                    return allowed_functions[func_name](*args)
        elif isinstance(node, ast.Name):
            if node.id in allowed_functions:
                return allowed_functions[node.id]
        raise ValueError(f"Unsupported expression: {expression}")
    
    try:
        tree = ast.parse(expression, mode='eval')
        result = _eval(tree.body)
        if isinstance(result, float):
            if result.is_integer():
                return str(int(result))
            return f"{result:.10g}".rstrip('0').rstrip('.')
        return str(result)
    except Exception:
        return None

def is_calculable(expression):
    """Check if the expression looks like a calculation."""
    if not expression:
        return False
    
    calc_chars = set('0123456789+-*/%().^sqrtcossin tanlogabsroundpi e')
    expression_lower = expression.lower()
    
    has_operators = any(op in expression for op in '+-*/%^')
    has_functions = any(func in expression_lower for func in ['sqrt', 'sin', 'cos', 'tan', 'log', 'abs', 'round'])
    has_numbers = any(c.isdigit() for c in expression)
    allowed = all(c.lower() in calc_chars or c.isspace() for c in expression)
    
    return allowed and (has_operators or has_functions) and has_numbers

def detect_platform():
    """
    Detect and return the specific platform/runtime environment.
    """
    # Check for Termux (Android terminal emulator)
    if 'com.termux' in sys.executable or os.path.exists('/data/data/com.termux'):
        return 'termux'

    system = platform.system().lower()
    # Check for Raspberry Pi
    if system == 'linux':
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read().lower()
                if 'raspberry' in cpuinfo or 'bcm' in cpuinfo:
                    return 'raspberry'
        except (IOError, PermissionError):
            pass
        return 'linux'
    return system

# ---------- Theme Support ----------

def check_colors():
    if curses.has_colors():
        num_colors = curses.COLORS
        if num_colors >= 256:
            # print("256-color mode available!")  # Optional log
            return True
        else:
            # print(f"Limited to {num_colors} colors.")
            return False
    else:
        # print("Terminal does not support colors.")
        return False


def init_colors():
    i = 1
    for name, spec in THEME.items():
        fg = spec[0] % curses.COLORS if curses.COLORS else 7
        bg = spec[1] % curses.COLORS if spec[1] != -1 else -1
        attr = spec[2] if len(spec) > 2 else 0
        curses.init_pair(i, fg, bg)
        COLOR[name] = curses.color_pair(i) | attr
        i += 1
        
def load_theme(path):
    global THEME

    namespace = {"curses": curses}

    try:
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        exec(code, namespace)

        if "THEME" not in namespace:
            raise ValueError("Theme file does not define THEME")

        THEME = namespace["THEME"]

    except Exception as e:
        print(f"Error loading theme '{path}': {e}", file=sys.stderr)
        sys.exit(1)

def create_theme(path):
    global THEME
    if os.path.exists(path):
        print(f"Refusing to overwrite existing file: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(
            "# IceMenu theme file\n"
            "# Edit freely.\n\n"
        )
        f.write(json.dumps(THEME, indent=4))

    print(f"Theme written to {path}")


# ---------- Execute Functions ---------

def execute(command,split:str=""):
    """Execute the program, handling tmux detection"""
    # Check if running inside tmux
    global GUICMD

    if os.environ.get('TMUX'):
        try:
            if split == "-":
                tmux_cmd = ['tmux', 'split-window', '-v', command]
            elif split == "|":
                tmux_cmd = ['tmux', 'split-window', '-h', command]
            else:
                tmux_cmd = ['tmux', 'new-window', command]
            #subprocess.Popen(tmux_cmd)
            subprocess.run(tmux_cmd)
            #os.system(tmux_cmd)
    
        except Exception as e:
            print(f"Error executing in tmux: {e}", file=sys.stderr)
            # Fall back to normal execution
            curses.endwin()
            os.system(f'{GUICMD} "{command}"')
            return
        
    else:
        curses.endwin()
        if split == "D":
            os.system(f'{GUICMD} "{command}" ')
        else:
            os.system(f'{GUICMD} "{command}"')
    return


# ---------- Menu Node Types ----------

class MenuNode: pass

class Program(MenuNode):
    def __init__(self, name, command, path, exist=True):
        self.name = name
        self.command = command
        self.path = path
        self.exist = exist

class Separator(MenuNode): pass

class Menu(MenuNode):
    def __init__(self, name, path):
        self.name = name
        self.items = []
        self.path = path

# ---------- Parser ----------

def parse_icewm_menu(path):
    root = Menu("IceWM Menu", [])
    stack = [root]

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("menu"):
                parts = shlex.split(line)
                name = parts[1]
                menu = Menu(name, stack[-1].path + [name])
                stack[-1].items.append(menu)
                stack.append(menu)
                continue

            if line == "}":
                stack.pop()
                continue

            if line.startswith("separator"):
                stack[-1].items.append(Separator())
                continue

            if line.startswith("prog"):
                parts = shlex.split(line)
                name = parts[1]
                command = " ".join(parts[3:])
                stack[-1].items.append(
                    Program(name, command, stack[-1].path + [name])
                )

    return root

# ---------- Various functions for menu ----------

def flatten_menu(menu):
    result = []
    for item in menu.items:
        if isinstance(item, Program):
            result.append(item)
        elif isinstance(item, Menu):
            result.extend(flatten_menu(item))
    return result

# ---------- UI ----------

def draw_full_screen(stdscr, title, filter_text, visible, selection, scroll, ifooter):
    """Draw the entire screen"""
    h, w = stdscr.getmaxyx()
    view_height = h - 5
    
    # Header
    stdscr.addstr(0, 0, title[:w].ljust(w), COLOR["title"])
    
    # Filter line
    stdscr.addstr(1, 0, ": ", COLOR["filter"])
    stdscr.addstr(filter_text.ljust(w-2), COLOR["filter"] | curses.A_BOLD)
    
    # Draw all items
    for i in range(scroll, min(scroll + view_height, len(visible))):
        y = 2 + i - scroll
        item = visible[i]
        
        if isinstance(item, Separator):
            stdscr.addstr(y, 0, "-"*w, COLOR["separator"])
        else:
            if hasattr(visible[0], 'path') and len(visible[0].path) > 1:  # Show paths in search
                label = " > ".join(item.path)
                color = COLOR["path"]
            elif isinstance(item, Menu):
                label = item.name + " >"
                color = COLOR["menu"]
            else:
                label = item.name
                color = COLOR["normal"]
            
            if i == selection:
                stdscr.addstr(y, 0, label[:w - 4].ljust(w), COLOR["selected"])
            else:
                stdscr.addstr(y, 0, label[:w - 4].ljust(w), color)
    
    # Clear remaining lines
    for i in range(len(visible) - scroll, view_height):
        y = 2 + i
        if y < h - 2:
            stdscr.addstr(y, 0, " ".ljust(w), COLOR["normal"])
    
    # Footer
    stdscr.addstr(h-1, 0, ifooter[:w-1].ljust(w-1), COLOR["status"])
    stdscr.refresh()

def update_selection(stdscr, visible, old_selection, new_selection, scroll, w):
    """Update only the selection highlighting"""
    h, _ = stdscr.getmaxyx()
    view_height = h - 5
    
    # Unhighlight old selection if visible
    if old_selection >= scroll and old_selection < scroll + view_height:
        y = 2 + old_selection - scroll
        item = visible[old_selection]
        
        if isinstance(item, Separator):
            stdscr.addstr(y, 0, "-"*w, COLOR["separator"])
        else:
            if hasattr(visible[0], 'path') and len(visible[0].path) > 1:
                label = " > ".join(item.path)
                color = COLOR["path"]
            elif isinstance(item, Menu):
                label = item.name + " >"
                color = COLOR["menu"]
            else:
                label = item.name
                color = COLOR["normal"]
            
            stdscr.addstr(y, 0, label[:w - 4].ljust(w), color)
    
    # Highlight new selection if visible
    if new_selection >= scroll and new_selection < scroll + view_height:
        y = 2 + new_selection - scroll
        item = visible[new_selection]
        
        if not isinstance(item, Separator):
            if hasattr(visible[0], 'path') and len(visible[0].path) > 1:
                label = " > ".join(item.path)
            elif isinstance(item, Menu):
                label = item.name + " >"
            else:
                label = item.name
            
            stdscr.addstr(y, 0, label[:w - 4].ljust(w), COLOR["selected"])
    
    stdscr.refresh()

def run_menu(stdscr, root, menu_path=None):
    global FOOTER, HISTORY
    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.bkgd(' ', COLOR['bg'])

    all_programs = flatten_menu(root)

    menu_stack = [root]
    selection = 0
    filter_text = ""
    ifooter = FOOTER
    scroll = 0
    visible = []
    last_selection = -1
    last_scroll = -1
    last_filter_text = ""
    last_menu_stack_len = 1
    
    while True:
        h, w = stdscr.getmaxyx()
        view_height = h - 5

        # Determine visible items
        show_paths = False
        if filter_text:
            visible = [
                p for p in all_programs
                if filter_text.lower() in " → ".join(p.path).lower() or filter_text.lower() in p.command.lower()
            ]
            show_paths = True
        else:
            current = menu_stack[-1]
            visible = current.items
            show_paths = False

        no_matches = filter_text and len(visible) == 0

        # Clamp selection
        selection = max(0, min(selection, len(visible) - 1 if visible else 0))

        # Scroll handling
        if selection < scroll:
            scroll = selection
        elif selection >= scroll + view_height and view_height > 0:
            scroll = selection - view_height + 1

        # Title
        title = " > ".join(menu_stack[-1].path) if not filter_text else "Search results"
        if not title:
            title = PROGNAME.rjust(w)

        # Check if we need full redraw
        need_full_redraw = (
            last_filter_text != filter_text or
            last_menu_stack_len != len(menu_stack) or
            last_scroll != scroll or
            last_selection == -1 or
            (last_selection >= 0 and (selection < scroll or selection >= scroll + view_height))
        )

        if need_full_redraw:
            draw_full_screen(stdscr, title, filter_text, visible, selection, scroll, ifooter)
            last_selection = selection
            last_scroll = scroll
            last_filter_text = filter_text
            last_menu_stack_len = len(menu_stack)
        else:
            # Just update selection if it changed and is visible
            if last_selection != selection and selection >= scroll and selection < scroll + view_height:
                update_selection(stdscr, visible, last_selection, selection, scroll, w)
                last_selection = selection
                
                # Update footer for program commands
                if visible and selection < len(visible) and isinstance(visible[selection], Program):
                    ifooter = visible[selection].command
                    # Update footer
                    stdscr.addstr(h-1, 0, ifooter[:w-1].ljust(w-1), COLOR["status"])
                    stdscr.refresh()
        
        key = stdscr.getch()

        # ---------- Key Handling ----------
        old_selection = selection

        if key in (curses.KEY_UP, ord('K')):
            selection -= 1
            
            if selection < 0:
                selection = len(visible) - 1
            
            # Skip separators
            while visible and selection >= 0 and isinstance(visible[selection], Separator):
                selection -= 1
                if selection < 0:
                    selection = len(visible) - 1

        elif key in (curses.KEY_DOWN, ord('J')):
            selection += 1
            
            if selection > len(visible) - 1:
                selection = 0
            
            # Skip separators
            while visible and selection < len(visible) and isinstance(visible[selection], Separator):
                selection += 1
                if selection >= len(visible):
                    selection = 0

        elif key == curses.KEY_PPAGE:  
            selection -= view_height
            if selection < 0:
                selection = 0

        elif key == curses.KEY_NPAGE:  
            selection += view_height
            if selection >= len(visible):
                selection = len(visible) - 1

        elif key == curses.KEY_HOME:
            ifooter = FOOTER
            selection = 0
            # Skip separator at start
            while visible and isinstance(visible[selection], Separator):
                selection += 1

        elif key == curses.KEY_END:
            ifooter = FOOTER
            selection = len(visible) - 1
            # Skip separator at end
            while visible and isinstance(visible[selection], Separator):
                selection -= 1

        elif key in (curses.KEY_BACKSPACE, 127, 8):
            filter_text = filter_text[:-1]
            selection = scroll = 0
        
        elif key == ord('\\'):  # Backslash to edit menu
            if not menu_path:
                continue
            
            curses.endwin()
            editor = os.environ.get('EDITOR') or DEFAULT_EDITOR
            
            try:
                execute(f"{editor} {menu_path}")
                root = parse_icewm_menu(menu_path)
                all_programs = flatten_menu(root)
                menu_stack = [root]
                selection = 0
                filter_text = ""
                scroll = 0
            except Exception as e:
                print(f"Error editing menu: {e}")
                input("Press Enter to continue...")
            HISTORY.clear()
            curses.initscr()
            curses.start_color()
            curses.use_default_colors()
            init_colors()
            stdscr.keypad(True)
            curses.curs_set(0)
            last_selection = -1  # Force full redraw
            continue

        elif key in (10, 13, curses.KEY_RIGHT, ord("-"), ord("|"), ord("D")):  # Enter
            if not visible:
                if is_calculable(filter_text):
                    calc_result = safe_eval(filter_text)
                    filter_text = str(calc_result)
                continue
            item = visible[selection]
            if isinstance(item, Program):
                curses.endwin()
                if key in (ord("-"), ord("|"), ord("D")):
                    execute(item.command, chr(key))
                else:
                    execute(item.command)
                return
            elif isinstance(item, Menu):
                HISTORY.append(selection)
                menu_stack.append(item)
                filter_text = ""
                ifooter = FOOTER
                selection = scroll = 0

        elif key in (27, curses.KEY_LEFT):  # ESC
            if filter_text:
                filter_text = ""
            elif len(menu_stack) > 1:
                menu_stack.pop()
            else:
                break
            
            if HISTORY:
                selection = HISTORY[-1]
                HISTORY.pop()
                continue

        elif 32 <= key <= 126:
            filter_text += chr(key)
            selection = scroll = 0
            HISTORY.clear()

        # Ensure selection is valid
        if visible:
            selection = max(0, min(selection, len(visible) - 1))

# ---------- Main ----------

def main():
    global THEME
    parser = argparse.ArgumentParser(
        description="""IceCli | terminal menu that uses IceWM config file\n
Press \\ to edit menu"""
    )

    parser.add_argument(
        "menu",
        nargs="?",
        help="Path to IceWM menu file"
    )

    parser.add_argument(
        "--save-theme",
        metavar="FILE",
        help="Save current theme file and exit"
    )

    args = parser.parse_args()

    THEME = THEME_16

    if args.save_theme:
        create_theme(args.save_theme)
        return

    if not args.menu:
        parser.error("menu file required unless --create-theme is used")

    system = detect_platform()
    if os.path.isfile(f"{args.menu}.{system}"):
        root = parse_icewm_menu(f"{args.menu}.{system}")
    else:
        root = parse_icewm_menu(args.menu)

    curses.initscr()
    curses.start_color()
    curses.use_default_colors()
    supports_256 = check_colors()
    if supports_256:
        THEME = THEME_256 
    else:
        THEME = THEME_16  
    
    init_colors()
    init_colors()

    curses.wrapper(run_menu, root, args.menu)

if __name__ == "__main__":
    main()
