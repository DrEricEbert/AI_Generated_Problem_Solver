import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Menu
import sympy
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import json
import numpy as np
import os
import importlib.util
import sys

# Matplotlib Integration & Controls
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# =============================================================================
# 1. TOOLBOX MANAGER
# =============================================================================

class ToolboxManager:
    def __init__(self, toolbox_dir="toolboxes"):
        self.toolbox_dir = toolbox_dir

    def discover_toolboxes(self):
        tbs = []
        if not os.path.exists(self.toolbox_dir):
            os.makedirs(self.toolbox_dir)
            with open(os.path.join(self.toolbox_dir, "__init__.py"), 'w') as f: pass

        for filename in os.listdir(self.toolbox_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                tb = self._load_module(filename)
                if tb: tbs.append(tb)
        return tbs

    def _load_module(self, filename):
        try:
            name = filename[:-3]
            path = os.path.join(self.toolbox_dir, filename)
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, 'toolbox_meta'):
                return mod.toolbox_meta
        except Exception as e:
            print(f"Fehler beim Laden von {filename}: {e}")
        return None

# =============================================================================
# 2. MATH ENGINE
# =============================================================================

class MathEngine:
    def __init__(self):
        self.base_context = {}
        self.toolbox_context = {}
        self.variables = {}
        self._init_base()

    def _init_base(self):
        for name in dir(sympy):
            if not name.startswith("_"):
                self.base_context[name] = getattr(sympy, name)
        for n in 'x y z t a b c m k omega gamma'.split():
            self.base_context[n] = sympy.Symbol(n)

    def load_functions(self, func_dict):
        self.toolbox_context.update(func_dict)

    def unload_functions(self, func_dict):
        for k in func_dict:
            if k in self.toolbox_context: del self.toolbox_context[k]

    def reset_vars(self):
        self.variables = {}

    def _hybrid_eval(self, code, ctx, transformations):
        try:
            return parse_expr(code, local_dict=ctx, transformations=transformations)
        except Exception:
            return eval(code, {}, ctx)

    def evaluate_block(self, block):
        if not block.strip(): return []

        lines = block.split('\n')
        results = []

        ctx = self.base_context.copy()
        ctx.update(self.toolbox_context)
        ctx.update(self.variables)

        transformations = (standard_transformations + (implicit_multiplication_application,))

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"): continue

            try:
                is_assignment = False
                if "=" in line and "==" not in line:
                    parts = line.split("=", 1)
                    if "(" not in parts[0]:
                        is_assignment = True

                if is_assignment:
                    lhs, rhs = line.split("=", 1)
                    lhs = lhs.strip()
                    val = self._hybrid_eval(rhs.strip(), ctx, transformations)

                    if "," in lhs:
                        var_names = [v.strip() for v in lhs.split(",")]
                        try:
                            if not hasattr(val, '__iter__'):
                                results.append("Err: Nicht entpackbar")
                                continue
                            if len(val) != len(var_names):
                                results.append(f"Err: {len(var_names)} Vars != {len(val)} Werte")
                                continue
                        except Exception as e:
                            results.append(f"Err unpacking: {e}")
                            continue

                        out_strs = []
                        for i, name in enumerate(var_names):
                            if not name.isidentifier():
                                results.append(f"Err: '{name}' ungültig")
                                continue
                            sub_val = val[i]
                            self.variables[name] = sub_val
                            ctx[name] = sub_val

                            if isinstance(sub_val, (np.ndarray, list)):
                                out_strs.append(f"{name}:=Arr{np.shape(sub_val)}")
                            else:
                                out_strs.append(f"{name}:={str(sub_val)[:10]}...")
                        results.append(", ".join(out_strs))
                    else:
                        var_name = lhs
                        if not var_name.isidentifier():
                            results.append(f"Err: '{var_name}' ungültig")
                            continue

                        if hasattr(val, 'evalf') and not hasattr(val, 'figure') and not isinstance(val, (np.ndarray, list)):
                             if not val.free_symbols: val = val.evalf()

                        self.variables[var_name] = val
                        ctx[var_name] = val

                        if hasattr(val, 'figure'):
                            results.append(val)
                        elif isinstance(val, (np.ndarray, list)):
                            results.append(f"{var_name} := Array {np.shape(val)}")
                        else:
                            results.append(f"{var_name} := {str(val)}")
                else:
                    val = self._hybrid_eval(line, ctx, transformations)
                    if hasattr(val, 'figure'):
                        results.append(val)
                    elif isinstance(val, (np.ndarray, list)):
                        results.append(f"Result: Array {np.shape(val)}")
                    else:
                        results.append(str(val))

            except Exception as e:
                results.append(f"Error ({line}): {e}")

        return results

# =============================================================================
# 3. GUI IMPLEMENTIERUNG
# =============================================================================

class MathCell(ttk.Frame):
    def __init__(self, parent, cell_id, callbacks):
        super().__init__(parent, style="Card.TFrame")
        self.callbacks = callbacks
        self.pack(fill="x", padx=15, pady=5)
        self.columnconfigure(1, weight=1)

        # Input
        ttk.Label(self, text=f"In [{cell_id}]:", foreground="#666").grid(row=0, column=0, sticky="nw", padx=5)
        self.entry = tk.Text(self, height=1, width=50, font=("Consolas", 11), bd=1, relief="solid")
        self.entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.entry.bind("<Shift-Return>", self.trigger)
        self.entry.bind("<KeyRelease>", self.autosize)

        ttk.Button(self, text="×", width=3, command=lambda: callbacks['del'](self), style="Small.TButton").grid(row=0, column=2, sticky="ne")

        # Output
        self.out_area = tk.Frame(self, bg="white")
        self.out_area.grid(row=1, column=1, sticky="w")
        self.lbl_marker = ttk.Label(self, text=f"Out[{cell_id}]:", foreground="#0055aa")

    def autosize(self, event=None):
        lines = int(self.entry.index('end-1c').split('.')[0])
        self.entry.configure(height=min(max(lines, 1), 15))

    def trigger(self, event=None):
        self.callbacks['exec']()
        return "break"

    def set_content(self, text):
        self.entry.delete("1.0", "end")
        self.entry.insert("1.0", text)
        self.autosize()

    def get_content(self):
        return self.entry.get("1.0", "end-1c")

    def show_results(self, results_list):
        # Alten Output bereinigen
        for w in self.out_area.winfo_children(): w.destroy()
        self.lbl_marker.grid_remove()

        if not results_list: return

        self.lbl_marker.grid(row=1, column=0, sticky="nw")

        for res in results_list:
            if res is None: continue
            if isinstance(res, str) and res == "": continue

            # === PLOT MIT TOOLBAR ===
            if hasattr(res, 'figure'):
                plot_frame = tk.Frame(self.out_area, bg="white", bd=1, relief="solid")
                plot_frame.pack(anchor="w", pady=5, padx=5)

                # WICHTIG: Tight Layout verhindert abgeschnittene Achsen
                try:
                    res.figure.tight_layout()
                except:
                    pass

                canvas = FigureCanvasTkAgg(res.figure, master=plot_frame)
                canvas.draw()

                # Toolbar hinzufügen
                toolbar = NavigationToolbar2Tk(canvas, plot_frame, pack_toolbar=False)
                toolbar.update()
                toolbar.pack(side="bottom", fill="x")

                canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

                # Kontextmenü für Plot
                self._bind_context_menu(canvas.get_tk_widget(), is_plot=True, data=res.figure)

            # === TEXT ===
            else:
                lbl = ttk.Label(self.out_area, text=str(res), font=("Consolas", 11, "bold"), background="white")
                lbl.pack(anchor="w", pady=1)
                self._bind_context_menu(lbl, is_plot=False, data=str(res))

    def _bind_context_menu(self, widget, is_plot, data):
        menu = Menu(self, tearoff=0)
        if is_plot:
            menu.add_command(label="Speichern unter...", command=lambda: self._save_plot(data))
        else:
            menu.add_command(label="Kopieren", command=lambda: self._copy_text(data))

        btn = "<Button-2>" if sys.platform == "darwin" else "<Button-3>"
        widget.bind(btn, lambda e: menu.post(e.x_root, e.y_root))

    def _copy_text(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    def _save_plot(self, fig):
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if path: fig.savefig(path)

# =============================================================================
# 4. MAIN APP
# =============================================================================

class PyMathPad(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PyMathPad - Ultimate")
        self.geometry("1100x800")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Card.TFrame", background="white", relief="raised")
        self.configure(bg="#f0f0f0")

        self.engine = MathEngine()
        self.tb_manager = ToolboxManager()
        self.cells = []
        self.cell_cnt = 1

        self._build_ui()
        self.available_toolboxes = self.tb_manager.discover_toolboxes()
        self._fill_toolbox_menu()
        self.add_cell()

    def _build_ui(self):
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        fmenu = tk.Menu(self.menubar, tearoff=0)
        fmenu.add_command(label="Neu", command=self.clear_all)
        fmenu.add_command(label="Speichern", command=self.save)
        fmenu.add_command(label="Laden", command=self.load)
        fmenu.add_separator()
        fmenu.add_command(label="Beenden", command=self.quit)
        self.menubar.add_cascade(label="Datei", menu=fmenu)

        self.tb_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Toolboxes", menu=self.tb_menu)

        hmenu = tk.Menu(self.menubar, tearoff=0)
        hmenu.add_command(label="Dokumentation", command=self.show_help_window)
        self.menubar.add_cascade(label="Hilfe", menu=hmenu)

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(frame, bg="#f0f0f0", highlightthickness=0)
        scr = ttk.Scrollbar(frame, orient="vertical", command=self.canvas.yview)

        self.scroll_frame = ttk.Frame(self.canvas)
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.win_id = self.canvas.create_window((0,0), window=self.scroll_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.win_id, width=e.width))
        self.canvas.configure(yscrollcommand=scr.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scr.pack(side="right", fill="y")
        self.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        tbar = ttk.Frame(self)
        tbar.pack(fill="x", side="bottom")
        ttk.Button(tbar, text="+ Zelle", command=lambda: self.add_cell()).pack(side="left")
        ttk.Button(tbar, text="Alles Berechnen", command=self.run_all).pack(side="left")

    def show_help_window(self):
        help_win = tk.Toplevel(self)
        help_win.title("PyMathPad Hilfe")
        help_win.geometry("600x500")

        txt = tk.Text(help_win, wrap="word", padx=10, pady=10, font=("Segoe UI", 10))
        txt.pack(fill="both", expand=True)

        help_text = """
=== PyMathPad Kurzreferenz ===

BEDIENUNG:
- Shift + Enter: Zelle ausführen
- X-Button: Zelle löschen
- Toolboxes Menü: Erweiterungen aktivieren

GRUNDLAGEN:
- Zuweisung: a = 10
- Ausdruck:  sin(45) * a
- Symbolik:  diff(x**2, x)

PLOTS & BILDER:
- In den 'Toolboxes' entsprechende Module aktivieren.
- Physik Plot: plot(sin(x), x, -10, 10, size=(5,3))
- FFT Plot:    fft_plot(signal, fs)
- Bild:        show_image(img, "Titel")

NAVIGATION IN PLOTS:
Unter jedem Graphen finden Sie eine Toolbar:
- Lupe: Bereich zoomen
- Kreuz: Verschieben (Pan)
- Diskette: Als Bild speichern
- Haus: Ansicht zurücksetzen

SPEICHERN:
Arbeitsblätter werden als .json Dateien gespeichert.
        """
        txt.insert("1.0", help_text)
        txt.config(state="disabled")

    def _fill_toolbox_menu(self):
        self.tb_vars = {}
        for tb in self.available_toolboxes:
            var = tk.BooleanVar(value=False)
            self.tb_vars[tb['name']] = var
            self.tb_menu.add_checkbutton(label=tb['name'], variable=var,
                                         command=lambda t=tb, v=var: self.toggle_toolbox(t, v))
        self.tb_menu.add_separator()
        for tb in self.available_toolboxes:
             if 'demo_code' in tb:
                 self.tb_menu.add_command(label=f"Demo: {tb['name']}", command=lambda t=tb: self.load_demo(t))

    def toggle_toolbox(self, tb_meta, var):
        if var.get():
            self.engine.load_functions(tb_meta['functions'])
            messagebox.showinfo("Toolbox", f"{tb_meta['name']} aktiviert.")
        else:
            self.engine.unload_functions(tb_meta['functions'])
        self.run_all()

    def run_all(self):
        self.engine.reset_vars()
        for c in self.cells:
            self.update_idletasks()
            res_list = self.engine.evaluate_block(c.get_content())
            c.show_results(res_list)

    def add_cell(self, content=""):
        c = MathCell(self.scroll_frame, self.cell_cnt, {'del': self.del_cell, 'exec': self.run_all})
        self.cells.append(c)
        self.cell_cnt += 1
        if content: c.set_content(content)
        self.canvas.yview_moveto(1.0)
        return c

    def del_cell(self, cell):
        cell.destroy()
        if cell in self.cells: self.cells.remove(cell)
        self.run_all()

    def clear_all(self):
        for c in self.cells: c.destroy()
        self.cells = []
        self.add_cell()

    def load_demo(self, tb_meta):
        if not self.tb_vars[tb_meta['name']].get():
            self.tb_vars[tb_meta['name']].set(True)
            self.engine.load_functions(tb_meta['functions'])
        self.clear_all()
        if self.cells: self.cells[0].destroy(); self.cells = []
        self.add_cell(tb_meta['demo_code'])
        self.run_all()

    def save(self):
        data = [c.get_content() for c in self.cells if c.get_content().strip()]
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("MathPad", "*.json")])
        if path:
            with open(path, 'w') as f: json.dump(data, f)

    def load(self):
        path = filedialog.askopenfilename(filetypes=[("MathPad", "*.json")])
        if path:
            with open(path, 'r') as f: data = json.load(f)
            self.clear_all()
            if self.cells: self.cells[0].destroy(); self.cells = []
            for d in data: self.add_cell(d)
            self.run_all()

if __name__ == "__main__":
    app = PyMathPad()
    app.mainloop()
