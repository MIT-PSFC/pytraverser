#!/usr/bin/env python
#from mdsthin import MDSplus
import MDSplus
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Tree, Static, Button
from textual.widgets.tree import TreeNode
from textual.widget import Widget
from textual.reactive import reactive
from rich.table import Table
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual import events
from textual import on
from textual.events import Key

import argparse

def _is_expanded(node) -> bool:
    """Best-effort check across Textual versions."""
    if hasattr(node, "is_expanded"):
        val = node.is_expanded
        return bool(val() if callable(val) else val)
    if hasattr(node, "expanded"):
        val = node.expanded
        return bool(val() if callable(val) else val)
    return False

def walk_visible(node, *, include_self: bool = True):
    """Yield TreeNode objects that are currently visible in the tree.

    Pre-order: parent first, then children (only if parent is expanded).
    """
    if include_self:
        yield node
    if _is_expanded(node):
        # Maintain on-screen order
        for child in getattr(node, "children", []) or []:
            yield from walk_visible(child, include_self=True)

class ReprPopup(ModalScreen[None]):
    """Simple popup to display repr(text)."""
    def __init__(self, text: str) -> None:
        super().__init__()
        self._text = text

    def compose(self) -> ComposeResult:
        # Minimal centered vertical stack
        yield Vertical(
            Static(self._text, id="repr-text"),
            Button("Close", id="close"),
            id="popup",
        )
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

class NodeFooter(Widget):
    # Reactive fields update the render automatically
    status: str = reactive("off")
    path: str = reactive("-")
    usage: str = reactive("-")
    datatype: str = reactive("-")
    length: str = reactive("-")
    tags: str = reactive("-")

    def on_mount(self) -> None:
        self.styles.dock = "bottom"
        self.styles.height = 3
#        self.styles.background = "transparent"

    def render(self):
        row1 = Table.grid(expand=True); row1.add_row(f"Status: {self.status}", f"Path: {self.path}")
        row2 = Table.grid(expand=True); row2.add_row(f"Usage: {self.usage}", f"Datatype: {self.datatype}", f"Length: {self.length}")
        row3 = Table.grid(expand=True); row3.add_row(f"Tags: {self.tags}")
        outer = Table.grid(expand=True)
        outer.add_row(row1); outer.add_row(row2); outer.add_row(row3)
        return outer

    def update_fields(self, *, status, path, usage, datatype, length, tags) -> None:
        self.status = status
        self.path = path
        self.usage = usage
        self.datatype = datatype
        self.length = length
        self.tags = tags

class MDSplusTreeApp(App):
    """A Textual app for browsing an MDSplus tree."""

    BINDINGS = [       
        ("q", "quit", "Quit"),
    ]

    CSS = """
    ReprPopup {
        align: center middle;
    }
    #popup {
        padding: 1 2;
        border: round $accent;
        background: $panel;
        width: 80%;
        max-width: 80;
    }
    #repr-text {
        height: auto;
        max-height: 20;
        overflow: auto;
    }

    """
    def __init__(self, tree_name: str, shot_number: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree_name = tree_name
        self.shot_number = shot_number
        self.mds_tree = None
        self.selected = None

    class HeaderBar(Static):
        def on_mount(self):
            self.update(
                "[b][click][/b]/[b]⏎[/b] expand + select + decompile   "
                "[b]⇧⏎[/b] expand + select + show data   "
                "[b]←[/b] collapse parent   "
                "[b]→[/b] expand   "
                "[b]↓[/b] move down + expand   "
                "[b]↑[/b] move up + expand"
            )

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield self.HeaderBar()
        with Container(id="main_container"):
            yield Tree(self.tree_name, id="tree_view")
        yield NodeFooter(id="footer")

    def on_mount(self) -> None:
        """Connect to the MDSplus tree and populate the root node."""
        self.styles.dock = "bottom"
        self.styles.height = 3
#        self.styles.background = "transparent"

        try:
            self.mds_tree = MDSplus.Tree(self.tree_name, self.shot_number)
            root_node = self.mds_tree.getNode("\\TOP")
            tree_widget = self.query_one(Tree)
            
            # The root of our Textual tree represents the MDSplus TOP node.
            textual_root = tree_widget.root
            textual_root.set_label(f"{self.tree_name.upper()} :: TOP")
            textual_root.data = root_node
            
            # Prepare the initial children of the root node for lazy loading.
            self.prepare_mds_node(textual_root)
            textual_root.expand()

        except Exception as e:
            self.log.error(f"Failed to open MDSplus tree: {e}")
            self.query_one(Tree).root.set_label(f"ERROR: Could not open tree '{self.tree_name}'")

    def prepare_mds_node(self, node: TreeNode) -> None:
        """Checks an MDSplus node and sets the Textual node to be expandable if it has children or members."""
        mds_node = node.data
        if mds_node.getNumDescendants() > 0:
            node.allow_expand = True

    def expand_mds_node(self, parent_widget: TreeNode) -> None:
        """Populates the Textual tree with children and members of an MDSplus node."""
        self._saved_focus = self.app.focused  # store currently focused widget
        self.app.set_focus(None)              # clear focus

        parent_widget.remove_children()
        mds_parent = parent_widget.data

        # Add member nodes first
        for mds_member in mds_parent.getMembers():
            if mds_member.number_of_descendants > 0:
                member_node = parent_widget.add(f"{mds_member.getNodeName()}")
            else:
                member_node = parent_widget.add_leaf(f":{mds_member.getNodeName()}")

            member_node.data = mds_member
            self.prepare_mds_node(member_node)
            
        # Then add child nodes
        for mds_child in mds_parent.getChildren():
            child_node = parent_widget.add(f".{mds_child.getNodeName()}")
            child_node.data = mds_child
            self.prepare_mds_node(child_node)
        
        parent_widget.loaded = True
        if self._saved_focus:
            self.app.set_focus(self._saved_focus)
        
    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Lazy-load the children and members of an MDSplus node when its Textual representation is expanded."""
        node = event.node
    
        if not hasattr(node, "loaded"):

            def load_and_populate():
                """A worker function to load the children and update the UI."""
                self.call_from_thread(self.expand_mds_node, node)
            
            self.run_worker(load_and_populate, exclusive=True, thread=True)

    # Tree selection handler: push the selected node's data into the footer
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        tree = self.query_one(Tree)
        selected_node = tree.cursor_node
        # data = selected_node.data
        # text = None
        # try:
        #     self.selected = data
        #     text = data.record.decompile()
        # except Exception as e:
        #     pass
        # if text is not None:
        #     self.push_screen(ReprPopup(text))


    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        footer = self.query_one(NodeFooter)
        data = event.node.data
        if data is not None:
            footer.update_fields(
                status="[green]On" if data.on else "[red]off",
                path=data.fullpath,
                usage=data.usage,
                datatype=data.dtype_str,
                length = "[red] 0" if data.length == 0 else str(data.length),            
                tags=', '.join(str(tag) for tag in data.tags)
            )
    @on(Key)  # app-wide
    def handle_tab(self, event: Key) -> None:
        if event.key in ("tab","enter") and self.focused and self.focused.id != "close":
            tree = self.query_one(Tree)
            selected_node = tree.cursor_node
            data = selected_node.data
            text = None
            if (event.key == "tab") and (self.focused is not None):
                try:
                    self.selected = data
                    text = str(data.data())
                except Exception as e:
                    return None
            elif event.key == "enter":
                try:
                    self.selected = data
                    text = data.record.decompile()
                except Exception as e:
                    return None
            if text is not None:
                self.push_screen(ReprPopup(text))
            return
        else:
            return None

    def key_right(self) -> None:
        """Expand the current node on → key."""
        tree = self.query_one(Tree)
        if tree.cursor_node:
            tree.cursor_node.expand()

    # def do_enter(self) -> None:
    #     tree = self.query_one(Tree)
    #     selected_node = tree.cursor_node
    #     data = selected_node.data
    #     text = None
    #     try:
    #         self.selected = data
    #         text = data.record.decompile()
    #     except Exception as e:
    #         pass
    #     if text is not None:
    #         self.push_screen(ReprPopup(text))
        
    def key_left(self) -> None:
        """If current node is expanded, collapse it; else collapse parent and center it."""
        def visible_line_for_node(tree: Tree, target) -> int | None:
            """Return the visible line number for a node, or None if not visible."""
            line = 0
            for node in walk_visible(tree.root):
                # Only count lines that are currently visible (i.e., within expanded branches)
                if node is target:
                    return line
                line += 1
            return None
    

        tree = self.query_one(Tree)
        node = tree.cursor_node
        if not node:
            return

        parent = node.parent
        if not parent:
            return

        # Collapse parent, then move cursor to parent and center it.
        parent.collapse()

        # Move the cursor to the parent (we need a visible line index to set cursor_line).
        line = visible_line_for_node(tree, parent)
        if line is None:
            # Parent not visible (e.g., higher ancestor collapsed) — expand ancestors so it becomes visible
            a = parent
            while a and not a.is_visible:
                if a.parent:
                    a.parent.expand()
                a = a.parent
            line = visible_line_for_node(tree, parent)

        if line is None:
            return  # still couldn't resolve (shouldn't happen, but be safe)

        tree.cursor_line = line


        def center_after_layout() -> None:
            tree = self.query_one(Tree)
            # Viewport height (after render)
            viewport_h = getattr(getattr(tree, "size", None), "height", 0)
            if viewport_h <= 0:
                return

            # Total scrollable content height (if available)
            content_h = getattr(getattr(tree, "virtual_size", None), "height", 0)

            # Compute desired top so the target 'line' is roughly centered
            target_y = max(0, line - viewport_h // 2)

            # Clamp to max scroll if we know content height
            if content_h and content_h > viewport_h:
                max_scroll = content_h - viewport_h
                target_y = min(target_y, max_scroll)
            else:
                # No need to scroll if content fits
                target_y = 0

            # Prefer modern API signatures; fall back gracefully
            if hasattr(tree, "scroll_to"):
                try:
                    tree.scroll_to(y=target_y)
                except TypeError:
                    tree.scroll_to(0, target_y)   # older versions need x,y
            elif hasattr(tree, "scroll_y"):
                tree.scroll_y = target_y
            elif hasattr(tree, "scroll_to_region"):
                tree.scroll_to_region(0, target_y, 1, 1)
        self.call_after_refresh(center_after_layout)

def parse_args():
    parser = argparse.ArgumentParser(description="Tree, optional shot, dark flag")

    # Required positional argument
    parser.add_argument("tree", type=str, help="Tree string")

    # Optional positional argument (int)
    parser.add_argument("shot", type=int, nargs="?", default=-1, help="Optional shot number (default -1)")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--dark', action='store_true', help='Enable dark mode')
    group.add_argument('-l', '--light', action='store_true', help='Enable light mode')

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Example usage: Replace 'your_tree_name' and '1' with actual values.
    app = MDSplusTreeApp(args.tree, args.shot) 
    app.run()
    print("Selected node:", app.selected)