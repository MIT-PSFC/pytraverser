#!/usr/bin/env python3
# tree_select.py
import sys
import curses
import MDSplus
from typing import Callable, List, Optional, Tuple

GetChildrenFn = Callable[[MDSplus.TreeNode], List[MDSplus.TreeNode]]
def get_children(node: MDSplus.TreeNode) -> List[MDSplus.TreeNode]:
    # TreeGetChildren returns both members and children, so we combine them here
    # and return a list of (node_id, node_name) tuples for each child node.

    members = node.getMembers()
    children = node.getChildren()
    return members + children

class _Node:
    __slots__ = ("id", "label", "parent", "children", "loaded", "expanded")
    def __init__(self, node_id: MDSplus.TreeNode, parent: Optional["_Node"]=None):
        self.id = node_id
        self.label = node_id.name
        self.parent = parent
        self.children: List["_Node"] = []
        self.loaded = False
        self.expanded = False



def _build_visible(root: _Node) -> List[Tuple[_Node, int]]:
    out: List[Tuple[_Node,int]] = []
    def walk(n: _Node, depth: int):
        out.append((n, depth))
        if n.expanded:
            for c in n.children:
                walk(c, depth+1)
    walk(root, 0)
    return out

_HELP = "↑/↓ move  ← collapse  → expand  Enter toggle/select  space toggle  s select  q cancel"

def tree_select(root_id: MDSplus.TreeNode) -> Optional[List[str]]:
    """
    Open a terminal tree browser and return the selected path of node IDs
    (root->...->selected) or None if canceled.

    - get_children(node_id) must return a list of (child_id).
    - Lazy loads children on first expansion.
    - Key bindings:
        Up/Down: move
        Right:   expand (or select if leaf)
        Left:    collapse / go to parent
        Enter:   toggle expand (or select if leaf)
        Space:   toggle expand
        s:       select current
        q / ESC: cancel and return None
    """
    selected_path: Optional[List[str]] = None

    ALT_ENTER = b"\x1b[?1049h"  # ANSI fallback: enter alt screen
    ALT_EXIT  = b"\x1b[?1049l"  # ANSI fallback: exit alt screen

    def _enter_alt_screen():
        # Try terminfo capability first
        try:
            s = curses.tigetstr('smcup')
            if s:
                curses.putp(s.decode())
                sys.stdout.flush()
                return True
        except Exception:
            pass
        # Fallback: ANSI sequence
        sys.stdout.buffer.write(ALT_ENTER)
        sys.stdout.flush()
        return True

    def _exit_alt_screen():
        try:
            r = curses.tigetstr('rmcup')
            if r:
                curses.putp(r.decode())
                sys.stdout.flush()
                return
        except Exception:
            pass
        sys.stdout.buffer.write(ALT_EXIT)
        sys.stdout.flush()

    def _ui(stdscr):
        nonlocal selected_path
        _enter_alt_screen()
        if (curses.tigetstr('civis') is not None) and (curses.tigetstr('cnorm') is not None) :
            curses.curs_set(0)
        stdscr.keypad(True)

        # Build root
        root = _Node(root_id, None)
        try:
            kids = get_children(root_id)
        except Exception:
            kids = []
        root.children = [_Node(cid, root) for cid in kids]
        root.loaded = True
        root.expanded = True

        cursor = 0
        while True:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()
            visible = _build_visible(root)
            if visible:
                cursor = max(0, min(cursor, len(visible)-1))

            # header
            stdscr.addnstr(0, 0, _HELP, max_x-1)
            stdscr.hline(1, 0, curses.ACS_HLINE, max_x)

            # rows
            start_row = 2
            for i, (node, depth) in enumerate(visible):
                row = start_row + i
                if row >= max_y - 2:
                    break
#                is_leaf = node.loaded and not node.children
                is_leaf = node.id.number_of_children+node.id.number_of_members == 0
                marker = " " if is_leaf else ("▸" if not node.expanded else "▾")
                line = "  " * depth + f"{marker} {node.label}"
                attr = curses.A_REVERSE if i == cursor else curses.A_NORMAL
                stdscr.addnstr(row, 0, line, max_x-1, attr)

            # footer
            stdscr.hline(max_y-2, 0, curses.ACS_HLINE, max_x)
            if visible:
                cur = visible[cursor][0]
                info = f"Current: {cur.label} (id={cur.id})"
            else:
                info = "No nodes visible"
            stdscr.addnstr(max_y-1, 0, info, max_x-1)

            stdscr.refresh()
            ch = stdscr.getch()

            if ch in (ord('q'), 27):  # q or ESC
                selected_path = None
                break
            elif ch in (curses.KEY_UP, ord('k')):
                cursor = max(0, cursor-1)
            elif ch in (curses.KEY_DOWN, ord('j')):
                cursor = min(len(visible)-1, cursor+1) if visible else 0
            elif ch in (curses.KEY_RIGHT, ord('l')):
                if not visible: 
                    continue
                node, _ = visible[cursor]
                if not node.loaded:
                    kids = get_children(node.id)
                    node.children = [_Node(cid, node) for cid in kids]
                    node.loaded = True
                if node.children:
                    node.expanded = True
            elif ch in (curses.KEY_LEFT, ord('h')):
                if not visible: 
                    continue
                node, _ = visible[cursor]
                if node.expanded:
                    node.expanded = False
                elif node.parent is not None:
                    # move cursor to parent
                    parent = node.parent
                    pv = _build_visible(root)
                    for idx, (n, _) in enumerate(pv):
                        if n is parent:
                            cursor = idx
                            break
            elif ch in (10, 13):  # Enter
                if not visible:
                    continue
                node, _ = visible[cursor]
                if not node.loaded:
                    kids = get_children(node.id)
                    node.children = [_Node(cid, node) for cid in kids]
                    node.loaded = True
#                if node.children:
#                    node.expanded = not node.expanded
#                else:
                selected_path = node.id 
                break
            elif ch == ord(' '):  # space toggles
                if not visible:
                    continue
                node, _ = visible[cursor]
                if not node.loaded:
                    kids = get_children(node.id)
                    node.children = [_Node(cid, node) for cid in kids]
                    node.loaded = True
                node.expanded = not node.expanded if node.children else False
            elif ch == ord('s'):  # select current
                if visible:
                    selected_path = visible[cursor][0].id
                    break

        stdscr.erase()
    _exit_alt_screen()
    try:
        curses.wrapper(_ui)
    except KeyboardInterrupt:
        return None
    print()
    return selected_path

# ---------------- Example usage ----------------
if __name__ == "__main__":
    print("Opening tree browser for MDSplus tree 'cmod'...")
    tree = MDSplus.Tree("cmod", -1)
    start = tree._TOP
    
    print("Starting tree traversal from node:", start.getNodeName())
    print(tree_select(start))

    