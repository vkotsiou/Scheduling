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
import copy

#sns.set_style("whitegrid")

alg_name=['MSF','Stratum','NLDSF','LDSF']
alg_name=['MSF','LLSF','Stratum','LDSF']
alg_name=['MSF','Stratum', 'LLSF','LDSF']
alg_name=['MSF','Stratum','LLSF','LDSF']
total_alg=len(alg_name)

path = '../plots/'

f_size=22
legend_fz=13

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
    #ax = fig.add_axes([0.15, 0.17, 0.8, 0.8])

    ax = fig.add_axes([0.20, 0.17, 0.75, 0.8])
    out_label = [ 1,2,3,5, 10, 20, 30, 40, 60, 80, 100, 120]
    out_label = [5,10, 20, 40, 60, 80, 100,120]

    y_ms=0
    plt.xlabel('Period of packet generation (sec)', fontsize=f_size-6)
    #plt.xlabel('Number of Nodes', fontsize=f_size - 2)
    if metric=='e2e delay':
        plt.ylabel("End 2 End Delay (ms)", fontsize=f_size-6)
        y_ms=1
    elif metric=='PDR':
        plt.ylabel("PDR (%)", fontsize=f_size - 6)
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
    elif metric == 'Alloc_Cells':
        plt.ylabel("Avg Allocated Cells", fontsize=f_size - 6)
    elif metric == 'Used_Cells':
        plt.ylabel("Avg Used Cells", fontsize=f_size - 6)
    elif metric == 'Cells_Allocation':
        plt.ylabel("% Cells Allocation", fontsize=f_size - 6)
    elif metric=='total_energy':
        plt.ylabel("Total Energy (mJ)", fontsize=f_size - 6)
    x = []

    for i in range(0, len(xlabel)):
        if xlabel[i] in out_label:
            x.append(xlabel[i])

    #ax.set_xticks(x, xlabel)
    plt.xticks(x, out_label, fontsize=f_size - 8, rotation='vertical')
    plt.yticks(fontsize=f_size - 8)

    x_vector=[]
    y_vector=[]
    alg=[]
    print "\n Metric", metric
    for i in range(0, len(alg_name)):

        for j in range(0,len(xlabel)):

            if xlabel[j] in out_label:
                count=0
                p_nodes=[]



                for k in range(0,len(stats[alg_name[i]][xlabel[j]]['PDR'])):
                    valid=True
                    '''
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
                    '''
                    #if metric=='lifetime' and alg_name[i]=='LDSF' and xlabel[j]==120 and stats[alg_name[i]][xlabel[j]][metric][k] <7.20 :
                     #   valid=False

                    if 1==1 and valid==True:
                        count+=1
                        p_nodes.append(stats[alg_name[i]][xlabel[j]]['TxNodes'][k])
                        x_vector.append(xlabel[j])
                        if y_ms==1:
                            y_vector.append(stats[alg_name[i]][xlabel[j]][metric][k]*10.0)
                        else:
                            if metric=='PDR':
                                y_vector.append(stats[alg_name[i]][xlabel[j]][metric][k]*100.0)
                            elif metric=='Alloc_Cells':
                                sum=0

                                for cell_i in range (0,len(stats[alg_name[i]][xlabel[j]][metric][k])):
                                    sum+=stats[alg_name[i]][xlabel[j]][metric][k][cell_i]
                                y_vector.append(sum)
                            elif metric == 'Used_Cells':
                                sum = 0

                                for cell_i in range(0, len(stats[alg_name[i]][xlabel[j]][metric][k])):
                                    sum += stats[alg_name[i]][xlabel[j]][metric][k][cell_i]
                                y_vector.append(sum)
                            elif metric=='Cells_Allocation':
                                if alg_name[i]=='LDSF':
                                    sum=0
                                    sum+=stats[alg_name[i]][xlabel[j]]['Alloc_Cells_total'][k][0]
                                    for cell_i in range(0,6):
                                        sum += stats[alg_name[i]][xlabel[j]]['Valloc_Cells'][k][cell_i]



                                    print stats[alg_name[i]][xlabel[j]]['Alloc_Cells_total'][k][0]
                                    print stats[alg_name[i]][xlabel[j]]['Valloc_Cells'][k]

                                    print "Sum", sum
                                    percentage = 100 * sum / (101.0 * stats[alg_name[i]][xlabel[j]]['Total_SlotFrames_Elapsed'][k])
                                else:
                                    sum = 0
                                    for cell_i in range(0, len(stats[alg_name[i]][xlabel[j]]['Alloc_Cells_total'][k])):
                                        sum += stats[alg_name[i]][xlabel[j]]['Alloc_Cells_total'][k][cell_i]

                                    print sum, stats[alg_name[i]][xlabel[j]]['Total_SlotFrames_Elapsed'][k]

                                    percentage=100 * sum/(101.0*stats[alg_name[i]][xlabel[j]]['Total_SlotFrames_Elapsed'][k])
                                print "%", percentage
                                y_vector.append(percentage)
                            else:
                                y_vector.append(stats[alg_name[i]][xlabel[j]][metric][k])

                        if metric=='lifetime' or metric=='total_energy':
                            print stats[alg_name[i]][xlabel[j]][metric][k]
                        alg.append(alg_name[i])

                print alg_name[i],xlabel[j],count,len(stats[alg_name[i]][xlabel[j]]['TxNodes']),i
                print p_nodes

    plot_data = {'x': x_vector, 'y': y_vector, 'alg': alg}

    #print plot_data
    ax=sns.lineplot(x='x', y='y', data=plot_data ,hue='alg', markers=True,style="alg", dashes=False)

    if metric=='PDR':
        plt.ylim([85,100])
    elif metric=='e2e delay':
        plt.ylim([0,2200])
    elif metric=='jitter':
        plt.ylim([0, 1500])
    elif metric=='lifetime':
        plt.ylim([0, 10])
    elif metric=='Cells_Allocation':
        plt.ylim([0,25])



    #plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), title='Scheduling Algorithms', prop={'size': 10})
    if metric in ['e2e delay','jitter']:
            plt.legend(loc='upper right', bbox_to_anchor=(1, 1), prop={'size': 12})
    elif metric in ['PDR']:
            plt.legend(loc='lower right', bbox_to_anchor=(1, 0.0), prop={'size': 12})
    else:
        plt.legend(loc='center left', bbox_to_anchor=(0.0, 0.85), prop={'size': 12})
    plt.savefig(path + metric+'_r'  +'.pdf', format='pdf')


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
    ax = fig.add_axes([0.15, 0.17, 0.8, 0.8])
    out_label = [ 3,5, 10, 20, 30, 40, 60, 80, 100, 120]
    out_label = [10, 20, 40, 60, 80, 100]

    y_ms=0
    #plt.xlabel('Period of packet generation (sec)', fontsize=f_size-2)
    plt.xlabel('Number of Nodes', fontsize=f_size - 6)
    if metric=='e2e delay':
        plt.ylabel("End 2 End Delay (ms)", fontsize=f_size-6)
        y_ms=1
    elif metric=='PDR':
        plt.ylabel("PDR (%)", fontsize=f_size - 6)
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
    plt.xticks(x, out_label, fontsize=f_size - 8, rotation='vertical')
    plt.yticks(fontsize=f_size - 8)

    x_vector=[]
    y_vector=[]
    alg=[]
    print "\n Metric", metric
    exStr={'60':[7,18,19,22,23],'40':[12,27],'80':[7,11,23,18],'100':[9,24,25,21]}
    for i in range(0, len(alg_name)):

        for j in range(0,len(xlabel)):
            #print stats[alg_name[i]][xlabel[j]][metric]
            if xlabel[j] in out_label:
                count=0
                p_nodes=[]
                for k in range(0,len(stats[alg_name[i]][xlabel[j]][metric])):
                    if i==1 and str(xlabel[j]) in exStr.keys()and k in exStr[str(xlabel[j])]:
                        pass
                    else:
                        p_nodes.append(stats[alg_name[i]][xlabel[j]]['TxNodes'][k])
                p_nodes.sort(reverse=True)

                if alg_name[i]=='LLSF':
                    #limit =0
                    print len(stats[alg_name[i]][xlabel[j]][metric]),'---', stats[alg_name[i]][xlabel[j]][metric]
                else:
                    limit = p_nodes[19]
                print limit,p_nodes
                c_nodes=[]
                values=[]
                for k in range(0, len(stats[alg_name[i]][xlabel[j]][metric])):
                    valid=False
                    if count < 20 and stats[alg_name[i]][xlabel[j]]['TxNodes'][k]>=limit:
                        valid = True
                    if i == 1 and str(xlabel[j]) in exStr.keys() and k in exStr[str(xlabel[j])]:
                        valid=False
                    if alg_name[i]=='LLSF' and stats[alg_name[i]][xlabel[j]]['e2e delay'][k] >150.0:
                       valid=False
                    #valid =True
                    if valid==True:
                        count+=1
                        c_nodes.append(stats[alg_name[i]][xlabel[j]]['TxNodes'][k])
                        x_vector.append(xlabel[j])
                        if y_ms==1:
                            y_vector.append(stats[alg_name[i]][xlabel[j]][metric][k]*10.0)
                        else:
                            if metric=='PDR':
                                y_vector.append(stats[alg_name[i]][xlabel[j]][metric][k]*100.0)
                            else:
                                y_vector.append(stats[alg_name[i]][xlabel[j]][metric][k])


                        alg.append(alg_name[i])
                        values.append(stats[alg_name[i]][xlabel[j]][metric][k])

                #print ,xlabel[j],count,len(stats[alg_name[i]][xlabel[j]]['TxNodes'])
                vl=['%.2f' % n for n in values]

                print alg_name[i],xlabel[j],len(vl),vl

    plot_data = {'x': x_vector, 'y': y_vector, 'alg': alg}

    #print plot_data
    ax=sns.lineplot(x='x', y='y', data=plot_data ,hue='alg', markers=True,style="alg", dashes=False)

    if metric=='PDR':
        plt.ylim([85,100])

    #plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), title='Scheduling Algorithms', prop={'size': 10})
    if metric in ['lifetime']:
            plt.legend(loc='upper right', bbox_to_anchor=(1, 1), prop={'size': 12})
    elif metric in ['PDR']:
            plt.legend(loc='lower right', bbox_to_anchor=(1, 0.0), prop={'size': 12})
    else:
        plt.legend(loc='center left', bbox_to_anchor=(0.0, 0.86), prop={'size': 12})
    plt.savefig(path + metric+'_nd'  +'.pdf', format='pdf')

def plot_stacked_bar(index1,metric,stats,alg,xlabel):
    out_label = [1, 3, 5, 10, 20, 40, 60, 80, 100, 120]
    n_groups = len(out_label)
    fig = plt.figure(index1)
    index = np.arange(n_groups)

    ax = fig.add_axes([0.15, 0.17, 0.8, 0.75])
    plt.gca().yaxis.grid(True)
    plt.gca().xaxis.grid(False)


    plt.xlabel('Period of packet generation (sec)', fontsize=f_size - 6)

    if metric=='Alloc_Cells':
        CellType = ('Shared', 'TX', 'RX')

    else:
        CellType = ( 'TX', 'RX')

    if metric == 'Alloc_Cells':
        plt.ylabel("Avg Allocated Cells", fontsize=f_size - 6)
    elif metric == 'Used_Cells':
        plt.ylabel("Avg Used Cells", fontsize=f_size - 6)

    # x-axis configuration
    x=[]
    for i in range(0, len(xlabel)):
        if xlabel[i] in out_label:
            x.append(xlabel[i])

    plt.xticks(x, out_label, fontsize=f_size - 8, rotation='vertical')
    plt.yticks(fontsize=f_size - 8)

    y_avg=[]
    y_conf = []
    st = []

    for  i in range(0, len(CellType)):
        t1=[]
        t2=[]
        y_avg.append(t1)
        y_conf.append(t2)

    z=0
    for j in range(0, len(xlabel)):

            if xlabel[j] in out_label:
                t3=[]
                st.append(t3)

                for l in range(0,len(CellType)):
                    t4=[]
                    st[z].append(t4)


                for k in range(0, len(stats[alg][xlabel[j]][metric])):

                        for cell_i in range(0, len(stats[alg][xlabel[j]][metric][k])):


                            st[z][cell_i].append(stats[alg][xlabel[j]][metric][k][cell_i])
                            #print z,cell_i,st[z][cell_i]


                z += 1

    print y_conf
    for i in range(0, len(out_label)):

        for j in range(0,len(CellType)):

            average, median, standard_deviation, minimum, maximum, confidence = statistics.stats(st[i][j], 0.05)
            #
            #print average, median, standard_deviation, minimum, maximum, confidence
            y_conf[j].append(confidence)
            y_avg[j].append(average)

    print y_conf


    plt.grid(linestyle='dashed', linewidth=0.5, axis='y')
    error_config = {'elinewidth': '0.1'}  # 'ecolor': '0.3',

    dataset1 = np.array(y_avg[0])
    dataset2 = np.array(y_avg[1])
    if metric=='Alloc_Cells':
        dataset3 = np.array(y_avg[2])



    p1 = plt.bar(index + 0.32 + bar_width, y_avg[0], bar_width, alpha=opacity, color=my_color[0],
                 error_kw=dict(lw=0.5, capsize=3, capthick=0.5, color=0.3), label=CellType[0], linewidth=1,
                edgecolor='grey',yerr=y_conf[0])#,

    p2 = plt.bar(index + 0.32 + bar_width, y_avg[1], bar_width, alpha=opacity, color=my_color[1],bottom = dataset1,
                     error_kw=dict(lw=0.5, capsize=3, capthick=0.5, color=0.3), label=CellType[1],
                    linewidth=1,edgecolor='grey',yerr=y_conf[1])#,

    if metric=='Alloc_Cells':
        p3 = plt.bar(index + 0.32 + bar_width, y_avg[2], bar_width, alpha=opacity, color=my_color[2], bottom=dataset1+dataset2,
                 error_kw=dict(lw=0.5, capsize=3, capthick=0.5, color=0.3), label=CellType[2],
                 linewidth=1, edgecolor='grey',yerr=y_conf[2])  # ,




    plt.tick_params(axis='y', which='major', labelsize=13)
    plt.tick_params(axis='x', which='major', labelsize=11)
    plt.yticks(fontsize=f_size - 6)
    plt.xticks(fontsize=f_size - 6)

    plt.title(alg)


    plt.legend(loc='upper right',  prop={'size': 10})


    plt.xticks(index + 0.32 + bar_width, out_label, fontsize=f_size-6)#,2.5
    locs, labels = plt.xticks()
    print locs,labels




    plt.savefig(path + metric+"_"+str(alg)+str(index1) +'.pdf', format='pdf')

# Double bar

def plot_stacked_bar2(index1,stats,alg,xlabel):
    out_label = [5, 10, 20, 40, 60, 80, 100, 120]
    n_groups = len(out_label)
    fig = plt.figure(index1)
    index = np.arange(n_groups)

    ax = fig.add_axes([0.15, 0.17, 0.8, 0.75])
    plt.gca().yaxis.grid(True)
    plt.gca().xaxis.grid(False)


    plt.xlabel('Period of packet generation (sec)', fontsize=f_size - 6)

    CellType = ('Shared', 'TX', 'RX','Used TX','Used RX')
    CellTypeB = ('TX','RX')

    metrics=['Alloc_Cells','Used_Cells']



    plt.ylabel("Avg Cells per SlotFrame", fontsize=f_size - 6)


    # x-axis configuration
    x=[]
    for i in range(0, len(xlabel)):
        if xlabel[i] in out_label:
            x.append(xlabel[i])

    plt.xticks(x, out_label, fontsize=f_size - 8, rotation='vertical')
    plt.yticks(fontsize=f_size - 8)

    y_avg=[]
    y_conf = []
    st = []

    for  i in range(0, 5):
        t1=[]
        t2=[]
        y_avg.append(t1)
        y_conf.append(t2)

    z=0
    for j in range(0, len(xlabel)):

            if xlabel[j] in out_label:
                t3=[]
                st.append(t3)

                for l in range(0,5):
                    t4=[]
                    st[z].append(t4)

                for v in range(0,len(metrics)):
                    for k in range(0, len(stats[alg][xlabel[j]][metrics[v]])):

                        for cell_i in range(0, len(stats[alg][xlabel[j]][metrics[v]][k])):


                            st[z][v*3+cell_i].append(stats[alg][xlabel[j]][metrics[v]][k][cell_i])
                            #print z,cell_i,st[z][cell_i]


                z += 1


    for i in range(0, len(out_label)):

        for j in range(0,5):

            average, median, standard_deviation, minimum, maximum, confidence = statistics.stats(st[i][j], 0.05)
            #
            #print average, median, standard_deviation, minimum, maximum, confidence
            y_conf[j].append(confidence)
            y_avg[j].append(average)



    plt.grid(linestyle='dashed', linewidth=0.5, axis='y')
    error_config = {'elinewidth': '0.1'}  # 'ecolor': '0.3',

    dataset1 = np.array(y_avg[0])
    dataset2 = np.array(y_avg[1])
    dataset3 = np.array(y_avg[2])
    # Used Cells
    dataset4 = np.array(y_avg[3])
    dataset5 = np.array(y_avg[4])

    p1 = plt.bar(index + 0.32 + bar_width, y_avg[0], bar_width, alpha=opacity, color=my_color[0],
                 error_kw=dict(lw=0.5, capsize=3, capthick=0.5, color=0.3), label=CellType[0], linewidth=1,
                edgecolor='grey',yerr=y_conf[0])#,

    p2 = plt.bar(index + 0.32 + bar_width, y_avg[1], bar_width, alpha=opacity, color=my_color[1],bottom = dataset1,
                     error_kw=dict(lw=0.5, capsize=3, capthick=0.5, color=0.3), label=CellType[1],
                    linewidth=1,edgecolor='grey',yerr=y_conf[1])#,

    p3 = plt.bar(index + 0.32 + bar_width, y_avg[2], bar_width, alpha=opacity, color=my_color[2], bottom=dataset1+dataset2,
                 error_kw=dict(lw=0.5, capsize=3, capthick=0.5, color=0.3), label=CellType[2],
                 linewidth=1, edgecolor='grey',yerr=y_conf[2])  # ,
    # --- Used Cells ---

    p4 = plt.bar(index  +0.32 +2*bar_width+0.05, y_avg[3], bar_width, alpha=opacity, color=my_color[1],
                 error_kw=dict(lw=0.5, capsize=3, capthick=0.5, color=0.3), label=CellType[3], linewidth=1,
                edgecolor='grey',yerr=y_conf[3],hatch="//")#,

    p5 = plt.bar(index  +0.32+ 2*bar_width+0.05, y_avg[4], bar_width, alpha=opacity, color=my_color[2],bottom = dataset4,
                     error_kw=dict(lw=0.5, capsize=3, capthick=0.5, color=0.3), label=CellType[4],
                    linewidth=1,edgecolor='grey',yerr=y_conf[4],hatch="//")#,




    plt.tick_params(axis='y', which='major', labelsize=13)
    plt.tick_params(axis='x', which='major', labelsize=11)
    plt.yticks(fontsize=f_size - 6)
    plt.xticks(fontsize=f_size - 6)

    plt.title(alg)


    plt.legend(loc='upper right',  prop={'size': 10})


    plt.xticks(index + 0.32 + bar_width, out_label, fontsize=f_size-6)#,2.5
    locs, labels = plt.xticks()

    plt.savefig(path +"Stacked_bar" +"_"+str(alg)+str(index1) +'.png', format='png')

def plot_stacked_bar3(index1,stats,pkt_rate):
    out_label = [5, 10, 20, 40, 60, 80, 100, 120]
    n_groups = len(alg_name)
    fig = plt.figure(index1)
    index = np.arange(n_groups)

    ax = fig.add_axes([0.15, 0.17, 0.8, 0.75])
    plt.gca().yaxis.grid(True)
    plt.gca().xaxis.grid(False)


    plt.xlabel('Algorithms', fontsize=f_size - 6)

    CellType = ('Shared/Autonomous', 'TX', 'RX','Used TX','Used RX')


    metrics=['Alloc_Cells_total','Used_Cells_total']

    plt.ylabel("%", fontsize=f_size - 6)


    # x-axis configuration
    '''
    x=[]
    for i in range(0,len(alg_name)):
        x.append(alg_name[i])



    plt.xticks(x, fontsize=f_size - 8)
    plt.yticks(fontsize=f_size - 8)
    '''

    y_avg=[]
    y_conf = []
    st = []

    for  i in range(0, 5):
        t1=[]
        t2=[]
        y_avg.append(t1)
        y_conf.append(t2)

    z=0
    for j in range(0,len(alg_name)):


                t3=[]
                st.append(t3)

                for l in range(0,5):
                    t4=[]
                    st[z].append(t4)

                for v in range(0,len(metrics)):
                    if metrics[v] =='Alloc_Cells_total' :
                        if alg_name[j]=='LDSF':
                            for k in range(0, len(stats[alg_name[j]][pkt_rate][metrics[v]])):
                                    NumOfSlotframes = stats[alg_name[j]][pkt_rate]['Total_SlotFrames_Elapsed'][k]
                                    for cell_i in range(0, 3):
                                        if cell_i==0: # SHARED
                                            value= stats[alg_name[j]][pkt_rate]['Alloc_Cells_total'][k][0]
                                        elif cell_i==1: # TX
                                            value = stats[alg_name[j]][pkt_rate]['Valloc_Cells'][k][0] +\
                                                    stats[alg_name[j]][pkt_rate]['Valloc_Cells'][k][1] + \
                                                    stats[alg_name[j]][pkt_rate]['Valloc_Cells'][k][4]
                                        elif cell_i==2 : #RX
                                            value = stats[alg_name[j]][pkt_rate]['Valloc_Cells'][k][2] + \
                                                    stats[alg_name[j]][pkt_rate]['Valloc_Cells'][k][3] + \
                                                    stats[alg_name[j]][pkt_rate]['Valloc_Cells'][k][5]


                                        percentage = 100 * value / (101.0 * NumOfSlotframes)
                                        st[z][v*3+cell_i].append(percentage)
                        else:

                            for k in range(0, len(stats[alg_name[j]][pkt_rate][metrics[v]])):
                                NumOfSlotframes =  stats[alg_name[j]][pkt_rate]['Total_SlotFrames_Elapsed'][k]
                                for cell_i in range(0, len(stats[alg_name[j]][pkt_rate][metrics[v]][k])):

                                    percentage = 100 * stats[alg_name[j]][pkt_rate][metrics[v]][k][cell_i]/ (101.0 * NumOfSlotframes)

                                    st[z][v * 3 + cell_i].append(percentage)

                                #print z,cell_i,st[z][cell_i]
                else:
                        for k in range(0, len(stats[alg_name[j]][pkt_rate][metrics[v]])):
                            NumOfSlotframes = stats[alg_name[j]][pkt_rate]['Total_SlotFrames_Elapsed'][k]
                            for cell_i in range(0, len(stats[alg_name[j]][pkt_rate][metrics[v]][k])):
                                percentage = 100 * stats[alg_name[j]][pkt_rate][metrics[v]][k][cell_i] / (101.0 * NumOfSlotframes)
                                st[z][v * 3 + cell_i].append(percentage)
                            # print z,cell_i,st[z][cell_i]


                z += 1


    for i in range(0, len(alg_name)):

        for j in range(0,5):

            average, median, standard_deviation, minimum, maximum, confidence = statistics.stats(st[i][j], 0.05)
            #
            #print average, median, standard_deviation, minimum, maximum, confidence
            y_conf[j].append(confidence)
            y_avg[j].append(average)


    plt.grid(linestyle='dashed', linewidth=0.5, axis='y')
    error_config = {'elinewidth': '0.1'}  # 'ecolor': '0.3',

    dataset1 = np.array(y_avg[0])
    dataset2 = np.array(y_avg[1])
    dataset3 = np.array(y_avg[2])
    # Used Cells
    dataset4 = np.array(y_avg[3])
    dataset5 = np.array(y_avg[4])

    p1 = plt.bar(index + 0.32 + bar_width, y_avg[0], bar_width, alpha=opacity, color=my_color[0],
                 error_kw=dict(lw=0.5, capsize=3, capthick=0.5, color=0.3), label=CellType[0], linewidth=1,
                 edgecolor='grey',yerr=y_conf[0])#,

    p2 = plt.bar(index + 0.32 + bar_width, y_avg[1], bar_width, alpha=opacity, color=my_color[1],bottom = dataset1,
                     error_kw=dict(lw=0.5, capsize=3, capthick=0.5, color=0.3), label=CellType[1],
                    linewidth=1,edgecolor='grey',yerr=y_conf[1])#,

    p3 = plt.bar(index + 0.32 + bar_width, y_avg[2], bar_width, alpha=opacity, color=my_color[2], bottom=dataset1+dataset2,
                 error_kw=dict(lw=0.5, capsize=3, capthick=0.5, color=0.3), label=CellType[2],
                 linewidth=1, edgecolor='grey',yerr=y_conf[2])  # ,
    # --- Used Cells ---

    p4 = plt.bar(index  +0.32 +2*bar_width+0.05, y_avg[3], bar_width, alpha=opacity, color=my_color[1],
                 error_kw=dict(lw=0.5, capsize=3, capthick=0.5, color=0.3), label=CellType[3], linewidth=1,
                edgecolor='grey',yerr=y_conf[3],hatch="//")#,

    p5 = plt.bar(index  +0.32+ 2*bar_width+0.05, y_avg[4], bar_width, alpha=opacity, color=my_color[2],bottom = dataset4,
                     error_kw=dict(lw=0.5, capsize=3, capthick=0.5, color=0.3), label=CellType[4],
                    linewidth=1,edgecolor='grey',yerr=y_conf[4],hatch="//")#,

    plt.xticks(index + 0.32 + 1.6*bar_width, alg_name, fontsize=f_size - 6)  # bar_width/2
    plt.tick_params(axis='y', which='major', labelsize=13)
    plt.tick_params(axis='x', which='major', labelsize=11)
    plt.yticks(fontsize=f_size - 6)

    title="Packet Rate: 1 packet per "+str(pkt_rate)+ " sec"
    plt.title(title)
    p7, = plt.plot([0], marker='None',
               linestyle='None', label='dummy-empty')

    categories1 = ['Shared/Autonomous', 'TX','RX']
    categories2=['TX','RX']
    leg3 =plt.legend([p7, p1, p2, p3,p7, p4, p5],
                  ['Allocated'] + categories1 + ['Used'] + categories2,
                  loc='upper right', ncol=2, prop={'size': 10})  # Two columns, vertical group labels

    plt.ylim([0,25])
   # plt.legend(loc='upper right',  prop={'size': 10})


   # plt.xticks(index + 0.32 + bar_width, out_label, fontsize=f_size-6)#,2.5
   # locs, labels = plt.xticks()





    plt.savefig(path +"Stacked_bar3" +"_"+str(pkt_rate)+str(index1) +'.pdf', format='pdf')

# =========================== main ============================================

def main():
    x_pkt=[5,10,30,60,120]
    x_pkt = [1,2,3,5,10,20,40,60,80,100,120]
    x_nodes=[10,20,40,60,80,100]
    x_pkt = [5,10,20,40,60,80,100,120]
    #Load
    '''
    stats_pkt = np.load('lines_nodes_1.npy').item()
    stats_pktA = np.load('LLSFNodes_+.npy').item()

   
    print "A", stats_pktA.keys()
    stats_pkt['LLSF']=copy.deepcopy(stats_pktA['LLSF'])

    print stats_pkt.keys()
    '''
    stats_pkt={}
    stats_pktA = np.load('MSF_Throughput+.npy').item()
    stats_pktB = np.load('Stratum_Throughput+.npy').item()
    stats_pktC = np.load('LLSF_Throughput+.npy').item()
    stats_pktD = np.load('LDSF_Throughput+.npy').item()

    print "A", stats_pktA.keys()
    for key in stats_pktA:
        stats_pkt[key] = copy.deepcopy(stats_pktA[key])

    
    for key in stats_pktB:
        stats_pkt[key] = copy.deepcopy(stats_pktB[key])

    print "C", stats_pktC.keys()
    for key in stats_pktC:
        stats_pkt[key] = copy.deepcopy(stats_pktC[key])

    print "D", stats_pktD.keys()
    for key in stats_pktD:
        stats_pkt[key] = copy.deepcopy(stats_pktD[key])

    print "ALL",stats_pkt.keys()


    #print stats_pkt


    metrics=['e2e delay','PDR','energy','lifetime','jitter','total_energy','avg_hops','ETX'] #,'Alloc_Cells','Used_Cells','Cells_Allocation']
    metrics=['total_energy']
   # metrics = ['Cells_Allocation']
    #metrics = ['e2e delay', 'PDR','lifetime', 'jitter']
    #plot_fig_lines3(20, stats_pkt, x_pkt)

    '''
    for i in range(0, len(metrics)):
        plot_fig_lines4(i,metrics[i],stats_pkt,x_nodes)
    '''

    #'''
    for i in range(0,len(metrics)):
      plot_fig_lines2(i,metrics[i],stats_pkt,x_pkt)
        #plot_fig_lines4(i,metrics[i],stats_pkt,x_nodes)

    '''
    for i in range(0,len(alg_name)):
        plot_stacked_bar2(20+i+1, stats_pkt, alg_name[i], x_pkt)
    

    for i in range(0,len(x_pkt)):
        plot_stacked_bar3(30 + i + 1, stats_pkt, x_pkt[i])
    '''

     #plot_stacked_bar(2*i,'Used_Cells',stats_pkt,alg_name[i],x_pkt)
     #plot_stacked_bar(2 * i+1, 'Alloc_Cells', stats_pkt, alg_name[i], x_pkt)
    plt.show()

if __name__ == '__main__':
    main()

