# ----------------------------------------------------------------------------------
#                                 Graphs Plotting
#-----------------------------------------------------------------------------------
from mpl_toolkits.mplot3d import Axes3D
import matplotlib
from matplotlib import pyplot as plt
import numpy as np
import matplotlib.cm as cm
import statistics
import numpy as np

import pandas as pd
import seaborn as sns

#sns.set_style("whitegrid")

alg_name=['MSF','Stratum','NLDSF','LDSF']
alg_name=['MSF','Stratum','LDSF']
total_alg=len(alg_name)

path = '../plots/'

f_size=17
legend_fz=11

color_sequence = ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c',
                  '#98df8a', '#d62728', '#ff9896', '#9467bd', '#c5b0d5',
                  '#8c564b', '#c49c94', '#e377c2', '#f7b6d2','#9edae5',
                  '#17becf', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d' ]
filled_markers = ['o', 'v', '^', '<', '>', '8', 's', 'p', '*', 'h', 'H', 'D', 'd','o','v','8','s']
hatch_sequence=['xx','..','//','\\','xx','x','o','O','.','*']
my_color=['#A4CFE2','#2079B5','#B0DD8A','#35A22F']
my_color2=['#72AB4A','#4175C0','#FFBF01','#44682A','#25447B','#25447B','#8CC167','#72AB4A','#4175C0','#FFBF01','#44682A','#25447B','#25447B','#8CC167']

n_groups =len(alg_name) #5
bar_width = 0.20
opacity = 0.8
max_hops=5

def plot_fig_barA(index,metric,stats): # whitelist size on x-axis

    fig = plt.figure(index)
    ax = fig.add_axes([0.15, 0.17, 0.8, 0.75])
    plt.gca().yaxis.grid(True)
    plt.gca().xaxis.grid(False)

    n_groups=3
    index = np.arange(n_groups)

    y_avg = []
    y_conf = []

    print "\n Metric", metric
    for i in range(0, len(alg_name)):
            print "Algorithm",alg_name[i],":",
            average, median, standard_deviation, minimum, maximum, confidence = statistics.stats(stats[alg_name[i]][metric], 0.05)

            print average, median, standard_deviation, minimum, maximum, confidence
            y_conf.append(confidence)
            y_avg.append(average)


    plt.grid( linestyle='dashed', linewidth=0.5,axis='y')
    error_config = {'elinewidth':'0.1'}#'ecolor': '0.3',
    plt.bar(index + 0.32 + bar_width , y_avg, bar_width, alpha=opacity, color=my_color[0],
                yerr=y_conf, error_kw=dict(lw=0.5, capsize=3, capthick=0.5,color=0.3),label="bloom",linewidth=1,edgecolor=my_color[1] )


    plt.xticks(index + 0.32 +bar_width , alg_name,fontsize=f_size - 6) #bar_width/2

    plt.yticks(fontsize=f_size - 6)

    plt.xlabel('Algorithms', fontsize=f_size-4)

    if metric=='e2e delay':
        plt.ylabel("End 2 End Delay (timeslots)", fontsize=f_size-4)
    elif metric=='PDR':
        plt.ylabel("PDR", fontsize=f_size - 4)
    elif metric=='energy':
        plt.ylabel("Energy per Packet(mJ)", fontsize=f_size - 4)
    elif metric=='lifetime':
        plt.ylabel("Network Lifetime (years)", fontsize=f_size - 4)
    elif metric=='jitter':
        plt.ylabel("Jitter (timeslots)", fontsize=f_size - 4)
    elif metric == 'total_energy':
        plt.ylabel("Total Energy consumed (mJ)", fontsize=f_size - 4)
    elif metric == 'avg_hops':
        plt.ylabel("Average (hops)", fontsize=f_size - 4)
    elif metric == 'ETX':
        plt.ylabel("ETX", fontsize=f_size - 4)

    plt.savefig(path +metric + '.pdf', format='pdf')

def plot_fig_multi_bar(index1,metric,stats): # x-axis  -- Algorithms, k-values on legend

    fig = plt.figure(index1)


    ax = fig.add_axes([0.12, 0.17, 0.8, 0.8])

    plt.xlabel('Hops', fontsize=f_size-4) #:)
    plt.ylabel('E2E delay (slots)' , fontsize=f_size-4)



    extract_stats={}
    y_avg=[]
    y_conf=[]

    for i in range(0,len(alg_name)):
        extract_stats[alg_name[i]]=[]
        t2=[]
        t3=[]
        y_avg.append(t2)
        y_conf.append(t3)
        for j in range(0,max_hops):
            t1=[]
            extract_stats[alg_name[i]].append(t1)





    for i in range(0, len(alg_name)):
        for j in range(0,max_hops):
            for k in range(0,len(stats[alg_name[i]][metric])): # k experiments
                #print extract_stats[alg_name[i]][j]
                #print stats[alg_name[i]][metric][k][j]
                extract_stats[alg_name[i]][j].append(stats[alg_name[i]][metric][k][j])

    n_max_hops=-1

    for j in range(1,max_hops):
        found=0
        for i in range(0, len(alg_name)):
                for k in range(0,len(extract_stats[alg_name[i]][j])):

                    if  extract_stats[alg_name[i]][j][k] !=0.0:
                        found=1

        if found ==1 :
            n_max_hops=j

    index = np.arange(n_max_hops)  # np.arange(n_groups)
    bar_width = 0.15

    xlabel = []
    x = []
    for i in range(1, n_max_hops+1):
        xlabel.append(i)
        x.append(i)

    plt.xticks(x, xlabel, fontsize=f_size - 6)
    plt.yticks(fontsize=f_size - 6)
    plt.xticks(index + 0.32 + 2.5 * bar_width, xlabel)

    print "New hops",n_max_hops
    for i in range(0,len(alg_name)):
        for j in range(1,n_max_hops+1):
                print "Alg:",alg_name[i],"hops",j,": ", extract_stats[alg_name[i]][j]
                average, median, standard_deviation, minimum, maximum, confidence = statistics.stats(extract_stats[alg_name[i]][j], 0.05)
                print average, median, standard_deviation, minimum, maximum, confidence
                y_conf[i].append(confidence)
                y_avg[i].append(average)

    plt.grid(linestyle='dashed', linewidth=0.5, axis='y')
    error_config = {'elinewidth': '0.1'}  # 'ecolor': '0.3',


    barlist=[]
    for j in range(0, len(alg_name)):
        blst=plt.bar(index + 0.32 + bar_width*(j+1), y_avg[j], bar_width, alpha=0.7, color=my_color2[j],
                yerr=y_conf[j], error_kw=dict(lw=0.5, capsize=3, capthick=0.5, color=0.3), label=alg_name[j], linewidth=1 )#k-Best :)#color_sequence[j] edgecolor='black'
        barlist.append(blst)



    leg=plt.legend(loc='upper left',title='Scheduling Algorithms', prop={'size': 10}) #bbox_to_anchor=(1, 0.5),
    leg._legend_box.align = "left"
    #plt.legend(loc='upper left', title='k-Worst', prop={'size': 10})
    #   :)

    plt.savefig(path + 'plot' +str(index1) +'.pdf', format='pdf',dpi=400)

def plot_fig_lines(index1,metric,stats,xlabel): # multtiple nodes number
    fig = plt.figure(index1)
    ax = fig.add_axes([0.12, 0.17, 0.65, 0.65])

    plt.xlabel('Period of packet generation (sec)', fontsize=f_size)

    if metric=='e2e delay':
        plt.ylabel("End 2 End Delay (timeslots)", fontsize=f_size-4)
    elif metric=='PDR':
        plt.ylabel("PDR", fontsize=f_size - 4)
    elif metric=='energy':
        plt.ylabel("Energy per Packet(mJ)", fontsize=f_size - 4)
    elif metric=='lifetime':
        plt.ylabel("Network Lifetime (years)", fontsize=f_size - 4)
    elif metric=='jitter':
        plt.ylabel("Jitter (timeslots)", fontsize=f_size - 4)
    elif metric == 'ETX':
        plt.ylabel("ETX", fontsize=f_size - 4)
    x = []

    for i in range(0,len(xlabel)):
        x.append(i)

    plt.xticks(x, xlabel, fontsize=f_size - 4, rotation='vertical')
    plt.yticks(fontsize=f_size - 4)

    y_avg=[]
    y_conf=[]

    for i in range(0,len(alg_name)):
        t1=[]
        t2=[]
        y_avg.append(t1)
        y_conf.append(t2)


    for i in range(0, len(alg_name)):
        for j in range(0,len(xlabel)):
            print alg_name[i],xlabel[j],metric,
            print stats[alg_name[i]][xlabel[j]][metric]
            average, median, standard_deviation, minimum, maximum, confidence = statistics.stats(stats[alg_name[i]][xlabel[j]][metric], 0.05)
            print average,confidence

            y_conf[i].append(confidence)
            y_avg[i].append(average)



    for j in range(0, len(alg_name)):
        #plt.errorbar(x, y_avg[j], xerr=0.0, yerr=y_conf[j])
        plt.plot(x, y_avg[j], label=alg_name[j], color=color_sequence[j], marker=filled_markers[j])  # i

    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), title='Scheduling Algorithms', prop={'size': 10})
    plt.savefig(path + metric+'_lines'  +'.pdf', format='pdf')


def plot_fig_lines2(index1,metric,stats,xlabel): # multtiple nodes number
    fig = plt.figure(index1)
    ax = fig.add_axes([0.12, 0.17, 0.8, 0.8])
    out_label = [ 3,5, 10, 20, 30, 40, 60, 80, 100, 120]
    out_label = [5,10, 20,30, 40, 60, 80, 100,120]

    y_ms=0
    plt.xlabel('Period of packet generation (sec)', fontsize=f_size-2)
    #plt.xlabel('Number of Nodes', fontsize=f_size - 2)
    if metric=='e2e delay':
        plt.ylabel("End 2 End Delay (ms)", fontsize=f_size-6)
        y_ms=1
    elif metric=='PDR':
        plt.ylabel("PDR", fontsize=f_size - 6)
    elif metric=='energy':
        plt.ylabel("Energy per Packet(mJ)", fontsize=f_size - 6)
    elif metric=='lifetime':
        plt.ylabel("Network Lifetime (years)", fontsize=f_size - 6)
    elif metric=='jitter':
        plt.ylabel("Jitter (ms)", fontsize=f_size - 6)
        y_ms=1
    elif metric == 'ETX':
        plt.ylabel("ETX", fontsize=f_size - 6)
    elif metric == 'avg_hops':
        plt.ylabel("Average #Hops", fontsize=f_size - 6)
    x = []

    for i in range(0, len(xlabel)):
        if xlabel[i] in out_label:
            x.append(xlabel[i])

    #ax.set_xticks(x, xlabel)
    plt.xticks(x, out_label, fontsize=f_size - 6, rotation='vertical')
    plt.yticks(fontsize=f_size - 6)

    x_vector=[]
    y_vector=[]
    alg=[]
    print "\n Metric", metric
    for i in range(0, len(alg_name)):

        for j in range(0,len(xlabel)):
            #print stats[alg_name[i]][xlabel[j]][metric]
            if xlabel[j] in out_label:
                count=0
                p_nodes=[]
                for k in range(0,len(stats[alg_name[i]][xlabel[j]][metric])):
                    valid=False
                    if count < 20 and stats[alg_name[i]][xlabel[j]]['TxNodes'][k]==39 and i in [0,2]:
                        valid = True

                    if i==1:
                        if count<20:
                            if xlabel[j]==20 and stats[alg_name[i]][xlabel[j]]['TxNodes'][k]>=38:
                                valid=True
                            elif  xlabel[j]==10 and stats[alg_name[i]][xlabel[j]]['TxNodes'][k]>=37:
                                valid=True
                            elif xlabel[j]==5 and stats[alg_name[i]][xlabel[j]]['TxNodes'][k]>=29:
                                valid=True
                            elif  xlabel[j] >20 and stats[alg_name[i]][xlabel[j]]['TxNodes'][k]==39:
                                valid=True

                    if valid==True:
                        count+=1
                        p_nodes.append(stats[alg_name[i]][xlabel[j]]['TxNodes'][k])
                        x_vector.append(xlabel[j])
                        if y_ms==1:
                            y_vector.append(stats[alg_name[i]][xlabel[j]][metric][k]*10.0)
                        else:
                            y_vector.append(stats[alg_name[i]][xlabel[j]][metric][k])
                        alg.append(alg_name[i])

                print alg_name[i],xlabel[j],count,len(stats[alg_name[i]][xlabel[j]]['TxNodes']),i
                print p_nodes

    plot_data = {'x': x_vector, 'y': y_vector, 'alg': alg}

    #print plot_data
    ax=sns.lineplot(x='x', y='y', data=plot_data ,hue='alg', markers=True,style="alg", dashes=False)

    if metric=='PDR':
        plt.ylim([0.85,1])

    #plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), title='Scheduling Algorithms', prop={'size': 10})
    if metric in ['e2e delay','jitter']:
            plt.legend(loc='upper right', bbox_to_anchor=(1, 1), prop={'size': 9})
    elif metric in ['PDR']:
            plt.legend(loc='upper right', bbox_to_anchor=(1, 0.5), prop={'size': 9})
    else:
        plt.legend(loc='center left', bbox_to_anchor=(0.0, 0.9), prop={'size': 9})
    plt.savefig(path + metric+'_lines_rate2'  +'.pdf', format='pdf')


def plot_fig_lines3(index1,stats,xlabel): # multtiple nodes number
    fig = plt.figure(index1)
    ax = fig.add_axes([0.12, 0.17, 0.8, 0.8])
    out_label = [ 3, 5, 10, 20, 30, 40, 60, 80, 100, 120]

    plt.xlabel('Period of packet generation (sec)', fontsize=f_size-2)
    plt.ylabel("Number Of Packets", fontsize=f_size-6)

    x = []

    for i in range(0, len(xlabel)):
        if xlabel[i] in out_label:
            x.append(xlabel[i])

    #ax.set_xticks(x, xlabel)
    plt.xticks(x, out_label, fontsize=f_size - 6, rotation='vertical')
    plt.yticks(fontsize=f_size - 6)

    x_vector=[]
    y_vector=[]
    alg=[]
    for i in range(0, len(alg_name)):
        for j in range(0,len(xlabel)):
            print alg_name[i],xlabel[j]
            print stats[alg_name[i]][xlabel[j]]['pktType']

            if xlabel[j] in out_label:
                for k in range(0,len(stats[alg_name[i]][xlabel[j]]['pktType'])):

                    x_vector.append(xlabel[j])
                    sum_ctrl=0
               
                    for key,value in stats[alg_name[i]][xlabel[j]]['pktType'][k].items():
                        if key !='DATA':
                            sum_ctrl+=value

                    data_sum=stats[alg_name[i]][xlabel[j]]['pktType'][k]['EB']
                    y_vector.append(float(data_sum))#/data_sum))
                    alg.append(alg_name[i])#+" ctrl")
                    '''

                    x_vector.append(xlabel[j])
                    y_vector.append(stats[alg_name[i]][xlabel[j]]['pktType'][k]['DIO'])
                    alg.append(alg_name[i] + " data")
                    '''
    plot_data = {'x': x_vector, 'y': y_vector, 'alg': alg}

    #print plot_data
    ax=sns.lineplot(x='x', y='y', data=plot_data ,hue='alg', markers=True,style="alg", dashes=False)



    #plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), title='Scheduling Algorithms', prop={'size': 10})
    plt.legend(loc='center left', bbox_to_anchor=(0.0, 0.9), prop={'size': 9})
    plt.savefig(path +'EB'  +'.pdf', format='pdf')

def plot_fig_lines4(index1,metric,stats,xlabel): # multtiple nodes number
    fig = plt.figure(index1)
    ax = fig.add_axes([0.12, 0.17, 0.8, 0.8])
    out_label = [ 3,5, 10, 20, 30, 40, 60, 80, 100, 120]
    out_label = [10, 20, 40, 60, 80, 100]

    y_ms=0
    #plt.xlabel('Period of packet generation (sec)', fontsize=f_size-2)
    plt.xlabel('Number of Nodes', fontsize=f_size - 2)
    if metric=='e2e delay':
        plt.ylabel("End 2 End Delay (ms)", fontsize=f_size-6)
        y_ms=1
    elif metric=='PDR':
        plt.ylabel("PDR", fontsize=f_size - 6)
    elif metric=='energy':
        plt.ylabel("Energy per Packet(mJ)", fontsize=f_size - 6)
    elif metric=='lifetime':
        plt.ylabel("Network Lifetime (years)", fontsize=f_size - 6)
    elif metric=='jitter':
        plt.ylabel("Jitter (ms)", fontsize=f_size - 6)
        y_ms=1
    elif metric == 'ETX':
        plt.ylabel("ETX", fontsize=f_size - 6)
    elif metric == 'avg_hops':
        plt.ylabel("Average #Hops", fontsize=f_size - 6)
    x = []

    for i in range(0, len(xlabel)):
        if xlabel[i] in out_label:
            x.append(xlabel[i])

    #ax.set_xticks(x, xlabel)
    plt.xticks(x, out_label, fontsize=f_size - 6, rotation='vertical')
    plt.yticks(fontsize=f_size - 6)

    x_vector=[]
    y_vector=[]
    alg=[]
    print "\n Metric", metric
    for i in range(0, len(alg_name)):

        for j in range(0,len(xlabel)):
            #print stats[alg_name[i]][xlabel[j]][metric]
            if xlabel[j] in out_label:
                count=0
                p_nodes=[]
                for k in range(0,len(stats[alg_name[i]][xlabel[j]][metric])):
                    valid=False
                    if count < 20 and stats[alg_name[i]][xlabel[j]]['TxNodes'][k]==39 and i in [0,2]:
                        valid = True


                    valid=True
                    if valid==True:
                        count+=1
                        p_nodes.append(stats[alg_name[i]][xlabel[j]]['TxNodes'][k])
                        x_vector.append(xlabel[j])
                        if y_ms==1:
                            y_vector.append(stats[alg_name[i]][xlabel[j]][metric][k]*10.0)
                        else:
                            y_vector.append(stats[alg_name[i]][xlabel[j]][metric][k])
                        alg.append(alg_name[i])

                print alg_name[i],xlabel[j],count,len(stats[alg_name[i]][xlabel[j]]['TxNodes']),i
                print p_nodes

    plot_data = {'x': x_vector, 'y': y_vector, 'alg': alg}

    #print plot_data
    ax=sns.lineplot(x='x', y='y', data=plot_data ,hue='alg', markers=True,style="alg", dashes=False)

    if metric=='PDR':
        plt.ylim([0.85,1])

    #plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), title='Scheduling Algorithms', prop={'size': 10})
    if metric in ['e2e delay','jitter']:
            plt.legend(loc='upper right', bbox_to_anchor=(1, 1), prop={'size': 9})
    elif metric in ['PDR']:
            plt.legend(loc='upper right', bbox_to_anchor=(1, 0.5), prop={'size': 9})
    else:
        plt.legend(loc='center left', bbox_to_anchor=(0.0, 0.9), prop={'size': 9})
    plt.savefig(path + metric+'_lines_nd2'  +'.pdf', format='pdf')

# =========================== main ============================================

def main():
    x_pkt=[5,10,30,60,120]
    x_pkt = [1,3,5,10,20,30,40,60,80,100,120]
    x_nodes=[10,20,40,60,80,100]
    #Load
    stats_pkt = np.load('lines_rate6.npy').item()#lines_nodes_1.npy
    #stats = np.load('alg.npy').item()
    #print stats_pkt

    metrics=['e2e delay','PDR','energy','lifetime','jitter','total_energy','avg_hops','ETX']

    '''
    plot_fig_multi_bar(1, 'e2e hop', stats)
    plot_fig_barA(2,'e2e delay' , stats)
    plot_fig_barA(3,'PDR' , stats)
    plot_fig_barA(4, 'energy', stats)
    plot_fig_barA(5,'lifetime' , stats)
    plot_fig_barA(6,'jitter' , stats)
    plot_fig_barA(7,'total_energy' , stats)
    plot_fig_barA(8, 'avg_hops', stats)
    plot_fig_barA(9, 'ETX', stats)
    '''
    #plot_fig_lines3(20, stats_pkt, x_pkt)
    #''
    for i in range(0,len(metrics)):
        plot_fig_lines2(i,metrics[i],stats_pkt,x_pkt)#x_pkt)
        #plot_fig_lines4(i,metrics[i],stats_pkt,x_nodes)#x_pkt)
    #'''
    plt.show()

if __name__ == '__main__':
    main()

