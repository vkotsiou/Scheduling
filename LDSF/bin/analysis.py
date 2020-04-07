from mpl_toolkits.mplot3d import Axes3D
import matplotlib
from matplotlib import pyplot as plt
import numpy as np
import matplotlib.cm as cm
#import statistics
import numpy as np
#import seaborn as sns

import pandas as pd



alg_name=['MSF','Stratum','LLSF','LDSF']
total_alg=len(alg_name)

path = '../plots/'

f_size=16
legend_fz=11

color_sequence = ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c',
                  '#98df8a', '#d62728', '#ff9896', '#9467bd', '#c5b0d5',
                  '#8c564b', '#c49c94', '#e377c2', '#f7b6d2','#9edae5',
                  '#17becf', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d' ]
filled_markers = ['o', 'v', '^', '<', '>', '8', 's', 'p', '*', 'h', 'H', 'D', 'd','o','v','8','s']
hatch_sequence=['xx','..','//','\\','xx','x','o','O','.','*']
my_color=['#A4CFE2','#2079B5','#B0DD8A','#35A22F']
my_color2=['#72AB4A','#4175C0','#FFBF01','#44682A','#25447B','#25447B','#8CC167','#72AB4A','#4175C0','#FFBF01','#44682A','#25447B','#25447B','#8CC167']


def plot_fig_lines(index1,X,Y,xlabel,ylabel): # multtiple nodes number
    fig = plt.figure(index1)

    ax = fig.add_axes([0.15, 0.17, 0.8, 0.8])

    plt.xlabel(xlabel, fontsize=f_size-2)
    plt.ylabel(ylabel, fontsize=f_size-2)

    #x = []

    #for i in range(0,len(xlabel)):
    #   x.append(i)

    #plt.xticks(x, xlabel, fontsize=f_size - 4, rotation='vertical')
    plt.yticks(fontsize=f_size - 4)

    print X
    print Y

    for j in range(0, len(alg_name)):
        #plt.errorbar(x, y_avg[j], xerr=0.0, yerr=y_conf[j])
        plt.plot(X, Y[j], label=alg_name[j], color=color_sequence[j], marker=filled_markers[j])  # i

    plt.legend(loc='center left', bbox_to_anchor=(0.0, 0.89),  prop={'size': 9})#title='Scheduling Algorithms',
    plt.savefig(path + 'plotB'+xlabel  +'.pdf', format='pdf')


Hops=[1,2,3,4,5,6,7,8,9,10]
SlotFrameSZ = [101,501,1001,2001,6001]

Y=[]
for i in range (0,len(alg_name)):
    t=[]
    Y.append(t)

constant_hops=5
ETX=1.5
Cells=2.0
for i in range (0,len(alg_name)):
    for sz in SlotFrameSZ:
        if i==0:
            delay=sz*constant_hops*ETX/(2.0 *Cells)
        elif i==1:
            if ETX>Cells:
                delay=sz*(1+constant_hops*(ETX/Cells-1))
            else:
                delay=sz
        elif i==3:
            delay=constant_hops*5*(2*ETX-1)
        elif i==2:
            delay=constant_hops*(2*ETX-1)
            delay=ETX*sz/(2.0*Cells) + (constant_hops-1)*(2*ETX-1)

        Y[i].append(delay)

plot_fig_lines(1,SlotFrameSZ,Y,"Slotframe Length","E2E delay (timeslots)")

Y1 = []
for i in range(0, len(alg_name)):
    t = []
    Y1.append(t)

constant_SlotFramesize = 101

for i in range(0, len(alg_name)):
    for hp in Hops:
        if i == 0:
            delay = hp * constant_SlotFramesize *ETX/ (2.0*Cells)
        elif i == 1:
            if ETX>  Cells :
                delay = constant_SlotFramesize*(1+hp*(ETX/Cells-1))
            else:
                delay=constant_SlotFramesize
        elif i == 3:
            delay = hp * 5*(2*ETX-1)
        elif i==2:
            delay=hp*(2*ETX-1)
            delay = ETX*constant_SlotFramesize/(2.0*Cells)+(hp-1) * (2 * ETX - 1)


        Y1[i].append(delay)

plot_fig_lines(2,Hops,Y1,"Number of Hops","E2E delay (timeslots)")

plt.show()
