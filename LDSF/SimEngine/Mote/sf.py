# =========================== imports =========================================

import random
import sys
from abc import abstractmethod

import netaddr

import SimEngine
import MoteDefines as d
import sixp

# =========================== defines =========================================

# =========================== helpers =========================================

# =========================== body ============================================

class SchedulingFunction(object):
    def __new__(cls, mote):
        settings    = SimEngine.SimSettings.SimSettings()
        class_name  = 'SchedulingFunction{0}'.format(settings.sf_class)
        return getattr(sys.modules[__name__], class_name)(mote)

class SchedulingFunctionBase(object):

    SLOTFRAME_HANDLE = 0

    def __init__(self, mote):

        # store params
        self.mote            = mote

        # singletons (quicker access, instead of recreating every time)
        self.settings        = SimEngine.SimSettings.SimSettings()
        self.engine          = SimEngine.SimEngine.SimEngine()
        self.log             = SimEngine.SimLog.SimLog().log

    # ======================= public ==========================================

    # === admin

    @abstractmethod
    def start(self):
        """
        tells SF when should start working
        """
        raise NotImplementedError() # abstractmethod

    @abstractmethod
    def stop(self):
        '''
        tells SF when should stop working
        '''
        raise NotImplementedError() # abstractmethod

    # === indications from other layers

    @abstractmethod
    def indication_neighbor_added(self, neighbor_mac_addr):
        pass

    @abstractmethod
    def indication_dedicated_tx_cell_elapsed(self,cell,used):
        """[from TSCH] just passed a dedicated TX cell. used=False means we didn't use it.

        """
        raise NotImplementedError() # abstractmethod

    @abstractmethod
    def indication_parent_change(self, old_parent, new_parent):
        """
        [from RPL] decided to change parents.
        """
        raise NotImplementedError() # abstractmethod

    @abstractmethod
    def detect_schedule_inconsistency(self, peerMac):
        raise NotImplementedError() # abstractmethod

    @abstractmethod
    def recv_request(self, packet):
        raise NotImplementedError() # abstractmethod

    @abstractmethod
    def clear_to_send_EBs_DATA(self):
        raise NotImplementedError() # abstractmethod


class SchedulingFunctionSFNone(SchedulingFunctionBase):

    def __init__(self, mote):
        super(SchedulingFunctionSFNone, self).__init__(mote)

    def start(self):
        pass # do nothing

    def stop(self):
        pass # do nothing

    def indication_neighbor_added(self, neighbor_mac_addr):
        pass # do nothing

    def indication_dedicated_tx_cell_elapsed(self,cell,used):
        pass # do nothing

    def indication_parent_change(self, old_parent, new_parent):
        pass # do nothing

    def detect_schedule_inconsistency(self, peerMac):
        pass # do nothing

    def recv_request(self, packet):
        pass # do nothing

    def clear_to_send_EBs_DATA(self):
        # always return True
        return True

# :)
#  Low Delay  Scheduling Function
#
class SchedulingFunctionLDSF(SchedulingFunctionBase):

    SLOTFRAME_HANDLE = 1
    INITIAL_NUM_TXRX_CELLS = 0
    DEFAULT_CELL_LIST_LEN = 20 #:)  #int((101 -1) / (2*d.SubFrameSize))
    TXRX_CELL_OPT = [d.CELLOPTION_TX, d.CELLOPTION_RX, d.CELLOPTION_SHARED]
    TX_CELL_OPT   = [d.CELLOPTION_TX]
    RX_CELL_OPT   = [d.CELLOPTION_RX]

    def __init__(self, mote):
        # initialize parent class
        super(SchedulingFunctionLDSF, self).__init__(mote)  #:)

        # (additional) local variables
        self.num_cells_elapsed = 0       # number of dedicated cells passed
        self.num_cells_used    = 0       # number of dedicated cells used
        self.cell_utilization  = 0
        self.locked_slots      = set([]) # slots in on-going ADD transactions

        self.mote = mote  # :)
        self.child_count = 0
        self.children = []

        print "~~~ Low Delay Scheduling Function  ~~~ ", self.mote.id

    # ======================= public ==========================================

    # === admin

    def start(self):
        # enable the pending bit feature
        #:) disable pending bit - Remeber to disable it from all other scheduling functions

        #self.mote.tsch.enable_pending_bit()

        # install SlotFrame 1 which has the same length as SlotFrame 0
        slotframe_0 = self.mote.tsch.get_slotframe(0)
        self.mote.tsch.add_slotframe(
            slotframe_handle = self.SLOTFRAME_HANDLE,
            length           = slotframe_0.length
        )

        # Keep track of children :)
        factor=1
        if self.mote.id==0:
            factor=2
        for i in range(0, factor*d.SubFrameSize):
            self.children.append(-1)


        if self.mote.dagRoot:
            # do nothing
            pass
        else:
            self._housekeeping_collision()

    def stop(self):
        # uninstall SlotFrame 1 instead of removing all the cells there
        self.mote.tsch.delete_slotframe(self.SLOTFRAME_HANDLE)

        if self.mote.dagRoot:
            # do nothing
            pass
        else:
            self.engine.removeFutureEvent((self.mote.id, '_housekeeping_collision'))

    # === indications from other layers

    def indication_neighbor_added(self, neighbor_mac_addr):

        pass

    def indication_dedicated_tx_cell_elapsed(self, cell, used):
        assert cell.mac_addr is not None

        preferred_parent = self.mote.rpl.getPreferredParent()
        if (
                (cell.mac_addr == preferred_parent)
                and
                (cell.options == [d.CELLOPTION_TX])
            ):

            # increment cell passed counter
            self.num_cells_elapsed += 1

            # increment cell used counter
            if used:
                self.num_cells_used += 1
            #:)
            '''
            # adapt number of cells if necessary
            if d.MSF_MAX_NUMCELLS <= self.num_cells_elapsed:
                self._adapt_to_traffic(preferred_parent)
                self._reset_cell_counters()
            '''

    def indication_parent_change(self, old_parent, new_parent):
        assert old_parent != new_parent

        # allocate the same number of cells to the new parent as it has for the
        # old parent; note that there could be three types of cells:
        # (TX=1,RX=1,SHARED=1), (TX=1), and (RX=1)
        if old_parent is None:
            num_tx_cells = 10 #:)
            num_rx_cells = 0
        else:
            dedicated_cells = self.mote.tsch.get_cells(
                mac_addr         = old_parent,
                slotframe_handle = self.SLOTFRAME_HANDLE
            )
            num_tx_cells = len(
                filter(
                    lambda cell: cell.options == [d.CELLOPTION_TX],
                    dedicated_cells
                )
            )
            num_rx_cells = len(
                filter(
                    lambda cell: cell.options == [d.CELLOPTION_RX],
                    dedicated_cells
                )
            )
        self._request_adding_cells(
            neighbor       = new_parent,
            num_txrx_cells = self.INITIAL_NUM_TXRX_CELLS,
            num_tx_cells   = num_tx_cells,
            num_rx_cells   = num_rx_cells
        )

        # clear all the cells allocated for the old parent
        def _callback(event, packet):
            if event == d.SIXP_CALLBACK_EVENT_FAILURE:
                # optimization which is not mentioned in 6P/MSF spec: remove
                # the outstanding transaction because we're deleting all the
                # cells scheduled to the peer now. The outstanding transaction
                # should have the same transaction key as the packet we were
                # trying to send.
                self.mote.sixp.abort_transaction(
                    initiator_mac_addr=packet['mac']['srcMac'],
                    responder_mac_addr=packet['mac']['dstMac']
                )
            self._clear_cells(old_parent)

        if old_parent is not None:
            self.mote.sixp.send_request(
                dstMac   = old_parent,
                command  = d.SIXP_CMD_CLEAR,
                callback = _callback
            )

    def detect_schedule_inconsistency(self, peerMac):
        # send a CLEAR request to the peer
        self.mote.sixp.send_request(
            dstMac   = peerMac,
            command  = d.SIXP_CMD_CLEAR,
            callback = lambda event, packet: self._clear_cells(peerMac)
        )

    def recv_request(self, packet):
        if   packet['app']['code'] == d.SIXP_CMD_ADD:
            self._receive_add_request(packet)
        elif packet['app']['code'] == d.SIXP_CMD_DELETE:
            self._receive_delete_request(packet)
        elif packet['app']['code'] == d.SIXP_CMD_CLEAR:
            self._receive_clear_request(packet)
        elif packet['app']['code'] == d.SIXP_CMD_RELOCATE:
            self._receive_relocate_request(packet)
        else:
            # not implemented or not supported
            # ignore this request
            pass

    def clear_to_send_EBs_DATA(self):
        # True if we have a TX cell to the current parent
        slotframe = self.mote.tsch.get_slotframe(self.SLOTFRAME_HANDLE)
        parent_addr = self.mote.rpl.getPreferredParent()
        if (
                (slotframe is None)
                or
                (parent_addr is None)
            ):
            tx_cells = []
        else:
            tx_cells = [
                cell for cell in slotframe.get_cells_by_mac_addr(parent_addr)
                if d.CELLOPTION_TX in cell.options
            ]

        if self.mote.dagRoot:
            ret_val = True
        else:
            ret_val = bool(tx_cells)

        return ret_val

    # ======================= private ==========================================

    def _reset_cell_counters(self):
        self.num_cells_elapsed = 0
        self.num_cells_used   = 0

    def _adapt_to_traffic(self, neighbor):
        """
        Check the cells counters and trigger 6P commands if cells need to be
        added or removed.

        :param int neighbor:
        :return:
        """
        cell_utilization = self.num_cells_used / float(self.num_cells_elapsed)
        if cell_utilization != self.cell_utilization:
            self.log(
                SimEngine.SimLog.LOG_MSF_CELL_UTILIZATION,
                {
                    '_mote_id'    : self.mote.id,
                    'neighbor'    : neighbor,
                    'value'       : '{0}% -> {1}%'.format(
                        int(self.cell_utilization * 100),
                        int(cell_utilization * 100)
                    )
                }
            )
            self.cell_utilization = cell_utilization
        if d.MSF_LIM_NUMCELLSUSED_HIGH < cell_utilization:
            # add one TX cell
            self._request_adding_cells(
                neighbor     = neighbor,
                num_tx_cells = 1
            )

        elif cell_utilization < d.MSF_LIM_NUMCELLSUSED_LOW:
            tx_cells = filter(
                lambda cell: cell.options == [d.CELLOPTION_TX],
                self.mote.tsch.get_cells(neighbor, self.SLOTFRAME_HANDLE)
            )
            # delete one *TX* cell but we need to keep one dedicated
            # cell to our parent at least
            if len(tx_cells) > 1:
                self._request_deleting_cells(
                    neighbor     = neighbor,
                    num_cells    = 1,
                    cell_options = self.TX_CELL_OPT
                )

    def _housekeeping_collision(self):
        """
        Identify cells where schedule collisions occur.
        draft-chang-6tisch-msf-01:
            The key for detecting a schedule collision is that, if a node has
            several cells to the same preferred parent, all cells should exhibit
            the same PDR.  A cell which exhibits a PDR significantly lower than
            the others indicates than there are collisions on that cell.
        :return:
        """
        return  #:) disable

        if self.mote.tsch.get_slotframe(self.SLOTFRAME_HANDLE) is None:
            return

        # for quick access; get preferred parent
        preferred_parent = self.mote.rpl.getPreferredParent()

        # collect TX cells which has enough numTX
        tx_cell_list = filter(
            lambda cell: cell.options == [d.CELLOPTION_TX],
            self.mote.tsch.get_cells(preferred_parent, self.SLOTFRAME_HANDLE)
        )
        tx_cell_list = {
            cell.slot_offset: cell for cell in tx_cell_list if (
                d.MSF_MIN_NUM_TX < cell.num_tx
            )
        }

        # collect PDRs of the TX cells
        def pdr(cell):
            assert cell.num_tx > 0
            return cell.num_tx_ack / float(cell.num_tx)
        pdr_list = {
            slotOffset: pdr(cell) for slotOffset, cell in tx_cell_list.items()
        }

        if len(pdr_list) > 0:
            # pick up TX cells whose PDRs are less than the higest PDR by
            # MSF_MIN_NUM_TX
            highest_pdr = max(pdr_list.values())
            relocation_cell_list = [
                {
                    'slotOffset'   : slotOffset,
                    'channelOffset': tx_cell_list[slotOffset].channel_offset
                } for slotOffset, pdr in pdr_list.items() if (
                    d.MSF_RELOCATE_PDRTHRES < (highest_pdr - pdr)
                )
            ]
            if len(relocation_cell_list) > 0:
                self._request_relocating_cells(
                    neighbor             = preferred_parent,
                    cell_options         = self.TX_CELL_OPT,
                    num_relocating_cells = len(relocation_cell_list),
                    cell_list            = relocation_cell_list
                )
        else:
            # we don't have any TX cell whose PDR is available; do nothing
            pass

        # schedule next housekeeping
        self.engine.scheduleIn(
            delay         = d.MSF_HOUSEKEEPINGCOLLISION_PERIOD,
            cb            = self._housekeeping_collision,
            uniqueTag     = (self.mote.id, '_housekeeping_collision'),
            intraSlotOrder= d.INTRASLOTORDER_STACKTASKS,
        )

    # cell manipulation helpers
    def _lock_cells(self, cell_list):
        for cell in cell_list:
            self.locked_slots.add(cell['slotOffset'])

    def _unlock_cells(self, cell_list):
        for cell in cell_list:
            self.locked_slots.remove(cell['slotOffset'])

    def _add_cells(self, neighbor, cell_list, cell_options):
        try:
            for cell in cell_list:
                self.mote.tsch.addCell(
                    slotOffset         = cell['slotOffset'],
                    channelOffset      = cell['channelOffset'],
                    neighbor           = neighbor,
                    cellOptions        = cell_options,
                    slotframe_handle   = self.SLOTFRAME_HANDLE
                )
        except Exception:
            # We may fail in adding cells since they could be allocated for
            # another peer. We need to have a locking or reservation mechanism
            # to avoid such a situation.
            raise

    def _delete_cells(self, neighbor, cell_list, cell_options):
        for cell in cell_list:
            if self.mote.tsch.get_cell(
                    slot_offset      = cell['slotOffset'],
                    channel_offset   = cell['channelOffset'],
                    mac_addr         = neighbor,
                    slotframe_handle = self.SLOTFRAME_HANDLE
               ) is None:
                # the cell may have been deleted for some reason
                continue
            self.mote.tsch.deleteCell(
                slotOffset       = cell['slotOffset'],
                channelOffset    = cell['channelOffset'],
                neighbor         = neighbor,
                cellOptions      = cell_options,
                slotframe_handle = self.SLOTFRAME_HANDLE
            )

    def _clear_cells(self, neighbor):
        cells = self.mote.tsch.get_cells(neighbor, self.SLOTFRAME_HANDLE)
        for cell in cells:
            assert neighbor == cell.mac_addr
            if d.CELLOPTION_SHARED in cell.options:
                # we consider this cell as the autonomous one of the
                # neighbor, which must not be deleted by CLEAR. Skip
                # this cell:
                # https://tools.ietf.org/html/draft-ietf-6tisch-msf-01#section-3
                pass
            else:
                self.mote.tsch.deleteCell(
                    slotOffset       = cell.slot_offset,
                    channelOffset    = cell.channel_offset,
                    neighbor         = cell.mac_addr,
                    cellOptions      = cell.options,
                    slotframe_handle = self.SLOTFRAME_HANDLE
                )

    def _relocate_cells(
            self,
            neighbor,
            src_cell_list,
            dst_cell_list,
            cell_options
        ):
        assert len(src_cell_list) == len(dst_cell_list)

        # relocation
        self._add_cells(neighbor, dst_cell_list, cell_options)
        self._delete_cells(neighbor, src_cell_list, cell_options)

    def _create_available_cell_list(self, cell_list_len):
        available_slots = list(
            set(self.mote.tsch.get_available_slots(self.SLOTFRAME_HANDLE)) -
            self.locked_slots
        )

        if len(available_slots) <= cell_list_len:
            # we don't have enough available cells; no cell is selected
            selected_slots = []
        else:
            selected_slots = random.sample(available_slots, cell_list_len)

        cell_list = []
        for slot_offset in selected_slots:
            channel_offset = random.randint(0, self.settings.phy_numChans - 1)
            cell_list.append(
                {
                    'slotOffset'   : slot_offset,
                    'channelOffset': channel_offset
                }
            )
        self._lock_cells(cell_list)
        return cell_list

    def _create_occupied_cell_list(
            self,
            neighbor,
            cell_options,
            cell_list_len
        ):

        occupied_cells = filter(
            lambda cell: cell.options == cell_options,
            self.mote.tsch.get_cells(neighbor, self.SLOTFRAME_HANDLE)
        )

        cell_list = [
            {
                'slotOffset'   : cell.slot_offset,
                'channelOffset': cell.channel_offset
            } for cell in occupied_cells
        ]

        if cell_list_len <= len(occupied_cells):
            cell_list = random.sample(cell_list, cell_list_len)

        return cell_list

    def _are_cells_allocated(
            self,
            peerMac,
            cell_list,
            cell_options
        ):

        # collect allocated cells
        assert cell_options in [self.TX_CELL_OPT, self.RX_CELL_OPT]
        allocated_cells = filter(
            lambda cell: cell.options == cell_options,
            self.mote.tsch.get_cells(peerMac, self.SLOTFRAME_HANDLE)
        )

        # test all the cells in the cell list against the allocated cells
        ret_val = True
        for cell in cell_list:
            slotOffset    = cell['slotOffset']
            channelOffset = cell['channelOffset']
            cell = self.mote.tsch.get_cell(
                slot_offset      = slotOffset,
                channel_offset   = channelOffset,
                mac_addr         = peerMac,
                slotframe_handle = self.SLOTFRAME_HANDLE
            )

            if cell is None:
                ret_val = False
                break

        return ret_val

    # ADD command related stuff
    def _request_adding_cells(
            self,
            neighbor,
            num_txrx_cells = 0,
            num_tx_cells   = 0,
            num_rx_cells   = 0
        ):

        # determine num_cells and cell_options; update num_{txrx,tx,rx}_cells
        if   num_txrx_cells > 0:
            assert num_txrx_cells == 1
            cell_options   = self.TXRX_CELL_OPT
            num_cells      = num_txrx_cells
            num_txrx_cells = 0
        elif num_tx_cells > 0:
            cell_options   = self.TX_CELL_OPT
            if num_tx_cells < self.DEFAULT_CELL_LIST_LEN:
                num_cells    = num_tx_cells
                num_tx_cells = 0
            else:
                num_cells    = self.DEFAULT_CELL_LIST_LEN
                num_tx_cells = num_tx_cells - self.DEFAULT_CELL_LIST_LEN
        elif num_rx_cells > 0:
            cell_options = self.RX_CELL_OPT
            num_cells    = num_rx_cells
            if num_rx_cells < self.DEFAULT_CELL_LIST_LEN:
                num_cells    = num_rx_cells
                num_rx_cells = 0
            else:
                num_cells    = self.DEFAULT_CELL_LIST_LEN
                num_rx_cells = num_rx_cells - self.DEFAULT_CELL_LIST_LEN
        else:
            # nothing to add
            return

        # prepare cell_list
        cell_list = self._create_available_cell_list(self.DEFAULT_CELL_LIST_LEN)

        if len(cell_list) == 0:
            # we don't have available cells right now
            self.log(
                SimEngine.SimLog.LOG_MSF_ERROR_SCHEDULE_FULL,
                {
                    '_mote_id'    : self.mote.id
                }
            )
            return

        # prepare _callback which is passed to SixP.send_request()
        callback = self._create_add_request_callback(
            neighbor,
            num_cells,
            cell_options,
            cell_list,
            num_txrx_cells,
            num_tx_cells,
            num_rx_cells
        )

        # send a request
        self.mote.sixp.send_request(
            dstMac      = neighbor,
            command     = d.SIXP_CMD_ADD,
            cellOptions = cell_options,
            numCells    = num_cells,
            cellList    = cell_list,
            callback    = callback
        )

    def _receive_add_request(self, request):

        # for quick access
        proposed_cells = request['app']['cellList']
        peerMac         = request['mac']['srcMac']
        pkt_flows       = request['app']['pkt_flows']

        print "ASN",self.engine.getAsn(), "~ID", self.mote.id, "<--", peerMac, "Receive request", request

        if self.mote.tx_slot ==-1 and self.mote.id !=0:
            print "Drop Request",self.mote.id, "<--", peerMac
            return
        '''
        #update childs underflow
        found = 0
        for y in self.mote.tsch.under_flows:
            if peerMac == y:
                found = 1
                break
        if found == 0:
            self.mote.tsch.under_flows.append(peerMac)

        print "#^ ID", self.mote.id, "|", self.mote.tsch.flows, "-->", self.mote.tsch.under_flows
        '''

        if self.mote.hops %2 ==0:
            turn_RX=0
        else:
            turn_RX=1
        cell_list=[]

        sub_slot = -1

        temp_flip_flop=self.mote.flip_flop  #:) !!!

        if self.mote.id !=0 : # relay node


            for i in range(0, d.SubFrameSize):
                if self.children[i] == peerMac:
                    sub_slot = i
                    break
            if sub_slot != -1:
                print "~ID", self.mote.id, "->", peerMac, "already schedule"

            print self.mote.flip_flop


            if sub_slot==-1:
                for i in range(0,d.SubFrameSize):
                    if self.children[i]==-1:
                        sub_slot=i
                        self.children[i]=peerMac
                        break

            if sub_slot!=-1:
                for i in range(0, request['app']['numCells']):
                    slot_offset = 1 + (d.SubFrameSize * (2 * i + (turn_RX+ self.mote.flip_flop)%2) + sub_slot)
                    channel_offset = random.randint(0,self.settings.phy_numChans - 1)  # :) select randomly the channel offset
                    cell_list.append(
                        {
                            'slotOffset': slot_offset,
                            'channelOffset': channel_offset
                        }
                    )

            else:
                print "Error Relay",self.mote.id,"childs",self.children

        else:

            for i in range(0, 2*d.SubFrameSize):
                if self.children[i] == peerMac:
                    sub_slot = i
                    break

            if sub_slot != -1:
                print "~ID", self.mote.id, "->", peerMac, "already schedule"
                temp_flip_flop=0
                if sub_slot>=d.SubFrameSize :
                    temp_flip_flop=1

            if sub_slot == -1:
                temp_flip_flop=0
                for i in range(0, 2*d.SubFrameSize):
                    if self.children[i] == -1:
                        sub_slot = i
                        self.children[i] = peerMac
                        break

                if i>=d.SubFrameSize :
                    temp_flip_flop=1
                    print "above 5"

            if sub_slot != -1:
                for i in range(0, request['app']['numCells']):
                    slot_offset = 1 + (d.SubFrameSize * (2 * i + (turn_RX + temp_flip_flop)%2) + sub_slot%d.SubFrameSize) % (self.settings.tsch_slotframeLength-1)
                    channel_offset = random.randint(0,self.settings.phy_numChans - 1)  # :) select randomly the channel offset
                    cell_list.append(
                        {
                            'slotOffset': slot_offset,
                            'channelOffset': channel_offset
                        }
                    )

            else:
                print "Error Sink", self.mote.id, "childs", self.children

        print "CellList", cell_list


        # prepare callback
        if len(cell_list) > 0:
            code = d.SIXP_RC_SUCCESS

            #self._lock_cells(candidate_cells)
            def callback(event, packet):
                #:) Add the cellist cells if parent receives a corresponding ack for upcoming 6P transaction
                if event == d.SIXP_CALLBACK_EVENT_MAC_ACK_RECEPTION:
                    # prepare cell options for this responder
                    if   request['app']['cellOptions'] == self.TXRX_CELL_OPT:
                        cell_options = self.TXRX_CELL_OPT
                    elif request['app']['cellOptions'] == self.TX_CELL_OPT:
                        # invert direction
                        cell_options = self.RX_CELL_OPT
                    elif request['app']['cellOptions'] == self.RX_CELL_OPT:
                        # invert direction
                        cell_options = self.TX_CELL_OPT
                    else:
                        # Unsupported cell options for MSF
                        raise Exception()

                    self._add_cells(
                        neighbor     = peerMac,
                        cell_list    = cell_list,
                        cell_options = cell_options
                )


                print "~ID", self.mote.id, "Schedule", self.mote.tsch.slotframes[1].slots
                #self._unlock_cells(candidate_cells)

                # ------ Add TX, RX flows for sender
                print "+ID", self.mote.id,"flows",pkt_flows

                for fl in pkt_flows:
                    pmac = fl[0]
                    id = fl[1]
                    if self.mote.tsch.search_flows(pmac, id) == -1:  # doesn't exists - assign the appropriate slots to Virtual SlotFrame
                        print "=ID",self.mote.id,self.mote.tsch.flows

                        start_tx = fl[2]
                        hops = fl[3]
                        flow_gen = fl[4]
                        tx_vslot=-1
                        if start_tx == -1 and hops == 0:  # from sender
                            tx_timeslot = cell_list[0]['slotOffset']
                            genSubframe = flow_gen

                            if ((self.mote.hops+1 + temp_flip_flop) % 2 == 0 and genSubframe % 2 == 1) or (
                                    (self.mote.hops+1 + temp_flip_flop) % 2 == 1 and genSubframe % 2 == 0):
                                genSubframe += 1


                            index = (genSubframe + 1) * d.SubFrameSize + tx_timeslot % d.SubFrameSize

                            if tx_timeslot % d.SubFrameSize == 0:
                                index += d.SubFrameSize  # 5

                            if self.mote.id !=0:
                                #self.mote.tsch.flows[pmac] = [id]
                                self.mote.tsch.add_flow(pmac, id)
                                self.mote.tsch.add_flow_rx(index, pmac, hops,id)

                                if index % d.SubFrameSize == 0:
                                    tx_vslot = index + self.mote.tx_slot
                                else:
                                    tx_vslot = index + d.SubFrameSize + self.mote.tx_slot - index % d.SubFrameSize

                                if id != 2 and id!=3 : # Keep_alive

                                    self.mote.tsch.add_flow_tx(tx_vslot, pmac, hops, id)
                                    #forwarding
                                    self.mote.tsch.add_pkt_flow(pmac, id, tx_vslot, hops + 1, flow_gen)


                            elif self.mote.id == 0:

                                self.mote.tsch.add_flow(pmac, id)
                                self.mote.tsch.add_flow_rx(index, pmac, hops,id)

                        else:

                            if start_tx % d.SubFrameSize == 0:
                                tx_vslot = start_tx + self.mote.tx_slot
                            else:
                                tx_vslot = start_tx + d.SubFrameSize + self.mote.tx_slot - start_tx % d.SubFrameSize


                            if start_tx != -1 and self.mote.tx_slot != -1 and self.mote.id != 0:
                                self.mote.tsch.add_flow(pmac, id)
                                self.mote.tsch.add_flow_rx(start_tx, pmac, hops,id)

                                if id != 2 and id!=3:
                                    self.mote.tsch.add_flow_tx(tx_vslot, pmac, hops,id)

                                    # forwarding #
                                    self.mote.tsch.add_pkt_flow(pmac,id,tx_vslot,hops+1,flow_gen)

                            elif self.mote.id == 0:# and start_tx != -1:
                                self.mote.tsch.add_flow(pmac, id)
                                self.mote.tsch.add_flow_rx(start_tx, pmac, hops,id)

                        print "^ID", self.mote.id, "Vindex", self.mote.tsch.asn2vindex(self.engine.getAsn()), "Gen", pmac, "Start TX", start_tx, "Hops", hops, "TX slot", self.mote.tx_slot, "VSLOT", tx_vslot



                # ------
        else:
            code      = d.SIXP_RC_ERR
            cell_list = None
            callback  = None

        if self.mote.id !=0 :
            temp_flip_flop=self.mote.flip_flop

        print "!ID",self.mote.id,"Flip Flop",temp_flip_flop

        # send a response
        self.mote.sixp.send_response(
            dstMac      = peerMac,
            return_code = code,
            cellList    = cell_list,
            callback    = callback,
            flip_flop   = temp_flip_flop #:)
        )

    def _create_add_request_callback(
            self,
            neighbor,
            num_cells,
            cell_options,
            cell_list,
            num_txrx_cells,
            num_tx_cells,
            num_rx_cells
        ):
        def callback(event, packet):
            if event == d.SIXP_CALLBACK_EVENT_PACKET_RECEPTION:
                print "ASN", self.engine.getAsn(), "~ID", self.mote.id, #:)

                assert packet['app']['msgType'] == d.SIXP_MSG_TYPE_RESPONSE
                if packet['app']['code'] == d.SIXP_RC_SUCCESS:
                    print "Success"
                    self.mote.lock_schedule = 1 #:)
                    # add cells on success of the transaction
                    self._add_cells(
                        neighbor     = neighbor,
                        cell_list    = packet['app']['cellList'],
                        cell_options = cell_options
                    )
                    #:)------ %%% here

                    self.mote.flip_flop = packet['app']['flip_flop']
                    tx_timeslot = packet['app']['cellList'][0]['slotOffset']

                    for fl in self.mote.tsch.pkt_flow:
                        pmac = fl[0]
                        id = fl[1]

                        if self.mote.tsch.search_flows(pmac,id) == -1 and pmac==self.mote.get_mac_addr():  # doesn't exists - assign the appropriate slots to Virtual SlotFrame
                            start_tx = fl[2]
                            hops = fl[3]
                            flow_gen = fl[4]
                            tx_vslot = -1

                            genSubframe = flow_gen

                            if ((self.mote.hops+self.mote.flip_flop) % 2 == 0 and genSubframe % 2 == 1) or ((self.mote.hops+self.mote.flip_flop) % 2 == 1 and genSubframe % 2 == 0):
                                    genSubframe += 1

                            index = (genSubframe + 1) * d.SubFrameSize + tx_timeslot % d.SubFrameSize

                            if tx_timeslot % d.SubFrameSize == 0:
                                index += d.SubFrameSize  # 5

                            print "#ID", self.mote.id, "Timeslot", tx_timeslot, "Index", index, "genSub", genSubframe
                            self.mote.tsch.add_flow_gen(index,id) # TODO add flows
                            self.mote.tx_slot = tx_timeslot % (d.SubFrameSize)  #:) change SOS
                            if self.mote.tx_slot == 0:
                                print "CCC", self.mote.id
                                self.mote.tx_slot = d.SubFrameSize  # 5




                    print ">ID", self.mote.id, "Flip Flop", self.mote.flip_flop
                    #:)-----
                    # The received CellList could be smaller than the requested
                    # NumCells; adjust num_{txrx,tx,rx}_cells
                    _num_txrx_cells = num_txrx_cells
                    _num_tx_cells   = num_tx_cells
                    _num_rx_cells   = num_rx_cells
                    remaining_cells = num_cells - len(packet['app']['cellList'])
                    if remaining_cells > 0:
                        if   cell_options == self.TXRX_CELL_OPT:
                            # One (TX=1,RX=1,SHARED=1) cell is requested;
                            # RC_SUCCESS shouldn't be returned with an empty cell
                            # list
                            raise Exception()
                        elif cell_options == self.TX_CELL_OPT:
                            _num_tx_cells -= remaining_cells
                        elif cell_options == self.RX_CELL_OPT:
                            _num_rx_cells -= remaining_cells
                        else:
                            # never comes here
                            raise Exception()

                    # start another transaction
                    self._request_adding_cells(
                        neighbor       = neighbor,
                        num_txrx_cells = _num_txrx_cells,
                        num_tx_cells   = _num_tx_cells,
                        num_rx_cells   = _num_rx_cells
                    )

                    #:)
                    print "~ID", self.mote.id, "Schedule", self.mote.tsch.slotframes[1].slots
                else:
                    # TODO: request doesn't succeed; how should we do?
                    print "Failed - Change Father",self.mote.id,"->",neighbor #,neighbor['mac_addr'] #:)
                    self.mote.black_parent.append(neighbor)
                    self.mote.rpl.changePreferredParent()
                    '''
                    print "Resend 6P add Request", self.mote.id
                    self._request_adding_cells(
                        neighbor=neighbor,
                        num_txrx_cells=self.INITIAL_NUM_TXRX_CELLS,
                        num_tx_cells=10,
                        num_rx_cells=0
                    )
                    '''
                    pass

            elif event == d.SIXP_CALLBACK_EVENT_TIMEOUT:
                # If this transaction is for the very first cell allocation to
                # the preferred parent, let's retry it. Otherwise, let
                # adaptation to traffic trigger another transaction if
                # necessary.
                if cell_options == self.TXRX_CELL_OPT:
                    self._request_adding_cells(
                        neighbor       = neighbor,
                        num_txrx_cells = 1
                    )
                else:
                    # do nothing as mentioned above
                    pass
            else:
                # ignore other events
                print "Ignoring"
                pass

            # unlock the slots used in this transaction
            self._unlock_cells(cell_list)

        return callback

    # DELETE command related stuff
    def _request_deleting_cells(
            self,
            neighbor,
            num_cells,
            cell_options
        ):

        # prepare cell_list to send
        cell_list = self._create_occupied_cell_list(
            neighbor      = neighbor,
            cell_options  = cell_options,
            cell_list_len = self.DEFAULT_CELL_LIST_LEN
        )
        assert len(cell_list) > 0

        # prepare callback
        callback = self._create_delete_request_callback(
            neighbor,
            cell_options
        )

        # send a DELETE request
        self.mote.sixp.send_request(
            dstMac      = neighbor,
            command     = d.SIXP_CMD_DELETE,
            cellOptions = cell_options,
            numCells    = num_cells,
            cellList    = cell_list,
            callback    = callback
        )

    def _receive_delete_request(self, request):
        # for quick access
        num_cells           = request['app']['numCells']
        cell_options        = request['app']['cellOptions']
        candidate_cell_list = request['app']['cellList']
        peerMac             = request['mac']['srcMac']

        # confirm all the cells in the cell list are allocated for the peer
        # with the specified cell options
        #
        # invert the direction in cell_options
        assert cell_options in [self.TX_CELL_OPT, self.RX_CELL_OPT]
        if   cell_options == self.TX_CELL_OPT:
            our_cell_options = self.RX_CELL_OPT
        elif cell_options == self.RX_CELL_OPT:
            our_cell_options   = self.TX_CELL_OPT

        if (
                (
                    self._are_cells_allocated(
                        peerMac      = peerMac,
                        cell_list    = candidate_cell_list,
                        cell_options = our_cell_options
                    ) is True
                )
                and
                (num_cells <= len(candidate_cell_list))
            ):
            code = d.SIXP_RC_SUCCESS
            cell_list = random.sample(candidate_cell_list, num_cells)

            def callback(event, packet):
                if event == d.SIXP_CALLBACK_EVENT_MAC_ACK_RECEPTION:
                    self._delete_cells(
                        neighbor     = peerMac,
                        cell_list    = cell_list,
                        cell_options = our_cell_options
                )
        else:
            code      = d.SIXP_RC_ERR
            cell_list = None
            callback  = None

        # send the response
        self.mote.sixp.send_response(
            dstMac      = peerMac,
            return_code = code,
            cellList    = cell_list,
            callback    = callback
        )

    def _create_delete_request_callback(
            self,
            neighbor,
            cell_options
        ):
        def callback(event, packet):
            if (
                    (event == d.SIXP_CALLBACK_EVENT_PACKET_RECEPTION)
                    and
                    (packet['app']['msgType'] == d.SIXP_MSG_TYPE_RESPONSE)
                ):
                if packet['app']['code'] == d.SIXP_RC_SUCCESS:
                    self._delete_cells(
                        neighbor     = neighbor,
                        cell_list    = packet['app']['cellList'],
                        cell_options = cell_options
                    )
                else:
                    # TODO: request doesn't succeed; how should we do?
                    pass
            elif event == d.SIXP_CALLBACK_EVENT_TIMEOUT:
                # TODO: request doesn't succeed; how should we do?
                pass
            else:
                # ignore other events
                pass

        return callback

    # RELOCATE command related stuff
    def _request_relocating_cells(
            self,
            neighbor,
            cell_options,
            num_relocating_cells,
            cell_list
        ):

        # determine num_cells and relocation_cell_list;
        # update num_relocating_cells and cell_list
        if self.DEFAULT_CELL_LIST_LEN < num_relocating_cells:
            num_cells             = self.DEFAULT_CELL_LIST_LEN
            relocation_cell_list  = cell_list[:self.DEFAULT_CELL_LIST_LEN]
            num_relocating_cells -= self.DEFAULT_CELL_LIST_LEN
            cell_list             = cell_list[self.DEFAULT_CELL_LIST_LEN:]
        else:
            num_cells             = num_relocating_cells
            relocation_cell_list  = cell_list
            num_relocating_cells  = 0
            cell_list             = []

        # we don't have any cell to relocate; done
        if len(relocation_cell_list) == 0:
            return

        # prepare candidate_cell_list
        candidate_cell_list = self._create_available_cell_list(
            self.DEFAULT_CELL_LIST_LEN
        )

        if len(candidate_cell_list) == 0:
            # no available cell to move the cells to
            self.log(
                SimEngine.SimLog.LOG_MSF_ERROR_SCHEDULE_FULL,
                {
                    '_mote_id'    : self.mote.id
                }
            )
            return

        # prepare callback
        def callback(event, packet):
            if event == d.SIXP_CALLBACK_EVENT_PACKET_RECEPTION:
                assert packet['app']['msgType'] == d.SIXP_MSG_TYPE_RESPONSE
                if packet['app']['code'] == d.SIXP_RC_SUCCESS:
                    # perform relocations
                    num_relocations = len(packet['app']['cellList'])
                    self._relocate_cells(
                        neighbor      = neighbor,
                        src_cell_list = relocation_cell_list[:num_cells],
                        dst_cell_list = packet['app']['cellList'],
                        cell_options  = cell_options
                    )

                    # adjust num_relocating_cells and cell_list
                    _num_relocating_cells = (
                        num_relocating_cells + num_cells - num_relocations
                    )
                    _cell_list = (
                        cell_list + relocation_cell_list[num_relocations:]
                    )

                    # start another transaction
                    self._request_relocating_cells(
                        neighbor             = neighbor,
                        cell_options         = cell_options,
                        num_relocating_cells = _num_relocating_cells,
                        cell_list            = _cell_list
                    )
            # unlock the slots used in this transaction
            self._unlock_cells(candidate_cell_list)

        # send a request
        self.mote.sixp.send_request(
            dstMac             = neighbor,
            command            = d.SIXP_CMD_RELOCATE,
            cellOptions        = cell_options,
            numCells           = num_cells,
            relocationCellList = relocation_cell_list,
            candidateCellList  = candidate_cell_list,
            callback           = callback
        )

    def _receive_relocate_request(self, request):
        return  #:) disable
        # for quick access
        num_cells        = request['app']['numCells']
        cell_options     = request['app']['cellOptions']
        relocating_cells = request['app']['relocationCellList']
        candidate_cells  = request['app']['candidateCellList']
        peerMac          = request['mac']['srcMac']

        # confirm all the cells in the cell list are allocated for the peer
        # with the specified cell options
        #
        # invert the direction in cell_options
        assert cell_options in [self.TX_CELL_OPT, self.RX_CELL_OPT]
        if   cell_options == self.TX_CELL_OPT:
            our_cell_options = self.RX_CELL_OPT
        elif cell_options == self.RX_CELL_OPT:
            our_cell_options   = self.TX_CELL_OPT

        if (
                (
                    self._are_cells_allocated(
                        peerMac      = peerMac,
                        cell_list    = relocating_cells,
                        cell_options = our_cell_options
                    ) is True
                )
                and
                (num_cells <= len(candidate_cells))
            ):
            # find available cells in the received candidate cell list
            slots_in_slotframe = set(range(0, self.settings.tsch_slotframeLength))
            slots_in_use       = set(
                self.mote.tsch.get_busy_slots(self.SLOTFRAME_HANDLE)
            )
            candidate_slots    = set(
                map(lambda c: c['slotOffset'], candidate_cells)
            )
            available_slots    = list(
                candidate_slots.intersection(
                    set(
                        self.mote.tsch.get_available_slots(self.SLOTFRAME_HANDLE)
                    )
                )
            )

            # FIXME: handle the case when available_slots is empty

            # prepare response
            code           = d.SIXP_RC_SUCCESS
            cell_list      = []
            selected_slots = random.sample(available_slots, num_cells)
            for cell in candidate_cells:
                if cell['slotOffset'] in selected_slots:
                    cell_list.append(cell)

            self._lock_cells(cell_list)
            # prepare callback
            def callback(event, packet):
                if event == d.SIXP_CALLBACK_EVENT_MAC_ACK_RECEPTION:
                    num_relocations = len(cell_list)
                    self._relocate_cells(
                        neighbor      = peerMac,
                        src_cell_list = relocating_cells[:num_relocations],
                        dst_cell_list = cell_list,
                        cell_options  = our_cell_options
                    )
                self._unlock_cells(cell_list)

        else:
            code      = d.SIXP_RC_ERR
            cell_list = None
            callback  = None

        # send a response
        self.mote.sixp.send_response(
            dstMac      = peerMac,
            return_code = code,
            cellList    = cell_list,
            callback    = callback
        )


    # CLEAR command related stuff
    def _receive_clear_request(self, request):
        return  #:) disable
        peerMac = request['mac']['srcMac']

        def callback(event, packet):
            # remove all the cells no matter what happens
            self._clear_cells(peerMac)

        # create CLEAR response
        self.mote.sixp.send_response(
            dstMac      = peerMac,
            return_code = d.SIXP_RC_SUCCESS,
            callback    = callback
        )

