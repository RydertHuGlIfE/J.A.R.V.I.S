import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re
import tkinter as tk
from tkinter import Frame, Label, Button, Entry, PhotoImage, messagebox

# Constants
DARK_BG = "#0A0F14"
ACCENT_COLOR = "#00B8D4"
ACCENT_COLOR_SECONDARY = "#00E5FF"
TEXT_COLOR = "#E2F1F8"
ENTRY_BG = "#111C26"
BUTTON_BG = "#00B8D4"
BUTTON_FG = "#0A0F14"
ACTIVE_GREEN = "#00E676"
INACTIVE_RED = "#FF1744"
GRADIENT_TOP = "#0A0F14"
GRADIENT_BOTTOM = "#172A3A"

plot_frame = None 
FONT_NAME = "Consolas"
HEADER_FONT = (FONT_NAME, 18, "bold")
NORMAL_FONT = (FONT_NAME, 12)
BUTTON_FONT = (FONT_NAME, 12, "bold")
STATUS_FONT = (FONT_NAME, 10)

# Animated button effect
class HoverButton(Button):
    def __init__(self, master, **kw):
        super().__init__(master=master, **kw)
        self.defaultBackground = self["background"]
        self.defaultForeground = self["foreground"]
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self['background'] = ACCENT_COLOR_SECONDARY
        self['foreground'] = BUTTON_FG

    def on_leave(self, e):
        self['background'] = self.defaultBackground
        self['foreground'] = self.defaultForeground

def create_graph():
    global plot_frame
    # Instead of creating a new Toplevel, use the main root window.
    graph_window = root
    graph_window.title("JARVIS Graph Plotter")
    # Set the desired geometry for the graph plotter directly on root.
    graph_window.geometry("1300x900")
    graph_window.configure(bg=DARK_BG)

    # Clear any existing widgets in root (if needed)
    for widget in graph_window.winfo_children():
        widget.destroy()

    input_frame = Frame(graph_window, bg=DARK_BG, padx=20, pady=20)
    input_frame.pack(fill="x")

    Label(input_frame, text="Enter relation between x and y (e.g., y = x**2 + 3*x - 2):",
          bg=DARK_BG, fg=TEXT_COLOR, font=NORMAL_FONT).pack(side="left")

    relation_entry = Entry(input_frame, bg=ENTRY_BG, fg=TEXT_COLOR, font=NORMAL_FONT, width=40)
    relation_entry.pack(side="left", padx=10)
    relation_entry.insert(0, "y = x**2")

    # Initialize the global plot_frame
    plot_frame = Frame(graph_window, bg=ENTRY_BG, padx=20, pady=20)
    plot_frame.pack(fill="both", expand=True)

    # Add range controls
    range_frame = Frame(input_frame, bg=DARK_BG)
    range_frame.pack(side="left", padx=20)

    Label(range_frame, text="X Min:", bg=DARK_BG, fg=TEXT_COLOR, font=NORMAL_FONT).grid(row=0, column=0)
    x_min_entry = Entry(range_frame, bg=ENTRY_BG, fg=TEXT_COLOR, font=NORMAL_FONT, width=5)
    x_min_entry.grid(row=0, column=1, padx=5)
    x_min_entry.insert(0, "-10")

    Label(range_frame, text="X Max:", bg=DARK_BG, fg=TEXT_COLOR, font=NORMAL_FONT).grid(row=0, column=2)
    x_max_entry = Entry(range_frame, bg=ENTRY_BG, fg=TEXT_COLOR, font=NORMAL_FONT, width=5)
    x_max_entry.grid(row=0, column=3, padx=5)
    x_max_entry.insert(0, "10")

    def plot_graph_with_range():
        global plot_frame
        try:
            x_min = float(x_min_entry.get())
            x_max = float(x_max_entry.get())

            relation = relation_entry.get().strip()
            if relation.startswith("y = "):
                relation = relation[4:]
            elif relation.startswith("y="):
                relation = relation[2:]

            x = np.linspace(x_min, x_max, 1000)

            code = compile(f"def f(x): return {relation}", "<string>", "exec")
            namespace = {}
            exec(code, {"np": np, "sin": np.sin, "cos": np.cos, "tan": np.tan,
                        "exp": np.exp, "log": np.log, "sqrt": np.sqrt}, namespace)
            f = namespace["f"]

            y = f(x)

            # Destroy current plot_frame if it exists
            if plot_frame is not None:
                plot_frame.destroy()

            # Create a new plot_frame and update the global variable
            plot_frame = Frame(graph_window, bg=ENTRY_BG, padx=20, pady=20)
            plot_frame.pack(fill="both", expand=True)

            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(x, y, color=ACCENT_COLOR)
            ax.set_title(f"Graph of y = {relation}")
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.grid(True)
            ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
            ax.axvline(x=0, color='k', linestyle='-', alpha=0.3)

            canvas = FigureCanvasTkAgg(fig, master=plot_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

        except Exception as e:
            messagebox.showerror("Error", f"Error plotting graph: {str(e)}")

    plot_button = HoverButton(input_frame, text="PLOT", command=plot_graph_with_range,
                              bg=BUTTON_BG, fg=BUTTON_FG, font=BUTTON_FONT,
                              relief="flat", padx=15, pady=5)
    plot_button.pack(side="left", padx=10)

    # Add functionality for common functions
    functions_frame = Frame(graph_window, bg=DARK_BG, padx=20, pady=10)
    functions_frame.pack(fill="x")

    Label(functions_frame, text="Common Functions:", bg=DARK_BG, fg=TEXT_COLOR, font=NORMAL_FONT).pack(side="left")

    common_functions = [
        ("y = x**2", "Quadratic"),
        ("y = np.sin(x)", "Sine"),
        ("y = np.cos(x)", "Cosine"),
        ("y = np.exp(x)", "Exponential"),
        ("y = np.log(abs(x))", "Logarithm"),
        ("y = x**3", "Cubic")
    ]

    for func, name in common_functions:
        def set_function(f=func):
            relation_entry.delete(0, tk.END)
            relation_entry.insert(0, f)

        func_button = HoverButton(functions_frame, text=name, command=set_function,
                                  bg=ENTRY_BG, fg=TEXT_COLOR, font=NORMAL_FONT,
                                  relief="flat", padx=5, pady=2)
        func_button.pack(side="left", padx=5)

    plot_graph_with_range()  # Plot the default graph

# Main application setup
root = tk.Tk()
root.title("JARVIS AI Assistant")
root.geometry("1300x900")
try:
    img = PhotoImage(file="jaricon.png")
    root.iconphoto(False, img)
except:
    pass  # Skip if icon not found
root.configure(bg=DARK_BG)
root.resizable(True, True)

# Directly call create_graph() to launch the graph plotter in the main window
create_graph()

if __name__ == "__main__":
    root.mainloop()
    