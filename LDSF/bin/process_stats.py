from __future__ import division

# =========================== adjust path =====================================

import os
import sys
import netaddr
import os
from os import walk
import numpy as np

if __name__ == '__main__':
    here = sys.path[0]
    sys.path.insert(0, os.path.join(here, '..'))

# ========================== imports ==========================================

import json
import glob
import numpy as np

from SimEngine import SimLog
import SimEngine.Mote.MoteDefines as d

# =========================== defines =========================================

DAGROOT_ID = 0  # we assume first mote is DAGRoot
DAGROOT_IP = 'fd00::1:0'
BATTERY_AA_CAPACITY_mAh = 2821.5


alg_name=['MSF','Stratum','NLDSF','LDSF']
alg_name=['MSF', 'Stratum', 'LLSF','LDSF']
alg_name=['MSF3']

#alg_name=['Stratum']
# =========================== decorators ======================================

def openfile(func):
    def inner(inputfile):
        with open(inputfile, 'r') as f:
            return func(f)
    return inner

# =========================== helpers =========================================

def mean(numbers):
    return float(sum(numbers)) / max(len(numbers), 1)

def init_mote():
    return {
        'upstream_num_tx': 0,
        'upstream_num_rx': 0,
        'upstream_num_lost': 0,
        'join_asn': None,
        'join_time_s': None,
        'sync_asn': None,
        'sync_time_s': None,
        'charge_asn': None,
        'upstream_pkts': {},
        'latencies': [],
        'hops': [],
        'charge': None,
        'packet_drops': {},
        'lifetime_AA_years': None,
        'avg_current_uA': None,
    }

# =========================== KPIs ============================================
max_hops=12

@openfile
def kpis_all(inputfile):

    allstats = {} # indexed by run_id, mote_id
    hops_delay =[]

    for i in range(0,max_hops):
        temp=[]
        hops_delay.append(temp)

    file_settings = json.loads(inputfile.readline())  # first line contains settings

    # === gather raw stats

    for line in inputfile:
        logline = json.loads(line)

        # shorthands
        run_id = logline['_run_id']
        if '_asn' in logline: # TODO this should be enforced in each line
            asn = logline['_asn']
        if '_mote_id' in logline: # TODO this should be enforced in each line
            mote_id = logline['_mote_id']

        # populate
        if run_id not in allstats:
            allstats[run_id] = {}
        if (
                ('_mote_id' in logline)
                and
                (mote_id not in allstats[run_id])
                #and
                #(mote_id != DAGROOT_ID)
            ):
            allstats[run_id][mote_id] = init_mote()
        #print  logline['_type']
        if   logline['_type'] == SimLog.LOG_TSCH_SYNCED['type']:
            # sync'ed

            # shorthands
            mote_id    = logline['_mote_id']

            # only log non-dagRoot sync times
            if mote_id == DAGROOT_ID:
                continue

            allstats[run_id][mote_id]['sync_asn']  = asn
            allstats[run_id][mote_id]['sync_time_s'] = asn*file_settings['tsch_slotDuration']

        elif logline['_type'] == SimLog.LOG_SECJOIN_JOINED['type']:
            # joined

            # shorthands
            mote_id    = logline['_mote_id']

            # only log non-dagRoot join times
            if mote_id == DAGROOT_ID:
                continue

            # populate
            assert allstats[run_id][mote_id]['sync_asn'] is not None
            allstats[run_id][mote_id]['join_asn']  = asn
            allstats[run_id][mote_id]['join_time_s'] = asn*file_settings['tsch_slotDuration']

        elif logline['_type'] == SimLog.LOG_APP_TX['type']:
            # packet transmission

            # shorthands
            mote_id    = logline['_mote_id']
            dstIp      = logline['packet']['net']['dstIp']
            appcounter = logline['packet']['app']['appcounter']

            # only log upstream packets
            if dstIp != DAGROOT_IP:
                continue

            # populate
            assert allstats[run_id][mote_id]['join_asn'] is not None
            if appcounter not in allstats[run_id][mote_id]['upstream_pkts']:
                allstats[run_id][mote_id]['upstream_pkts'][appcounter] = {
                    'hops': 0,
                }

            allstats[run_id][mote_id]['upstream_pkts'][appcounter]['tx_asn'] = asn

        elif logline['_type'] == SimLog.LOG_APP_RX['type']:
            # packet reception

            # shorthands
            mote_id    = netaddr.IPAddress(logline['packet']['net']['srcIp']).words[-1]
            dstIp      = logline['packet']['net']['dstIp']
            hop_limit  = logline['packet']['net']['hop_limit']
            appcounter = logline['packet']['app']['appcounter']

            # only log upstream packets
            if dstIp != DAGROOT_IP:
                continue

            allstats[run_id][mote_id]['upstream_pkts'][appcounter]['hops']   = (
                d.IPV6_DEFAULT_HOP_LIMIT - hop_limit + 1
            )
            allstats[run_id][mote_id]['upstream_pkts'][appcounter]['rx_asn'] = asn

        elif logline['_type'] == SimLog.LOG_PACKET_DROPPED['type']:
            # packet dropped

            # shorthands
            mote_id    = logline['_mote_id']
            reason     = logline['reason']

            type       = logline['packet']['type']



            # populate
            if reason not in allstats[run_id][mote_id]['packet_drops']:
                allstats[run_id][mote_id]['packet_drops'][reason] = 0

            #print reason
            allstats[run_id][mote_id]['packet_drops'][reason] += 1
            '''
            if type=='DATA':
                appcounter = logline['packet']['app']['appcounter']
                gen_mac    =logline['packet']['app']['gen_mac']

                print "GenMAC",gen_mac,"TX",mote_id,"Counter",appcounter,"Reason",reason   #:)

            '''


        elif logline['_type'] == SimLog.LOG_BATT_CHARGE['type']:
            # battery charge

            # shorthands
            mote_id    = logline['_mote_id']
            charge     = logline['charge']

            # only log non-dagRoot charge
            if mote_id == DAGROOT_ID:
                continue

            # populate
            if allstats[run_id][mote_id]['charge'] is not None:
                assert charge >= allstats[run_id][mote_id]['charge']

            allstats[run_id][mote_id]['charge_asn'] = asn
            allstats[run_id][mote_id]['charge']     = charge

        #LOG_TSCH_ALLOC_CELLS = {'type': 'tsch.alloc_cells', 'keys': ['_mote_id', 'slotframe_no', 'shared', 'tx', 'rx']}
        elif logline['_type'] == 'tsch.alloc_cells':  #:) Throughput
            mote_id = logline['_mote_id']
            slotframe =logline['slotframe_no']
            shared = logline['shared']
            tx = logline['tx']
            rx= logline['rx']

            if 'Alloc_Cells' not in  allstats[run_id][mote_id]:
                allstats[run_id][mote_id]['Alloc_Cells']={'slotframes':0,'shared':0,'tx':0,'rx':0}


            allstats[run_id][mote_id]['Alloc_Cells']['slotframes'] += 1
            allstats[run_id][mote_id]['Alloc_Cells']['shared'] +=shared
            allstats[run_id][mote_id]['Alloc_Cells']['tx'] +=tx
            allstats[run_id][mote_id]['Alloc_Cells']['rx'] += rx

            #print mote_id, allstats[run_id][mote_id]['Alloc_Cells']

        # LOG_TSCH_USED_CELLS                   = {'type': 'tsch.used_cells',               'keys': ['_mote_id','asn','type']}
        elif logline['_type'] == 'tsch.used_cells':  #:) Throughput

            typeAct= logline['type']
            typeCell=logline['cell_type']

            if 'Used_Cells' not in allstats[run_id][mote_id]:
                allstats[run_id][mote_id]['Used_Cells'] = {'tx': 0, 'rx': 0}

            if typeAct=='TX':
                allstats[run_id][mote_id]['Used_Cells']['tx'] +=1
            elif typeAct == 'RX':
                allstats[run_id][mote_id]['Used_Cells']['rx'] += 1

        #LOG_TSCH_VALLOC_CELLS = {'type': 'tsch.valloc_cells', 'keys': ['_mote_id', 'main_TX', 'ghost_TX', 'main_RX', 'ghost_RX']}
        elif logline['_type'] == 'tsch.valloc_cells':  #:) Throughput
            mote_id = logline['_mote_id']

            main_tx = logline['main_TX']
            ghost_tx = logline['ghost_TX']
            main_rx = logline['main_RX']
            ghost_rx = logline['ghost_RX']
            keep_alive_tx=logline['keep_alive_TX']
            keep_alive_rx = logline['keep_alive_RX']



            if 'Valloc_Cells' not in allstats[run_id][mote_id]:
                allstats[run_id][mote_id]['Valloc_Cells'] = {'main_tx': 0, 'ghost_tx':0,'main_rx': 0,'ghost_rx':0,'keep_alive_tx':0,'keep_alive_rx':0}

            allstats[run_id][mote_id]['Valloc_Cells']['main_tx'] += main_tx
            allstats[run_id][mote_id]['Valloc_Cells']['ghost_tx'] += ghost_tx
            allstats[run_id][mote_id]['Valloc_Cells']['main_rx'] += main_rx
            allstats[run_id][mote_id]['Valloc_Cells']['ghost_rx'] +=ghost_rx
            allstats[run_id][mote_id]['Valloc_Cells']['keep_alive_tx'] += keep_alive_tx
            allstats[run_id][mote_id]['Valloc_Cells']['keep_alive_rx'] += keep_alive_rx




        elif  logline['_type']=='tsch.txdone':
            # shorthands
            mote_id = logline['_mote_id']
            ack= logline['isACKed']
            type = logline['packet']['type']


            if 'pktType' not in  allstats[run_id][mote_id]:
                allstats[run_id][mote_id]['pktType']={}

            if type not in allstats[run_id][mote_id]['pktType'] :
                allstats[run_id][mote_id]['pktType'][type]=[1,0]
            else:
                allstats[run_id][mote_id]['pktType'][type][0] += 1

            if ack == True:
                allstats[run_id][mote_id]['pktType'][type][1]+=1

            if 'packets' not in allstats[run_id][mote_id]:
                    allstats[run_id][mote_id]['packets'] =0
                    allstats[run_id][mote_id]['acks']=0

            if type == "DATA":
                allstats[run_id][mote_id]['packets']+=1

                if ack==True:
                    allstats[run_id][mote_id]['acks'] += 1

                #print allstats[run_id][mote_id]['packets'] ,allstats[run_id][mote_id]['acks']

    # === compute advanced motestats
    sum_charge = 0
    jitter_per_mote=[]
    etx_per_mote=[]
    total_tx_packets=0
    total_acks=0
    sum_hops=0
    maxHops=-1
    s_hops=[]
    pkt_hops=[]
    count_hops=0
    joined_motes=0
    tx_nodes = 0
    alloc_cells_total=[0,0,0]
    used_cells_total=[0,0]
    alloc_cells=[[],[],[]]
    used_cells=[[],[]]
    total_slotrames=0
    Valloc_cells=[0,0,0,0,0,0]
    # TX , Rx
    for (run_id, per_mote_stats) in allstats.items():
        for (mote_id, motestats) in per_mote_stats.items():
            if mote_id != 0:

                if (motestats['sync_asn'] is not None) and (motestats['charge_asn'] is not None):
                    # avg_current, lifetime_AA
                    if (
                            (motestats['charge'] <= 0)
                            or
                            (motestats['charge_asn'] == motestats['sync_asn'])
                        ):
                        motestats['lifetime_AA_years'] = 'N/A'
                    else:
                        motestats['avg_current_uA'] = motestats['charge']/float((motestats['charge_asn']-motestats['sync_asn']) * file_settings['tsch_slotDuration'])
                        #assert motestats['avg_current_uA'] > 0
                        motestats['lifetime_AA_years'] = (BATTERY_AA_CAPACITY_mAh*1000/float(motestats['avg_current_uA']))/(24.0*365)
                        sum_charge += motestats['charge']

                if motestats['join_asn'] is not None:
                    joined_motes+=1
                    # latencies, upstream_num_tx, upstream_num_rx, upstream_num_lost
                    for (appcounter, pktstats) in allstats[run_id][mote_id]['upstream_pkts'].items():
                        motestats['upstream_num_tx']      += 1
                        if 'rx_asn' in pktstats:
                            motestats['upstream_num_rx']  += 1
                            thislatency = (pktstats['rx_asn']-pktstats['tx_asn'])*file_settings['tsch_slotDuration']
                            latency_slot=pktstats['rx_asn']-pktstats['tx_asn']
                            motestats['latencies']  += [thislatency]
                            motestats['hops']       += [pktstats['hops']]

                            hops_delay[pktstats['hops']].append(latency_slot)

                        else:
                            motestats['upstream_num_lost'] += 1
                            #print mote_id,appcounter
                    if (motestats['upstream_num_rx'] > 0) and (motestats['upstream_num_tx'] > 0):
                        motestats['latency_min_s'] = min(motestats['latencies'])
                        motestats['latency_avg_s'] = sum(motestats['latencies'])/float(len(motestats['latencies']))
                        motestats['latency_max_s'] = max(motestats['latencies'])
                        motestats['upstream_reliability'] = motestats['upstream_num_rx']/float(motestats['upstream_num_tx'])
                        motestats['avg_hops'] = sum(motestats['hops'])/float(len(motestats['hops']))

                        if motestats['avg_hops'] > maxHops:
                            maxHops=motestats['avg_hops']

                        sum_hops+=  motestats['avg_hops']

                        count_hops+=1
                        s_hops.append(motestats['avg_hops'])
                        pkt_hops.append(len(motestats['latencies']))

                    if motestats['acks']!=0:                    #:) ETX
                        ETX= motestats['packets']/float(motestats['acks'])
                        etx_per_mote.append(ETX)
                        total_tx_packets += motestats['packets']
                        total_acks +=motestats['acks']
                        #print mote_id , ETX   #:)

                #print mote_id,motestats['packet_drops']
                sum_jitter = 0
                if len (motestats['latencies'])>=2:
                    for i in range(1,len (motestats['latencies']) ):
                        sum_jitter += abs(motestats['latencies'][i]-motestats['latencies'][i-1])/float(file_settings['tsch_slotDuration'])

                    jitter_per_mote.append(sum_jitter/len (motestats['latencies']))
                    #print mote_id,"Average Jitter",sum_jitter/len (motestats['latencies'])
            #allocated cells
            if motestats['join_asn'] is not None or mote_id==0:
                sum_shared = 0
                sum_tx = 0
                sum_rx = 0


                numOfSlotframes=motestats['Alloc_Cells']['slotframes']
                total_slotrames +=numOfSlotframes


                alloc_cells[0].append(motestats['Alloc_Cells']['shared'] / float(numOfSlotframes))
                alloc_cells[1].append(motestats['Alloc_Cells']['tx'] / float(numOfSlotframes))
                alloc_cells[2].append( motestats['Alloc_Cells']['rx']/ float(numOfSlotframes))
                #print motestats['Alloc_Cells']['tx'] / float(numOfSlotframes),  motestats['Alloc_Cells']['rx']/ float(numOfSlotframes)

                used_cells[0].append(motestats['Used_Cells']['tx']/ float(numOfSlotframes))
                used_cells[1].append(motestats['Used_Cells']['rx']/ float(numOfSlotframes))

                total_used= motestats['Used_Cells']['tx'] + motestats['Used_Cells']['rx']
                total_allocated=motestats['Alloc_Cells']['shared'] + motestats['Alloc_Cells']['tx'] + motestats['Alloc_Cells']['rx']

                percentage = total_used/float(total_allocated)
                alloc_cells_total[0]+=motestats['Alloc_Cells']['shared']
                alloc_cells_total[1] += motestats['Alloc_Cells']['tx']
                alloc_cells_total[2] += motestats['Alloc_Cells']['rx']

                used_cells_total[0]+=motestats['Used_Cells']['tx']
                used_cells_total[1] += motestats['Used_Cells']['rx']

                if 'Valloc_Cells' in motestats.keys():
                    Valloc_cells[0]+=motestats['Valloc_Cells']['main_tx']
                    Valloc_cells[1] += motestats['Valloc_Cells']['ghost_tx']
                    Valloc_cells[2] += motestats['Valloc_Cells']['main_rx']
                    Valloc_cells[3] += motestats['Valloc_Cells']['ghost_rx']
                    Valloc_cells[4] += motestats['Valloc_Cells']['keep_alive_tx']
                    Valloc_cells[5] += motestats['Valloc_Cells']['keep_alive_rx']

                #print mote_id,"%", percentage*100

    # === network stats
    pktTypes = {'JOIN_REQUEST': [0,0,0], 'DIO': [0,0,0], 'KEEP_ALIVE':[0,0,0] , 'DAO': [0,0,0], 'EB': [0,0,0], '6P': [0,0,0], 'JOIN_RESPONSE': [0,0,0], 'DATA': [0,0,0], 'DIS': [0,0,0]}
    for (run_id, per_mote_stats) in allstats.items():

        #-- define stats

        app_packets_sent = 0
        app_packets_received = 0
        app_packets_lost = 0


        joining_times = []
        us_latencies = []
        current_consumed = []
        lifetimes = []
        slot_duration = file_settings['tsch_slotDuration']

        #-- compute stats

        for (mote_id, motestats) in per_mote_stats.items():
            if mote_id == DAGROOT_ID:
                continue

            # counters
            if 'pktType' in motestats:
                #print mote_id , motestats['pktType']

                for key,value in motestats['pktType'].items():
                    #print key,value
                    for j in range (0,2):
                        pktTypes[key][j]+= value[j]
                    if pktTypes[key][1]!=0:
                        pktTypes[key][2] =float(pktTypes[key][0] /pktTypes[key][1])

            app_packets_sent += motestats['upstream_num_tx']
            app_packets_received += motestats['upstream_num_rx']
            app_packets_lost += motestats['upstream_num_lost']

            if motestats['upstream_num_rx'] != 0:
                tx_nodes+=1
            # joining times

            if motestats['join_asn'] is not None:
                joining_times.append(motestats['join_asn'])

            # latency

            us_latencies += motestats['latencies']

            # current consumed

            current_consumed.append(motestats['charge'])
            if motestats['lifetime_AA_years'] is not None:
                lifetimes.append(motestats['lifetime_AA_years'])

        #-- save stats
    '''
        allstats[run_id]['global-stats'] = {
            'e2e-upstream-delivery': [
                {
                    'name': 'E2E Upstream Delivery Ratio',
                    'unit': '%',
                    'value': 1 - app_packets_lost / app_packets_sent
                },
                {
                    'name': 'E2E Upstream Loss Rate',
                    'unit': '%',
                    'value':  app_packets_lost / app_packets_sent
                }
            ],
            'e2e-upstream-latency': [
                {
                    'name': 'E2E Upstream Latency',
                    'unit': 's',
                    'mean': mean(us_latencies),
                    'min': min(us_latencies),
                    'max': max(us_latencies),
                    '99%': np.percentile(us_latencies, 99)
                },
                {
                    'name': 'E2E Upstream Latency',
                    'unit': 'slots',
                    'mean': mean(us_latencies) / slot_duration,
                    'min': min(us_latencies) / slot_duration,
                    'max': max(us_latencies) / slot_duration,
                    '99%': np.percentile(us_latencies, 99) / slot_duration
                }
            ],
            'current-consumed': [
                {
                    'name': 'Current Consumed',
                    'unit': 'mA',
                    'mean': mean(current_consumed),
                    '99%': np.percentile(current_consumed, 99)
                }
            ],
            'network_lifetime':[
                {
                    'name': 'Network Lifetime',
                    'unit': 'years',
                    'min': min(lifetimes),
                    'total_capacity_mAh': BATTERY_AA_CAPACITY_mAh,
                }
            ],
            'joining-time': [
                {
                    'name': 'Joining Time',
                    'unit': 'slots',
                    'min': min(joining_times),
                    'max': max(joining_times),
                    'mean': mean(joining_times),
                    '99%': np.percentile(joining_times, 99)
                }
            ],
            'app-packets-sent': [
                {
                    'name': 'Number of application packets sent',
                    'total': app_packets_sent
                }
            ],
            'app_packets_received': [
                {
                    'name': 'Number of application packets received',
                    'total': app_packets_received
                }
            ],
            'app_packets_lost': [
                {
                    'name': 'Number of application packets lost',
                    'total': app_packets_lost
                }
            ]
        }
    '''

    '''
    for (run_id, per_mote_stats) in allstats.items():
        for (mote_id, motestats) in per_mote_stats.items():
            if 'sync_asn' in motestats:
                del motestats['sync_asn']
            if 'charge_asn' in motestats:
                del motestats['charge_asn']
                del motestats['charge']
            if 'join_asn' in motestats:
                del motestats['upstream_pkts']
                del motestats['hops']
                del motestats['join_asn']
    '''


    V=3.3
    energy_per_pkt=(sum_charge*V/1000)/app_packets_received



    delay= mean(us_latencies) / slot_duration

    output={}
    output['e2e delay']=delay
    output['PDR']= 1 - app_packets_lost / app_packets_sent
    output['e2e hop']=[]
    output['energy']=energy_per_pkt
    print lifetimes
    output['lifetime']=min(lifetimes)
    output['jitter']=mean(jitter_per_mote)
    output['parameters']=[file_settings['sf_class'],file_settings['app_pkPeriod'],file_settings['exec_numMotes']]
    output['ETX']=mean(etx_per_mote)
    output['pktType']=pktTypes
    output['Alloc_Cells']=[0,0,0]  #Shared ,tx,rx
    output['Used_Cells']=[0,0] #tx,rx
    output['Alloc_Cells'] = [0, 0, 0]  # Shared ,tx,rx
    output['Used_Cells'] = [0, 0]  # tx,rx
    output['Alloc_Cells_total'] = [0, 0, 0]  # Shared ,tx,rx
    output['Used_Cells_total'] = [0, 0]  # tx,rx
    output['Total_SlotFrames_Elapsed']=total_slotrames
    output['Valloc_Cells'] = [Valloc_cells[0],Valloc_cells[1],Valloc_cells[2],Valloc_cells[3],Valloc_cells[4],Valloc_cells[5]]

    #print sum_charge,sum(current_consumed)

    output['total_energy']=(sum_charge*V/1000.0)
    output['avg_hops']=sum_hops/float(count_hops)

    #Throughput

    for i in range(0,3):
        output['Alloc_Cells'][i]=mean(alloc_cells[i])
        output['Alloc_Cells_total'][i] =alloc_cells_total[i]

    for i in range(0,2):
        output['Used_Cells'][i]=mean(used_cells[i])
        output['Used_Cells_total'][i] = used_cells_total[i]

    print 'Alloc',output['Alloc_Cells'], output['Used_Cells']


    #weighted hops
    total_packets=sum(pkt_hops)
    wghtHops=0
    for i in range(0,len(s_hops)):
        wghtHops+=pkt_hops[i]/float(total_packets) * s_hops[i]

    avg_hops=sum_hops/float(count_hops)
    ETX2=total_tx_packets / float(total_acks)
    pkt_rate = output['parameters'][1]
    nd=output['parameters'][2]
    #print "Rate",pkt_rate,

    valid=True

    print output['parameters'][0], nd, pkt_rate,
    #print output['parameters'][0],pkt_rate,
    if joined_motes<nd-1:
        print " ** ",
        valid =False
    if tx_nodes <nd-1:
        print " !!", tx_nodes,
        valid=False

    print "PDR",output['PDR'],"Delay",delay,"Motes",joined_motes,"Hops",sum_hops/float(count_hops),wghtHops,"ETX", output['ETX'] ,total_tx_packets/float(total_acks),
    print "Theoretical Delay",5*avg_hops*(2*output['ETX']-1),5*wghtHops*(2*ETX2-1),
    print "Max Hops",maxHops
    print pktTypes
    #output['ETX']*5*sum_hops/float(count_hops),output['ETX']*5*wghtHops
    for i in range(0, max_hops):
        if hops_delay[i]!=0:
            output['e2e hop'].append(mean(hops_delay[i]))
        else:
            output['e2e hop'].append(mean(0))


    output['TxNodes']=tx_nodes
    output['file']=inputfile

    return valid, output


def main():
    x_pkt = [1,2,3,5,10,20,30,40,60,80,100,120]
    x_nodes=[10,20,40,60,80,100]

    stats = {}
    stats_pkt = {}
    stats_node = {}
    for i in range(0, len(alg_name)):
        stats[alg_name[i]] = {'e2e delay': [], 'e2e hop': [], 'PDR': [], "energy": [], "lifetime": [], "jitter": [],"total_energy":[],"avg_hops":[],"ETX":[]}
        stats_pkt[alg_name[i]] = {}
        for j in range(0, len(x_pkt)):
            stats_pkt[alg_name[i]][x_pkt[j]] = {'e2e delay': [], 'e2e hop': [], 'PDR': [], "energy": [], "lifetime": [],
                                                "jitter": [],"total_energy":[],"avg_hops":[],"ETX":[],'pktType':[],'TxNodes':[],'file':[],
                                                'Alloc_Cells':[],'Used_Cells':[],'Alloc_Cells_total':[],'Used_Cells_total':[],'Total_SlotFrames_Elapsed':[],'Valloc_Cells':[]}
        #for j in range(0, len(x_nodes)):
        #    stats_pkt[alg_name[i]][x_nodes[j]] = {'e2e delay': [], 'e2e hop': [], 'PDR': [], "energy": [], "lifetime": [],
        #                                        "jitter": [], "total_energy": [], "avg_hops": [], "ETX": [],
         #                                       'pktType': [], 'TxNodes': [], 'file': []}
    #print stats_pkt

    # Define data path
    dir_alg = ['MSF\\bin\simData', 'Stratum\\bin\SimData','NLDSF\\bin\\simData', 'LDSF\\bin\\simData']
    dir_alg = ['MSF', 'nrgMSF','Stratum', 'LLSF','LDSF']
    dir_alg = ['MSF3']


    RootPath = 'C:\Users\\Vassilios\Google Drive\OpenWSN\Scheduling\\LDSF\\bin\\simData'
    #RootPath='C:\Users\\Vassilios\Desktop\\Results\\'
    RootPath='C:\Users\\Vassilios\\Desktop\Mega\Scheduling\LDSF\\bin\simData'
    RootPath = 'C:\Users\\Vassilios\Desktop\\New Results-CBR\\'
    RootPath ='C:\Users\Vassilios\Desktop\Results-Nodes\\'
    #RootPath='C:\Users\\Vassilios\Desktop\Stratum'
    RootPath = 'C:\Users\\Vassilios\Google Drive\OpenWSN\Scheduling\\LDSF\\bin\\simData'
    RootPath ='C:\Users\Vassilios\Desktop\Results - Throughput Rate\\'
    #RootPath='C:\Users\k\Desktop\Results\\'
    #RootPath='C:\Users\Eleni\Desktop\Results\\'
    #RootPath='C:\Users\Vassilios\Desktop\Results-Nodes\\'



    for i in range(0,len(alg_name)):
        stats_pkt={}
        stats_pkt[alg_name[i]] = {}
        for j in range(0, len(x_pkt)):
            stats_pkt[alg_name[i]][x_pkt[j]] = {'e2e delay': [], 'e2e hop': [], 'PDR': [], "energy": [], "lifetime": [],
                                                "jitter": [], "total_energy": [], "avg_hops": [], "ETX": [],
                                                'pktType': [], 'TxNodes': [], 'file': [],
                                                'Alloc_Cells': [], 'Used_Cells': [], 'Alloc_Cells_total': [],
                                                'Used_Cells_total': [], 'Total_SlotFrames_Elapsed': [],'Valloc_Cells':[]}

        data_path = RootPath + dir_alg[i]
        l = 0
        #print i,data_path
        j=0
        for (dirpath, dirnames, filenames) in walk(data_path):
            print dirpath,"  j:",j
            #print filenames

            d = dirpath.split("\\")
            #print len(d)
            if len(d) == 7: #10  #7
                k=1
                if  len(filenames)==1:
                    k=0
                    print "!!!! Ignore "
                if k!=0:
                    file = dirpath + "\\" + filenames[k]
                    print file

                    valid,output = kpis_all(file)

                    #valid=False
                    if  1==1 : #valid==True
                        print  output,"\n\n"


                        pkt_rate = output['parameters'][1]
                        nd=output['parameters'][2]
                        x_val=nd#pkt_rate  #nd
                        #print "Rate", x_val
                        stats_pkt[alg_name[i]][x_val]['e2e delay'].append(output['e2e delay'])
                        stats_pkt[alg_name[i]][x_val]['PDR'].append(output['PDR'])
                        stats_pkt[alg_name[i]][x_val]['e2e hop'].append(output['e2e hop'])
                        stats_pkt[alg_name[i]][x_val]['energy'].append(output['energy'])
                        stats_pkt[alg_name[i]][x_val]['lifetime'].append(output['lifetime'])
                        stats_pkt[alg_name[i]][x_val]['jitter'].append(output['jitter'])
                        stats_pkt[alg_name[i]][x_val]['total_energy'].append(output['total_energy'])
                        stats_pkt[alg_name[i]][x_val]['avg_hops'].append(output['avg_hops'])
                        stats_pkt[alg_name[i]][x_val]['ETX'].append(output['ETX'])
                        stats_pkt[alg_name[i]][x_val]['pktType'].append(output['pktType'])
                        stats_pkt[alg_name[i]][x_val]['TxNodes'].append(output['TxNodes'])
                        stats_pkt[alg_name[i]][x_val]['file'].append(output['file'])
                        stats_pkt[alg_name[i]][x_val]['Alloc_Cells'].append(output['Alloc_Cells'])
                        stats_pkt[alg_name[i]][x_val]['Used_Cells'].append(output['Used_Cells'])
                        stats_pkt[alg_name[i]][x_val]['Alloc_Cells_total'].append(output['Alloc_Cells_total'])
                        stats_pkt[alg_name[i]][x_val]['Used_Cells_total'].append(output['Used_Cells_total'])
                        stats_pkt[alg_name[i]][x_val]['Total_SlotFrames_Elapsed'].append(output['Total_SlotFrames_Elapsed'])
                        stats_pkt[alg_name[i]][x_val]['Valloc_Cells'].append(output['Valloc_Cells'])
            j+=1


        #print stats_pkt
        np.save(alg_name[i]+'Nodes_+.npy', stats_pkt)


    #Save
    #np.save('alg.npy', stats)
    #
    #np.save('Throughput_nrgMSF.npy',stats_pkt)

    '''
    for i in range(0,5):
        print "   Algorithm -",alg_name[i]
        for val in x_pkt:
          print val," : ", len(stats_pkt[alg_name[i]][val]['e2e delay'])
        print "\n"
    '''

if __name__ == '__main__':
    main()



