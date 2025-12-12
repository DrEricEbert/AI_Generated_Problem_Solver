import numpy as np
import scipy.stats as stats
from matplotlib.figure import Figure

class PlotWrapper:
    def __init__(self, fig): self.figure = fig

def stat_hist(data, bins=20):
    fig = Figure(figsize=(5, 3), dpi=100)
    ax = fig.add_subplot(111)
    ax.hist(data, bins=bins, color='skyblue', edgecolor='black')
    ax.set_title("Histogramm")
    return PlotWrapper(fig)

def stat_linregress(x, y):
    res = stats.linregress(x, y)
    fig = Figure(figsize=(5, 3), dpi=100)
    ax = fig.add_subplot(111)
    ax.plot(x, y, 'o', label='Daten')
    ax.plot(x, res.intercept + res.slope * np.array(x), 'r', label=f'Fit: k={res.slope:.2f}')
    ax.legend()
    return PlotWrapper(fig)

toolbox_meta = {
    'name': 'Statistik',
    'functions': {
        'mean': np.mean,
        'median': np.median,
        'std': np.std,
        'linregress_plot': stat_linregress,
        'histogram': stat_hist,
        'normal_dist': np.random.normal
    },
    'demo_code': """# Statistik Demo
data = normal_dist(0, 1, 500)
mu = mean(data)
sigma = std(data)
histogram(data, 30)"""
}
