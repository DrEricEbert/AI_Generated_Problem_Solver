import numpy as np
from skimage import data, filters
from matplotlib.figure import Figure

class PlotWrapper:
    def __init__(self, fig): self.figure = fig

def img_show(arr, title="Bild", size=(4, 4)):
    if isinstance(size, list): size = tuple(size)
    arr = np.array(arr)
    fig = Figure(figsize=size, dpi=100)
    ax = fig.add_subplot(111)
    is_gray = (len(arr.shape) == 2)
    ax.imshow(arr, cmap='gray' if is_gray else None)
    ax.axis('off')
    ax.set_title(title)
    return PlotWrapper(fig)

def safe_sobel(arr):
    return filters.sobel(np.array(arr))

toolbox_meta = {
    'name': 'Bildverarbeitung',
    'functions': {
        'show_image': img_show,
        'load_sample': data.camera,
        'sobel': safe_sobel
    },
    'demo_code': """# Bild Demo
img = load_sample()
edges = sobel(img)
show_image(img, "Orig", size=(3,3))
show_image(edges, "Kanten", size=(3,3))"""
}
