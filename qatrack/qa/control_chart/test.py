import numpy
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from qatrack.qa.control_chart import control_chart

bad_data = [97.3, 97.1, 97.1, 97.3, 97.6, 99.3,  99.6, 99.1, 98.6, 98.8, 99, 98.1, 98.6, 98.8, 98.4, 98.6, 98.6, 98.1, 99.1, 97.3, 98.5, 98.2, 98.7]
ok_data = [1.999, 1.994, 1.99, 1.987, 1.988, 1.988, 1.99, 1.987, 1.985, 2.001, 2.004, 1.989, 2.006, 1.998, 1.972, 1.993, 1.993, 1.994, 1.993, 2.004, 2.008, 1.997, 1.995, 2, 2.005, 1.996, 2.009, 2.026, 2.014, 2.014, 2.007, 2.003, 1.986, 2.008, 2.011, 1.997, 1.997, 2.01, 2.007, 1.981, 1.987, 2.001, 1.99, 1.993, 2.008, 2.007, 2.016, 2.002, 2.014, 2.007, 1.978, 1.98, 2.032, 2.008, 2.016, 1.987, 1.996, 2.026, 2.015, 1.976, 1.992, 2.013, 2.035, 2.022, 2.032]

data = ok_data
n_subgroups = 1
subgroup_size = 1
include_fit = True

fig=Figure(dpi=72,facecolor="white")

control_chart.display(fig, numpy.array(data), subgroup_size, n_subgroups, fit = include_fit)



