import sympy
import numpy as np
from matplotlib.figure import Figure

class PlotWrapper:
    def __init__(self, fig): self.figure = fig

def plot_func(expr, var, start, end, title="Plot", size=(5, 3)):
    f = sympy.lambdify(var, expr, modules=['numpy'])
    x_vals = np.linspace(float(start), float(end), 400)
    try:
        y_vals = f(x_vals)
        if np.isscalar(y_vals): y_vals = np.full_like(x_vals, y_vals)
    except: return "Fehler im Plot"

    fig = Figure(figsize=size, dpi=100)
    ax = fig.add_subplot(111)
    ax.plot(x_vals, y_vals, label=f"${sympy.latex(expr)}$")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.5)
    return PlotWrapper(fig)

toolbox_meta = {
    'name': 'Physik & Mechanik',
    'functions': { 'plot': plot_func },
    'demo_code': """# Gedämpfter Oszillator
m = 1.0
k = 20.0
c = 0.5
omega = sqrt(k/m)
gamma = c / (2*m)
A = 5
x_t = A * exp(-gamma * t) * cos(omega * t)
plot(x_t, t, 0, 10, 'Ort x(t)', size=(6,3))"""
}
