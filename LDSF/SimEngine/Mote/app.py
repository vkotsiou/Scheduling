"""
An application lives on each node
"""

# =========================== imports =========================================

from abc import abstractmethod
import random

# Mote sub-modules

# Simulator-wide modules
import SimEngine
import MoteDefines as d

# =========================== defines =========================================

# =========================== helpers =========================================

# =========================== body ============================================

def App(mote):
    """factory method for application
    """

    settings = SimEngine.SimSettings.SimSettings()

    # use mote.id to determine whether it is the root or not instead of using
    # mote.dagRoot because mote.dagRoot is not initialized when application is
    # instantiated
    if mote.id == 0:
        return AppRoot(mote)
    else:
        return globals()[settings.app](mote)

class AppBase(object):
    """Base class for Applications.
    """

    def __init__(self, mote, **kwargs):

        # store params
        self.mote       = mote

        # singletons (quicker access, instead of recreating every time)
        self.engine     = SimEngine.SimEngine.SimEngine()
        self.settings   = SimEngine.SimSettings.SimSettings()
        self.log        = SimEngine.SimLog.SimLog().log

        # local variables
        self.appcounter = 0

    #======================== public ==========================================

    @abstractmethod
    def startSendingData(self):
        """Starts the application process.

        Typically, this methods schedules an event to send a packet to the root.
        """
        raise NotImplementedError()  # abstractmethod

    def recvPacket(self, packet):
        """Receive a packet destined to this application
        """
        # log and mote stats
        self.log(
            SimEngine.SimLog.LOG_APP_RX,
            {
                '_mote_id': self.mote.id,
                'packet'  : packet
            }
        )

    #======================== private ==========================================

    def _generate_packet(
            self,
            dstIp,
            packet_type,
            packet_length,
        ):

        # create data packet
        dataPacket = {
            'type':              packet_type,
            'net': {
                'srcIp':         self.mote.get_ipv6_global_addr(),
                'dstIp':         dstIp,
                'packet_length': packet_length
            },
            'app': {
                'appcounter':    self.appcounter,
                'timestamp':     self.engine.getAsn(),
                'gen_mac': self.mote.get_mac_addr(),  # Packet generation mac
                #'flow': self.mote.flow_gen_time,  #:) Include in Data Packet Information
                #'hops': 0,
                #'start_tx': self.mote.start_tx,
                'pkt_flows': self.mote.tsch.pkt_flow,
                'next':0  # 1-upcoming data packet of the
            }

        }

        # update appcounter

        print "&ID", self.mote.id, "ASN", self.engine.getAsn(), "Counter", self.appcounter, self.mote.flow_gen_time
        self.appcounter += 1
        # :)

        return dataPacket

    def _send_packet(self, dstIp, packet_length):

        # abort if I'm not ready to send DATA yet
        if self.mote.clear_to_send_EBs_DATA()==False:
            return

        # create
        packet = self._generate_packet(
            dstIp          = dstIp,
            packet_type    = d.PKT_TYPE_DATA,
            packet_length  = packet_length
        )

        # log
        self.log(
            SimEngine.SimLog.LOG_APP_TX,
            {
                '_mote_id':       self.mote.id,
                'packet':         packet,
            }
        )

        # send
        self.mote.sixlowpan.sendPacket(packet)

class AppRoot(AppBase):
    """Handle application packets from motes
    """

    # the payload length of application ACK
    APP_PK_LENGTH = 10

    def __init__(self, mote):
        super(AppRoot, self).__init__(mote)

    #======================== public ==========================================

    def startSendingData(self):
        # nothing to schedule
        pass

    def recvPacket(self, packet):
        assert self.mote.dagRoot

        # log and update mote stats
        self.log(
            SimEngine.SimLog.LOG_APP_RX,
            {
                '_mote_id': self.mote.id,
                'packet'  : packet
            }
        )

    #======================== private ==========================================

    def _send_ack(self, destination, packet_length=None):

        if packet_length is None:
            packet_length = self.APP_PK_LENGTH

        self._send_packet(
            dstIp          = destination,
            packet_length  = packet_length
        )

class AppPeriodic(AppBase):

    """Send a packet periodically

    Intervals are distributed uniformly between (pkPeriod-pkPeriodVar)
    and (pkPeriod+pkPeriodVar).

    The first timing to send a packet is randomly chosen between [next
    asn, (next asn + pkPeriod)].
    """

    def __init__(self, mote, **kwargs):
        super(AppPeriodic, self).__init__(mote)
        self.sending_first_packet = True

    #======================== public ==========================================

    def startSendingData(self):
        if self.sending_first_packet:
            self._schedule_transmission()

    #======================== public ==========================================

    def _schedule_transmission(self):
        assert self.settings.app_pkPeriod >= 0
        if self.settings.app_pkPeriod == 0:
            return
        Q=0
        if self.sending_first_packet:
            # compute initial time within the range of [next asn, next asn+pkPeriod]
            delay = self.settings.tsch_slotDuration + (self.settings.app_pkPeriod * random.random())
            #:)
            Q=1


            self.sending_first_packet = False
        else:
            # compute random delay
            assert self.settings.app_pkPeriodVar < 1
            delay = self.settings.app_pkPeriod * (1 + random.uniform(-self.settings.app_pkPeriodVar, self.settings.app_pkPeriodVar))

            #:)
            delay = self.settings.app_pkPeriod + self.settings.app_pkPeriod * 1 * self.settings.tsch_slotDuration

        operA = (self.settings.tsch_slotframeLength - 1) / d.SubFrameSize

        if Q == 1:

                rsubframe = int( ((self.engine.getAsn() + delay / 0.01) % self.settings.tsch_slotframeLength - 1) / (d.SubFrameSize))
                vsubframe = int(((self.engine.getAsn() + delay / 0.01) / self.settings.tsch_slotframeLength)) % (self.mote.tsch.VirtualSlotFrameSize / self.settings.tsch_slotframeLength) * operA + rsubframe

                self.mote.tsch.add_pkt_flow(self.mote.get_mac_addr(),1,-1,0,vsubframe)  #mac,id,start_tx,hop,flow_gen
                #Reserve flow for DAO - we have not delay constrains
                dao_vsubframe=(vsubframe +20) % 200 #(se lf.mote.tsch.VirtualSlotFrameSize/d.SubFrameSize)
                keep_alive_vsubframe1=(vsubframe +70) %200 #(self.mote.tsch.VirtualSlotFrameSize/d.SubFrameSize)
                keep_alive_vsubframe2 = (vsubframe + 90) % 200 #(self.mote.tsch.VirtualSlotFrameSize / d.SubFrameSize)
                keep_alive_vsubframe3 = (vsubframe + 110) % 200 #(self.mote.tsch.VirtualSlotFrameSize / d.SubFrameSize)
                print "=ID",self.mote.id,"DAO start",dao_vsubframe,self.mote.tsch.VirtualSlotFrameSize/d.SubFrameSize

                #self.mote.tsch.add_pkt_flow(self.mote.get_mac_addr(), 0, -1, 0, dao_vsubframe)
                #self.mote.tsch.add_pkt_flow(self.mote.get_mac_addr(), 2, -1, 0, keep_alive_vsubframe1)
                #self.mote.tsch.add_pkt_flow(self.mote.get_mac_addr(), 3, -1, 0, keep_alive_vsubframe2)
                #self.mote.tsch.add_pkt_flow(self.mote.get_mac_addr(), 4, -1, 0, keep_alive_vsubframe3) # random 1551383064

        else:
                rsubframe = int((self.engine.getAsn() % self.settings.tsch_slotframeLength - 1) / (d.SubFrameSize))
                vsubframe = int((self.engine.getAsn() / self.settings.tsch_slotframeLength)) % (self.mote.tsch.VirtualSlotFrameSize / self.settings.tsch_slotframeLength) * operA + rsubframe
            # print "ID",self.mote.id,"ASN",self.engine.getAsn(),"Delay",delay,"subframe",int((self.engine.getAsn() % self.settings.tsch_slotframeLength-1)/(d.SubFrameSize)),"Mod",(self.engine.getAsn() % self.settings.tsch_slotframeLength-1)%(d.SubFrameSize)

        self.mote.flow_gen_time = vsubframe
        print "ID", self.mote.id, "ASN", self.engine.getAsn(), "Vindex", self.mote.tsch.asn2vindex(self.engine.getAsn()), "subframe", vsubframe, "hops", self.mote.hops, rsubframe, delay

        # schedule
        self.engine.scheduleIn(
            delay           = delay,
            cb              = self._send_a_single_packet,
            uniqueTag       = (
                'AppPeriodic',
                'scheduled_by_{0}'.format(self.mote.id)
            ),
            intraSlotOrder  = d.INTRASLOTORDER_ADMINTASKS,
        )

    def _send_a_single_packet(self):
        if self.mote.rpl.dodagId == None:
            # it seems we left the dodag; stop the transmission
            self.sending_first_packet = True
            return

        #:) Don't send data packets if schedule doesn't exists.
        if self.mote.lock_schedule == 0:
            self.sending_first_packet =False# == True  #:)- ==


            #'''
            if self.mote.tsch.pending_6P_ADD()==False:
                print "ReSending",self.mote.id
                self.mote.sf._request_adding_cells(
                    neighbor=self.mote.rpl.getPreferredParent(),
                    num_txrx_cells=0,
                    num_tx_cells=10,
                    num_rx_cells=0


                )
            #'''
        else:
            self._send_packet(
                dstIp          = self.mote.rpl.dodagId,
                packet_length  = self.settings.app_pkLength
            )
        # schedule the next transmission
        self._schedule_transmission()

class AppBurst(AppBase):
    """Generate burst traffic to the root at the specified time (only once)
    """

    #======================== public ==========================================

    def startSendingData(self):
        # schedule app_burstNumPackets packets in app_burstTimestamp
        self.engine.scheduleIn(
            delay           = self.settings.app_burstTimestamp,
            cb              = self._send_burst_packets,
            uniqueTag       = (
                'AppBurst',
                'scheduled_by_{0}'.format(self.mote.id)
            ),
            intraSlotOrder  = d.INTRASLOTORDER_ADMINTASKS,
        )

    #======================== private ==========================================

    def _send_burst_packets(self):
        if self.mote.rpl.dodagId == None:
            # we're not part of the network now
            return

        for _ in range(0, self.settings.app_burstNumPackets):
            self._send_packet(
                dstIp         = self.mote.rpl.dodagId,
                packet_length = self.settings.app_pkLength
            )
