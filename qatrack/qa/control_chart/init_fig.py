# (c) Dan La Russa & Randy Taylor

import matplotlib.pyplot as plt

def new_fig(w, h, col):
    """
    This method initializes a figure with a given width (w),
    height(h) and facecolor (col).
    """
    fig = plt.figure(1, figsize = (w, h), facecolor = col)
    return fig