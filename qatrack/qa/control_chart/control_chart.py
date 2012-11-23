#range (c) Dan La Russa & Randy Taylor
# functions for pre-formatted control chart
import datetime
import numpy as np
import matplotlib.gridspec as gridspec
import matplotlib.dates
import leastsquaresfit as lsqfit
import maximumlikelihoodfit as mlefit
import histogram as htg

from matplotlib.ticker import NullFormatter,FuncFormatter
from matplotlib.font_manager import FontProperties

# Set some values:

# Spacing:
WSPACE  = 0.05   # horizontal space between plots
HSPACE  = 0.15   # vertical space between plots
DATA_HSPACE = 0.05 # space following data; frac of # of subgroups (aesthetics)
DATA_TSPACE = 0.10 # space above data to leave room for string.

LMARGIN = 0.1    #
RMARGIN = 0.95   #   definition of outer
BMARGIN = 0.1    #   borders
TMARGIN = 0.9    #

HEADERX = 0.1    # x position of header
HEADERY = 0.93   # y position of header
STRING_XPOS = 0.05 # relative position of control chart string in x direction
STRING_YPOS = 0.95 # relative position of control chart string in y direction

XPOS_MULT = 0.7 # adjust the relative x-position of histogram strings
YPOS_MULT = 0.1 # adjust the relative y-position of histogram string (cntrl chrt only)

# Histogram limits:
NBIN_THRESH = 10    # minimum number of bins.
                    # Note that not all bins will have events, and so
                    # there still may be fewer than NBIN_THRESH displayed

# Formats for raw data:
BC = '#36648B' # baseline data color
RC = '#63B8FF' # color of remaining data
DATAMARKER = 'o'
LINESTYLE = '-'

# Formats for fit lines and thresholds:
LINEWIDTH = 3  # width of fit lines and control/range chart limits
COLORS   = ['#006400','#CD2626', '#CD2626','#FFC125','#FFC125']
STDSTYLE = ['-', '-', '-', '--', '--']
DATALABEL   = ['mean', 'range limit', '', 'st. dev. limit', '']
GAUSSFORMAT = 'k'       # Format of Gaussian distribution fit line
GAMMAFORMAT = '#0000CD' # Format of Gamma distributio fit line
GAMMALINE   = '--'      # Style of fit line for Gamma distribution

# Axis labels:
CC_YAXIS  = 'subgroup mean'   # y-axis label for control chart
R_YAXIS   = 'range'           # y-axis label for range chart
HISTAXIS  = 'frequency'       # axis label for histograms
LBL_XAXIS = 'subgroup number' # x-axis label for range and control charts
LBL_DATE_XAXIS = 'subgroup start date'

# Data labels:
LBL1 = 'used to calc. limits'  # labels the baseline data used to calculate limits
LBL2 = 'all data'              # label to indicate that it reprensents all the data
LBL_GAUSS = "Gaussian dist. fit line"  # in legend
LBL_GAMMA = "Gamma dist. fit line"     # in legend

header_string = '# of data points = %r  |  subgroup size = %r  |  # of baseline points = %r'
control_chart_string = 'Ac = %1.2f    Au = %1.2f    Al = %1.2f    Au,s = %1.2f    Al,s = %1.2f'
range_chart_string   = 'Rc = %1.2f    Ru = %1.2f    Rl = %1.2f'
hist_string       = 'mean = %1.2f,  stdev = %1.2f \nfit mean = %1.2f, fit stdev = %1.2f \nfit k = %1.2f,  fit theta = %1.2f'
short_hist_string = 'mean = %1.2f,  stdev = %1.2f \nfit mean = %1.2f, fit stdev = %1.2f'

# Font sizes:
HFS   = 16  # Header font size
CFS   = 14  # Font size for text in control/range charts
HISTFS = 11 # Font size for text in histograms

ALFS  = 16  # axis label font size
TLFS  = 12  # tick label font size
LEGFS = 11  # legend font size

nullfmt = NullFormatter()
font = FontProperties(size=LEGFS)


#----------------------------------------------------------------------
def generate_fit(x,axes,freq, bins, binwidth):
    """
    """
    optParam, cov = lsqfit.gauss_fit(x, freq, bins, binwidth)
    norm, fitmean, fitsigma = optParam
    paramUnc = np.zeros(len(optParam))
    for i in np.arange(0, len(optParam)):
        paramUnc[i] = np.sqrt(abs(cov[i,1]))
    xdata = np.linspace(fitmean-fitsigma*10, fitmean+fitsigma*10, 500)
    ydata = lsqfit.gauss_pdf(xdata, norm, fitmean, fitsigma)
    axes.plot(ydata, xdata, GAUSSFORMAT, label=LBL_GAUSS, lw=LINEWIDTH)

    # maximum likelihood estimator fit of Gaussian and Gamma distributions:
    # Gaussian distribution (not for plotting):
    optParam = mlefit.gauss_fit(x, binwidth)
    norm, mean, sigma = optParam

    # Gamma distribution:
    if np.min(x) >= 0:
        optParam = mlefit.gamma_fit(x, binwidth)
        norm, k, theta = optParam
        ydata = mlefit.gamma_pdf(xdata, norm, k, theta)
        axes.plot(ydata, xdata, GAMMAFORMAT,
                  ls=GAMMALINE, label=LBL_GAMMA, lw=LINEWIDTH)

        return mean, sigma, fitmean, fitsigma, k, theta
    else:
        return mean, sigma, fitmean, fitsigma

#################################################################################

def display(fig, x, sgSize, baseline, dates = None, fit = None):

    """
    Display a statistical control chart for a dataset. See Pawlicki et al
    Med Phys 32 (9), 2005, pg 2777

    Arguments:
    fig      -- a matplotlib figure instance to display the control chart
    x        -- one dimensional array or list of data
    sgSize   -- subgroup size
    baseline -- number of subgroups used to generate the baseline

    Keyword arguments:
    dates    -- Optional labels for x-axis.  len(x) must == len(dates)
    fit      -- Optional argument to fit data to Gaussian & Gamma distributions
    """

    if dates is None:
        dates = range(len(x))
        use_dates = False
    else:
        use_dates = True

    if fit is None:
        fit = False

    # process data for plotting
    sg, xbar, sgNum = get_subgroups(x, sgSize, dates) # sg = subgroup of size sgSize
    r = get_ranges(sg, sgSize)                 # sgNum = index of subgroup
                                               # xbar = mean of a sub group, sg
                                               # range data

    # calculate control chart limits
    xbar_thresh, range_thresh = get_param(sg, xbar, r, baseline, sgSize)

    grid = get_axes()

    # plot for subgroup data
    axData = fig.add_subplot(grid[0,0])
    generate_cc(axData, sgNum, xbar, baseline, xbar_thresh)

    # historgram(s) for the binned subgroups
    axHistD = fig.add_subplot(grid[0,1])
    freq, bins, binwidth = generate_hist(axHistD, xbar, baseline)
    if fit:
        cc_fits = generate_fit(xbar,axHistD,freq,bins,binwidth)
    else:
        cc_fits = []

    # plot for the range data
    axRange = fig.add_subplot(grid[1,0])
    if sgSize == 1:
        sgNum, r, baseline = unity_sgSize(sgNum, r, baseline)

    generate_cc(axRange, sgNum, r, baseline, range_thresh)

    # histogram(s) for the binned range data
    axHistR = fig.add_subplot(grid[1,1])
    freq, bins, binwidth = generate_hist(axHistR, r, baseline)
    if fit:
        rc_fits = generate_fit(r,axHistR,freq,bins,binwidth)
    else:
        rc_fits = []

    # format the plots
    plots = [axData, axHistD, axRange, axHistR] # don't change the order
    format_plots(plots,xbar_thresh,range_thresh,
                 cc_fits,rc_fits,sgNum[ - 1],fit,use_dates)

    fig.text(HEADERX, HEADERY,
             header_string % (len(x), sgSize, baseline),
             fontsize = HFS)


################################################################################

def get_bins(x):
    binwidth = htg.binwidth(x)

    xMax = np.max(x)
    xMin = np.min(x)

    bins_min = xMin - binwidth/2.
    bins_max = xMax + binwidth
    bins = np.arange(bins_min,bins_max,binwidth)

    if len(bins)<NBIN_THRESH:
        binwidth = 2.*(xMax-xMin)/NBIN_THRESH
        centre = (xMin+xMax)/2.
        bins_min = centre-binwidth*(NBIN_THRESH/2+1)
        bins_max = centre+binwidth*(NBIN_THRESH/2+1)
        bins = np.arange( bins_min, bins_max, binwidth)

    return bins, binwidth

################################################################################

def get_axes():

    gs = gridspec.GridSpec(2,2,
                           left=LMARGIN,
                           bottom=BMARGIN,
                           right=RMARGIN,
                           top=TMARGIN,wspace=WSPACE,
                           hspace=HSPACE,
                           width_ratios=[2,1])
    return gs


################################################################################

def generate_cc(ax, sgNum, data, baseline, thresh):

    color = COLORS
    style = STDSTYLE
    label = DATALABEL

    prop = { 'marker': DATAMARKER,
             'ls': LINESTYLE
           }

    ax.plot(sgNum[0: baseline], data[0: baseline], color=BC, label=LBL1, **prop)
    ax.plot(sgNum[baseline: ], data[baseline: ], color=RC, **prop)

    if not isinstance(sgNum[0],datetime.date):
        t = [0, sgNum[ - 1] + sgNum[ - 1] * 0.1]
    else:
        t = [sgNum[0], sgNum[ - 1]]
    for i, val in enumerate(thresh):
        ax.plot(t, val, color[i], ls=style[i], lw = LINEWIDTH, label=label[i])


################################################################################
def generate_hist(ax, data, baseline):

    bins, binwidth = get_bins(data)

    orientation = 'horizontal'
    prop = {'orientation': orientation}

    freq, edges, ignored = ax.hist(data, bins=bins, color=RC, label=LBL2, **prop)
    ax.hist(data[0: baseline], bins=bins, color=BC, label=LBL1, **prop)

    return freq, bins, binwidth


################################################################################

def format_plots(plots, xbar_thresh, range_thresh,
                 cc_fits, rc_fits, xaxis_limit, fit,use_dates):

    [Ac, Au, Al, Aus, Als] = xbar_thresh
    [Rc, Ru, Rl] = range_thresh


    plots[0].set_ylabel(CC_YAXIS, fontsize = ALFS)
    if use_dates:
        plots[2].set_xlabel(LBL_DATE_XAXIS, fontsize = ALFS)
    else:
        plots[2].set_xlabel(LBL_XAXIS, fontsize = ALFS)
    plots[2].set_ylabel(R_YAXIS, fontsize = ALFS)
    plots[3].set_xlabel(HISTAXIS, fontsize = ALFS)

    # new y-axis limits to make room for string
    cc_ylim = plots[0].get_ylim()
    cc_ylim = (cc_ylim[0], cc_ylim[1] + cc_ylim[1]*DATA_TSPACE)
    plots[0].set_ylim( cc_ylim )

    range_lim = plots[2].get_ylim()
    if np.abs(range_lim[1] - Ru[0])/range_lim[1] < 0.05: # then make space
        range_lim = (range_lim[0], range_lim[1] + range_lim[1]*DATA_TSPACE)
        plots[2].set_ylim( range_lim )


    # redefine x-axis limits for aesthetics
    cc_xlim = plots[0].get_xlim()
    if not use_dates:
        cc_xlim = (cc_xlim[0], xaxis_limit + xaxis_limit * DATA_HSPACE)

    plots[0].set_xlim( cc_xlim )     # white space after data ends
    plots[2].set_xlim( plots[0].get_xlim() )  # Range chart shares x-axis with control chart

    plots[1].set_ylim( plots[0].get_ylim() )  # Control chart shares y-axis with histogram
    plots[3].set_ylim( plots[2].get_ylim() )  # Range chart shares y-axis with histogram

    if use_dates:
        cc_string_xpos = cc_xlim[0]+50
    else:
        cc_string_xpos = xaxis_limit*STRING_XPOS

    cc_string_ypos = np.max(xbar_thresh) + np.abs(cc_ylim[1] - np.max(xbar_thresh))/2.
    cchist_string_xpos = np.mean( plots[1].get_xlim() ) * XPOS_MULT
    cchist_string_ypos = cc_ylim[0] + (cc_ylim[1]- cc_ylim[0]) * YPOS_MULT

    r_string_ypos = Ru + np.abs(np.max(range_lim) - Ru) / 2.
    rhist_string_xpos = np.mean( plots[3].get_xlim() ) * XPOS_MULT
    rhist_string_ypos = np.mean( plots[3].get_ylim() )


    for i,plot in enumerate(plots):

        for label in plot.get_xticklabels() + plot.get_yticklabels():
            label.set_fontsize(TLFS)

        if plot == plots[0]:
            plot.xaxis.set_major_formatter(nullfmt)

            plot.legend(loc='upper center', bbox_to_anchor=(0.5, -0.01),
                        ncol=4, fancybox=True, shadow=True, prop=font)

            plot.text(cc_string_xpos, cc_string_ypos,
                control_chart_string % (Ac[0],Au[0],Al[0],Aus[0],Als[0]),
                fontsize = CFS)

            plot.grid(True)

        if plot == plots[2]:
            plot.text(cc_string_xpos, r_string_ypos[0],
                range_chart_string % (Rc[0],Ru[0],Rl[0]),
                fontsize = CFS)

            plot.grid(True)

        if plot == plots[1] or plot == plots[3]:
            plot.yaxis.set_major_formatter(nullfmt)
            plot.legend(bbox_to_anchor=(1.05,1.05),
                        fancybox=True, shadow=True, prop=font)

            if plot == plots[1] and fit:
                if len(cc_fits) == 6:
                    cm, cs, fcm, fcs, fck, fct = cc_fits
                    plot.text(cchist_string_xpos, cchist_string_ypos,
                              hist_string % (cm, cs, fcm, fcs, fck, fct),
                              fontsize = HISTFS)
                else:
                    cm, cs, fcm, fcs = cc_fits
                    plot.text(cchist_string_xpos, cchist_string_ypos,
                              short_hist_string % (cm, cs, fcm, fcs),
                              fontsize = HISTFS)


            if plot == plots[3] and fit:
                if len(rc_fits) == 6:
                    rm, rs, frm, frs, frk, frt = rc_fits
                    plot.text(rhist_string_xpos, rhist_string_ypos,
                              hist_string % (rm, rs, frm, frs, frk, frt),
                              fontsize = HISTFS)
                else:
                    rm, rs, frm, frs = rc_fits
                    plot.text(rhist_string_xpos, rhist_string_ypos,
                              short_hist_string % (rm, rs, frm, frs),
                              fontsize = HISTFS)
    if use_dates:
        #plots[2].xaxis.set_major_locator(matplotlib.dates.MonthLocator())
        plots[2].xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d %b %Y"))
        [(tick.set_rotation(25),tick.set_fontsize(TLFS/1.5)) for tick in plots[2].get_xticklabels()]



################################################################################

def unity_sgSize(sgNum, r, baseline):
    sgNum = sgNum[1: ]
    r = r[1: ]
    baseline = baseline - 1
    return sgNum, r, baseline


################################################################################

def get_subgroups(x, sgSize,dates):

    sg = [x[i: i + sgSize] for i in np.arange(0, len(x), sgSize)] # subgroups
    dates = [dates[i] for i in np.arange(0, len(x), sgSize)]
    if len(sg[ - 1])< sgSize:
        sg = sg[0:- 1]
        dates = dates[0:-1]
    xbar = [np.mean(sg[i]) for i in np.arange( len(sg) )]  # mean of subgroup
    xbar = np.array(xbar)

    if isinstance(dates[0],datetime.date):
        sgNum = dates
    else:
        sgNum = np.arange(1, len(xbar) + 1)                    # index of subgroup

    return sg, xbar, sgNum


################################################################################

def get_ranges(sg, n):

    r = np.zeros(len(sg))
    if n == 1:
        for i in np.arange(1, len(sg)):
            r[i] = np.abs(sg[i] - sg[i - 1])
    else:
        for i in np.arange(0, len(sg)):
            r[i] = np.max(sg[i]) - np.min(sg[i])

    return r

################################################################################

def get_param(sg, xbar, r, bl, n):

    d2, d3 = get_dvalues(n)

    Ac = [np.mean(xbar[0: bl]), np.mean(xbar[0: bl])]
    Rc = [np.mean(r[0: bl]), np.mean(r[0: bl])]

    Afactor = 3.0 * Rc[0] / (d2 * np.sqrt(n))
    Au = [Ac[0] + Afactor, Ac[0] + Afactor]
    Al = [Ac[0] - Afactor, Ac[0] - Afactor]

    Rfactor = (3.0 * d3 / d2)
    Ru = [(1.0 + Rfactor) * Rc[0], (1.0 + Rfactor) * Rc[0]]
    Rl = [(1.0 - Rfactor) * Rc[0], (1.0 - Rfactor) * Rc[0]]
    if Rl[0] < 0.0:
        Rl = [0.0, 0.0]

    sumSq = np.sum(xbar[0: bl] ** 2)
    sqSum = np.sum(xbar[0: bl]) ** 2
    stdStat = np.sqrt((bl * sumSq - sqSum) / (bl * (bl - 1)))

    Afactor = 3.0 * stdStat
    Aus = [Ac[0] + Afactor, Ac[0] + Afactor]
    Als = [Ac[0] - Afactor, Ac[0] - Afactor]

    return [Ac, Au, Al, Aus, Als], [Rc, Ru, Rl]


################################################################################

def get_dvalues(n):

    dtwo = [1.128, 1.128, 1.693, 2.059, 2.326, 2.534, 2.704, 2.847, 2.970, 3.078, 3.173, 3.258, 3.336, 3.407, 3.472, 3.735, 3.931, 4.086, 4.322, 4.498, 5.015]

    dthree = [0.8525, 0.8525, 0.8884, 0.8798, 0.8641, 0.8480, 0.8332, 0.8198, 0.8078, 0.7971, 0.7873, 0.7785, 0.7704, 0.7630, 0.7562, 0.7287, 0.7084, 0.6927, 0.6692, 0.6521, 0.6052]

    ndata = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 20, 25, 30, 40, 50, 100]

    d2 = np.interp(n, ndata, dtwo)
    d3 = np.interp(n, ndata, dthree)

    return d2, d3
