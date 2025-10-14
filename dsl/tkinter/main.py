# draw_state_machine.py

import tkinter as tk
from tkinter import simpledialog, Toplevel, Text, Scrollbar, VERTICAL, RIGHT, Y, END, messagebox, StringVar
import math

class State:
    def __init__(self, name, x, y, kind="Normal", initial=False):
        self.name = name
        self.x = x
        self.y = y
        self.kind = kind
        self.initial = initial
        self.width = 100
        self.height = 60

class Transition:
    def __init__(self, src, dst, label=""):
        self.src = src
        self.dst = dst
        self.label = label
        self.text_id = None
        self.rect_id = None

class StateMachineDrawer:
    def __init__(self, root):
        self.root = root
        self.root.title("Draw State Machine")

        self.panel = tk.Frame(root)
        self.panel.pack(side=tk.LEFT, fill=tk.Y)

        self.edit_mode = tk.BooleanVar(value=False)
        self.edit_toggle = tk.Checkbutton(self.panel, text="Edit Mode", variable=self.edit_mode)
        self.edit_toggle.pack(pady=5)

        self.initial_state_var = tk.BooleanVar()
        self.initial_checkbox = tk.Checkbutton(self.panel, text="Initial", variable=self.initial_state_var)
        self.initial_checkbox.pack(pady=10)

        self.state_kind_var = StringVar(value="Normal")
        self.kinds = ["Always", "Normal", "Hot", "Error", "Ok", "Transition"]

        self.canvas = tk.Canvas(root, width=800, height=600, bg="white")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(self.panel, text="Click to Add State:").pack()
        for kind in self.kinds:
            icon = "✔" if kind == "Ok" else "✖" if kind == "Error" else ("♻" if kind == "Always" else "🔥" if kind == "Hot" else "➡" if kind == "Transition" else "⬤")
            b = tk.Button(self.panel, text=f"{icon} {kind}", width=12, command=lambda k=kind: self.set_current_state_kind(k))
            b.pack(pady=2)

        self.current_state_kind = "Normal"

        self.states = []
        self.transitions = []
        self.dragging_state = None
        self.transition_start = None
        self.selected_state = None

        self.canvas.bind("<Button-1>", self.left_click)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.drop)
        self.canvas.bind("<Button-3>", self.right_click)
        self.root.bind("<Command-x>", self.command_x)

        export_btn = tk.Button(self.panel, text="Export State Machine", command=self.export)
        export_btn.pack(pady=20)

    def set_current_state_kind(self, kind):
        self.current_state_kind = kind

    def left_click(self, event):
        clicked_state = self.get_state_at(event.x, event.y)
        self.selected_state = clicked_state  # Ensure selected_state is updated

        if self.edit_mode.get():
            if clicked_state and clicked_state.kind not in ["Error", "Ok"]:
                new_name = simpledialog.askstring("Edit State Name", "New name:", initialvalue=clicked_state.name)
                if new_name:
                    clicked_state.name = new_name
                    self.redraw()
                return
            for t in self.transitions:
                if t.text_id:
                    bbox = self.canvas.bbox(t.text_id)
                    if bbox and bbox[0] <= event.x <= bbox[2] and bbox[1] <= event.y <= bbox[3]:
                        new_label = self.multiline_input("Edit Transition Label", initial=t.label)
                        if new_label is not None:
                            t.label = new_label
                            self.redraw()
                        return
            return

        if self.current_state_kind == "Transition":
            if clicked_state:
                if self.transition_start:
                    if clicked_state != self.transition_start:
                        label = self.multiline_input("Transition label")
                        self.transitions.append(Transition(self.transition_start, clicked_state, label or ""))
                        self.transition_start = None
                        self.redraw()
                    else:
                        self.transition_start = None
                        self.redraw()
                else:
                    self.transition_start = clicked_state
                    self.redraw()
            return

        if clicked_state is None:
            name = "" if self.current_state_kind in ["Error", "Ok"] else simpledialog.askstring("Input", "State name:", parent=self.root)
            if name is None and self.current_state_kind not in ["Error", "Ok"]:
                return
            new_state = State(
                name,
                event.x,
                event.y,
                kind=self.current_state_kind,
                initial=self.initial_state_var.get()
            )
            self.states.append(new_state)
            self.redraw()

    def drag(self, event):
        if not self.dragging_state:
            self.dragging_state = self.get_state_at(event.x, event.y)
        if self.dragging_state:
            self.dragging_state.x = event.x
            self.dragging_state.y = event.y
            self.redraw()

    def drop(self, event):
        self.dragging_state = None

    def right_click(self, event):
        clicked_state = self.get_state_at(event.x, event.y)
        if clicked_state:
            self.selected_state = clicked_state  # Set selected state so Command-x works
            if messagebox.askyesno("Delete", f"Delete state '{clicked_state.name}'?"):
                self.states = [s for s in self.states if s != clicked_state]
                self.transitions = [t for t in self.transitions if t.src != clicked_state and t.dst != clicked_state]
                self.selected_state = None
                self.redraw()

    def command_x(self, event):
        if self.selected_state:
            if messagebox.askyesno("Delete", f"Delete state '{self.selected_state.name}'?"):
                self.states = [s for s in self.states if s != self.selected_state]
                self.transitions = [t for t in self.transitions if t.src != self.selected_state and t.dst != self.selected_state]
                self.selected_state = None
                self.redraw()

    def multiline_input(self, title, initial=""):
        dialog = Toplevel(self.root)
        dialog.title(title)
        text_widget = Text(dialog, wrap="word", height=10, width=40)
        text_widget.insert("1.0", initial)
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar = Scrollbar(dialog, command=text_widget.yview, orient=VERTICAL)
        scrollbar.pack(side=RIGHT, fill=Y)
        text_widget.config(yscrollcommand=scrollbar.set)

        dialog.resizable(True, True)

        result = {}

        def submit():
            result["text"] = text_widget.get("1.0", END).strip()
            dialog.destroy()

        submit_btn = tk.Button(dialog, text="OK", command=submit)
        submit_btn.pack()
        text_widget.focus_set()
        self.root.wait_window(dialog)
        return result.get("text", None)

    def export(self):
        result = {
            "states": [s.name for s in self.states],
            "transitions": [(t.src.name, t.dst.name, t.label) for t in self.transitions]
        }
        print(result)

    def get_state_at(self, x, y):
        for state in self.states:
            left = state.x - state.width // 2
            right = state.x + state.width // 2
            top = state.y - state.height // 2
            bottom = state.y + state.height // 2
            if left <= x <= right and top <= y <= bottom:
                return state
        return None

    def redraw(self):
        self.canvas.delete("all")
        for t in self.transitions:
            self.draw_arrow(t.src.x, t.src.y, t.dst.x, t.dst.y, t.label)
        for s in self.states:
            fill = {
                "Always": "lightgreen",
                "Normal": "white",
                "Hot": "yellow",
                "Error": "red",
                "Ok": "lightblue"
            }.get(s.kind, "white")
            text = {
                "Error": "✖",
                "Ok": "✔"
            }.get(s.kind, s.name)
            self.canvas.create_rectangle(s.x - s.width // 2, s.y - s.height // 2, s.x + s.width // 2, s.y + s.height // 2,
                                         fill=fill, outline="black", width=2)
            self.canvas.create_text(s.x, s.y, text=text)
            if s.initial:
                self.canvas.create_line(s.x - s.width // 2 - 20, s.y, s.x - s.width // 2, s.y, arrow=tk.LAST, fill="black", width=2)
        if self.transition_start:
            self.canvas.create_rectangle(
                self.transition_start.x - self.transition_start.width // 2 - 4,
                self.transition_start.y - self.transition_start.height // 2 - 4,
                self.transition_start.x + self.transition_start.width // 2 + 4,
                self.transition_start.y + self.transition_start.height // 2 + 4,
                outline="blue", dash=(3, 3)
            )

    def draw_arrow(self, x1, y1, x2, y2, label=""):
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist == 0:
            return
        offset = 30
        ratio = (dist - offset) / dist
        x1_adj = x1 + dx * offset / dist
        x2_adj = x1 + dx * ratio
        y1_adj = y1 + dy * offset / dist
        y2_adj = y1 + dy * ratio
        self.canvas.create_line(x1_adj, y1_adj, x2_adj, y2_adj, arrow=tk.LAST, width=2)
        if label:
            mx = (x1_adj + x2_adj) / 2
            my = (y1_adj + y2_adj) / 2
            text_id = self.canvas.create_text(mx, my, text=label, anchor="nw", width=200, justify="left", tags="label")
            bbox = self.canvas.bbox(text_id)
            if bbox:
                rect_id = self.canvas.create_rectangle(bbox, fill="white", outline="gray", tags="label")
                self.canvas.tag_lower(rect_id, text_id)
            for t in self.transitions:
                if t.src.x == x1 and t.dst.x == x2 and t.src.y == y1 and t.dst.y == y2 and t.label == label:
                    t.text_id = text_id
                    t.rect_id = rect_id

if __name__ == "__main__":
    root = tk.Tk()
    app = StateMachineDrawer(root)
    root.mainloop()
