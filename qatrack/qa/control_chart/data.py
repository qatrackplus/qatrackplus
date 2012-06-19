# (c) Dan La Russa & Randy Taylor
import matplotlib
matplotlib.use("Agg")
matplotlib.interactive(True)

import matplotlib.pyplot as plt

import datetime
import numpy as np
import control_chart
import init_fig

def get_data():
    samples = int(raw_input('Enter the number of samples, N: '))

    print 'Enter the number of samples per "subgroup", n'
    sgSize = int(raw_input('1 <= n <= 100 OR the number of samples: '))
    if sgSize < 1 or sgSize > 100:
        print "the subgroup size you've entered is out of range."
        print 'setting subgroup size to 1...  '
        sgSize = 1

    print 'Enter the number of "subgroups" for the BASELINE data, b'
    baseline = int(raw_input(' 1 <= b <= N / n: '))
    if baseline < 1 or baseline > samples / sgSize:
        print "the number of subgroups is out of range."
        print 're-run the proggy and try again'
        exit(0)

    return samples, sgSize, baseline

def temp_data():
    samples =  1000
    sgSize = 2
    baseline = 2

    return samples, sgSize, baseline

def main():
#    samples, sgSize, baseline = get_data()
    samples, sgSize, baseline = temp_data()

    x = np.random.normal(6, 3, samples)
    x = np.array([x for x in x if x >=0]) # crappy way to remove
                                          # (-)ve numbers

    #x = (100.0, 102.0, 100.0, 99.0, 99.0, 101.0)

    dates = [datetime.datetime.today()+datetime.timedelta(days=i) for i in range(len(x))]

    print 'Generating control chart.'
    width = 12 #width of control chart
    height = 8 #height of control chart
    fig = init_fig.new_fig(width, height, 'w')
    try:
        control_chart.display(fig, x, sgSize, baseline, fit = True,dates=dates)
    except RuntimeError as e:
        print e

    plt.show()
    print "ok"
if __name__ == '__main__':
    main()
