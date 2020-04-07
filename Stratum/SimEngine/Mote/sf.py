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


class SchedulingFunctionMSF(SchedulingFunctionBase):

    SLOTFRAME_HANDLE = 1
    INITIAL_NUM_TXRX_CELLS = 0
    DEFAULT_CELL_LIST_LEN = 5
    TXRX_CELL_OPT = [d.CELLOPTION_TX, d.CELLOPTION_RX, d.CELLOPTION_SHARED]
    TX_CELL_OPT   = [d.CELLOPTION_TX]
    RX_CELL_OPT   = [d.CELLOPTION_RX]

    def __init__(self, mote):
        # initialize parent class
        super(SchedulingFunctionMSF, self).__init__(mote)

        # (additional) local variables
        self.num_cells_elapsed = 0       # number of dedicated cells passed
        self.num_cells_used    = 0       # number of dedicated cells used
        self.cell_utilization  = 0
        self.locked_slots      = set([]) # slots in on-going ADD transactions

    # ======================= public ==========================================

    # === admin

    def start(self):
        # enable the pending bit feature
        self.mote.tsch.enable_pending_bit()

        # install SlotFrame 1 which has the same length as SlotFrame 0
        slotframe_0 = self.mote.tsch.get_slotframe(0)
        self.mote.tsch.add_slotframe(
            slotframe_handle = self.SLOTFRAME_HANDLE,
            length           = slotframe_0.length
        )

        # install a Non-SHARED autonomous cell
        self._allocate_non_shared_autonomous_cell()

        # install autonomous TX cells for neighbors
        for mac_addr in self.mote.sixlowpan.on_link_neighbor_list:
            self._allocate_shared_autonomous_cell(mac_addr)

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
        if self.mote.tsch.get_slotframe(self.SLOTFRAME_HANDLE) is None:
            # it's not ready to add cells
            pass
        else:
            self._allocate_shared_autonomous_cell(neighbor_mac_addr)

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

            # adapt number of cells if necessary
            if d.MSF_MAX_NUMCELLS <= self.num_cells_elapsed:
                self._adapt_to_traffic(preferred_parent)
                self._reset_cell_counters()

    def indication_parent_change(self, old_parent, new_parent):
        assert old_parent != new_parent

        # allocate the same number of cells to the new parent as it has for the
        # old parent; note that there could be three types of cells:
        # (TX=1,RX=1,SHARED=1), (TX=1), and (RX=1)
        if old_parent is None:
            num_tx_cells = 1
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

        # find available cells in the received CellList
        slots_in_cell_list = set(
            map(lambda c: c['slotOffset'], proposed_cells)
        )
        available_slots  = list(
            slots_in_cell_list.intersection(
                set(self.mote.tsch.get_available_slots(self.SLOTFRAME_HANDLE)) -
                self.locked_slots
            )
        )

        # prepare cell_list
        candidate_cells = [
            c for c in proposed_cells if c['slotOffset'] in available_slots
        ]
        if len(candidate_cells) < request['app']['numCells']:
            cell_list = candidate_cells
        else:
            cell_list = random.sample(
                candidate_cells,
                request['app']['numCells']
            )

        # prepare callback
        if len(available_slots) > 0:
            code = d.SIXP_RC_SUCCESS

            self._lock_cells(candidate_cells)
            def callback(event, packet):
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
                self._unlock_cells(candidate_cells)
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
                assert packet['app']['msgType'] == d.SIXP_MSG_TYPE_RESPONSE
                if packet['app']['code'] == d.SIXP_RC_SUCCESS:
                    # add cells on success of the transaction
                    self._add_cells(
                        neighbor     = neighbor,
                        cell_list    = packet['app']['cellList'],
                        cell_options = cell_options
                    )

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
                else:
                    # TODO: request doesn't succeed; how should we do?
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

    # autonomous cell
    def _get_autonomous_cell(self, mac_addr):
        slotframe = self.mote.tsch.get_slotframe(self.SLOTFRAME_HANDLE)
        hash_value = self._sax(mac_addr)

        slot_offset = int(1 + (hash_value % (slotframe.length - 1)))
        channel_offset = int(hash_value % 16)

        return (slot_offset, channel_offset)

    def _allocate_non_shared_autonomous_cell(self):
        mac_addr = self.mote.get_mac_addr()
        slot_offset, channel_offset = self._get_autonomous_cell(mac_addr)
        self.mote.tsch.addCell(
            slotOffset       = slot_offset,
            channelOffset    = channel_offset,
            neighbor         = None,
            cellOptions      = [
                d.CELLOPTION_TX,
                d.CELLOPTION_RX
            ],
            slotframe_handle = self.SLOTFRAME_HANDLE
        )

    def _allocate_shared_autonomous_cell(self, mac_addr):
        slot_offset, channel_offset = self._get_autonomous_cell(mac_addr)
        self.mote.tsch.addCell(
            slotOffset       = slot_offset,
            channelOffset    = channel_offset,
            neighbor         = mac_addr,
            cellOptions      = [
                d.CELLOPTION_TX,
                d.CELLOPTION_RX,
                d.CELLOPTION_SHARED
            ],
            slotframe_handle = self.SLOTFRAME_HANDLE
        )

    # SAX
    def _sax(self, mac_addr):
        # XXX: a concrete definition of this hash function is needed to be
        # provided by the draft

        LEFT_SHIFT_NUM = 5
        RIGHT_SHIFT_NUM = 2

        # assuming v (seed) is 0
        hash_value = 0
        for word in netaddr.EUI(mac_addr).words:
            for byte in divmod(word, 0x100):
                left_shifted = (hash_value << LEFT_SHIFT_NUM)
                right_shifted = (hash_value >> RIGHT_SHIFT_NUM)
                hash_value ^= left_shifted + right_shifted + byte

        # assuming T (table size) is 16-bit
        return hash_value & 0xFFFF

class SchedulingFunctionStratum(SchedulingFunctionBase):

    SLOTFRAME_HANDLE = 1
    INITIAL_NUM_TXRX_CELLS = 0
    DEFAULT_CELL_LIST_LEN = 5
    TXRX_CELL_OPT = [d.CELLOPTION_TX, d.CELLOPTION_RX, d.CELLOPTION_SHARED]
    TX_CELL_OPT   = [d.CELLOPTION_TX]
    RX_CELL_OPT   = [d.CELLOPTION_RX]

    def __init__(self, mote):
        # initialize parent class
        super(SchedulingFunctionStratum, self).__init__(mote)

        # (additional) local variables
        self.num_cells_elapsed = 0       # number of dedicated cells passed
        self.num_cells_used    = 0       # number of dedicated cells used
        self.cell_utilization  = 0
        self.locked_slots      = set([]) # slots in on-going ADD transactions

        #Stratum Variables
        self.Cmin = -1  #:)
        self.Cmax = -1

        self.last_asn=-1
        self.TimeoutSFloc_tx=self.settings.tsch_slotframeLength*self.settings.app_pkPeriod # timeout in timeslots
        print "Scheduling Function Stratum "
    # ======================= public ==========================================

    # === admin
    # Statum Functions #:)
    #-----------------------
    def limits1(self):
        min = 1
        max = self.B0() + 1

        for j in range(1, self.mote.hops + 1):
            min = max
            max = max + self.size(j)

        return min, max

    def limits(self):
        max = 101
        min = max - self.B0()

        for j in range(1, self.mote.hops + 1):
            max = min
            min = max - self.size(j)

        return min, max

    def B0(self):
        sum1 = 0
        for i in range(0, self.mote.R):
            sum2 = 0
            for j in range(1, i + 1):
                sum2 += j ** 2 - (j - 1) ** 2
            # print "@",sum2
            sum1 += (1.0 - 1.0 / float((self.mote.R ** 2)) * sum2)
            # print "$",sum1
        return int((self.settings.tsch_slotframeLength - 1) * 1.0 / float(sum1))

    def size(self, hops):
        sum = 0
        for i in range(1, hops + 1):
            sum += i ** 2 - (i - 1) ** 2
        print "#", sum, int((self.B0()) * (1.0 - 1.0 / float(self.mote.R ** 2) * sum))
        return int((self.B0()) * (1.0 - 1.0 / float(self.mote.R ** 2) * sum))

    # -----------------------


    def start(self):
        # enable the pending bit feature
        #self.mote.tsch.enable_pending_bit()

        # install SlotFrame 1 which has the same length as SlotFrame 0
        slotframe_0 = self.mote.tsch.get_slotframe(0)
        self.mote.tsch.add_slotframe(
            slotframe_handle = self.SLOTFRAME_HANDLE,
            length           = slotframe_0.length
        )

        #:) disable autonomous cells
        # install a Non-SHARED autonomous cell
        #self._allocate_non_shared_autonomous_cell()

        # install autonomous TX cells for neighbors
        #for mac_addr in self.mote.sixlowpan.on_link_neighbor_list:
        #    self._allocate_shared_autonomous_cell(mac_addr)

        if self.mote.dagRoot:
            # do nothing
            pass
        else:
            pass
            #self._housekeeping_collision() #:) commented

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
        '''
        if self.mote.tsch.get_slotframe(self.SLOTFRAME_HANDLE) is None:
            # it's not ready to add cells
            pass
        else:
            self._allocate_shared_autonomous_cell(neighbor_mac_addr)
        '''

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
            # print "ID", self.mote.id, "ASN", self.engine.getAsn(), "Cell Usage", cell.slot_offset, cell.num_tx
            # adapt number of cells if necessary
            if d.MSF_MAX_NUMCELLS <= self.num_cells_elapsed:
                pass                                                #:) implement SFloc
                #self._adapt_to_traffic(preferred_parent)
                #self._reset_cell_counters()

    def indication_parent_change(self, old_parent, new_parent):
        assert old_parent != new_parent

        # allocate the same number of cells to the new parent as it has for the
        # old parent; note that there could be three types of cells:
        # (TX=1,RX=1,SHARED=1), (TX=1), and (RX=1)
        if old_parent is None:
            num_tx_cells = 1
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
#:) --------
    def get_tx_PDR(self):
        parent=self.mote.rpl.getPreferredParent()

        pdr_cell=[]
        for slt in self.mote.tsch.slotframes[1].slots:
            for cell in slt:
                if cell.mac_addr == parent and cell.options[0]=='TX':
                    if cell.num_tx!=0:
                        pdr_cell.append(float(cell.num_tx_ack)/float(cell.num_tx))
                    else:
                        #print "Error"
                        pdr_cell.append(1.0)

        return pdr_cell
    def get_data_pkts_num(self):

        cnt=0;
        #print self.mote.tsch.txQueue
        for pkt in self.mote.tsch.txQueue:
            if pkt['type']=='DATA':
                cnt+=1

        return cnt

    def get_inactive_cells(self):
        parent=self.mote.rpl.getPreferredParent()

        inactive_cells=[]
        for slt in self.mote.tsch.slotframes[1].slots:
            for cell in slt:
                if cell.mac_addr == parent and cell.options[0]=='TX':
                    print cell.rcv_ack
                    if cell.rcv_ack==0:
                        cell.reset_rcv_ack()
                        inactive_cells.append({
                                    'slotOffset'   : cell.slot_offset,
                                    'channelOffset': cell.channel_offset
                         })

        return inactive_cells



    def SFloc(self):


        asn= self.engine.getAsn()
        if sum(self.get_tx_PDR()) < self.get_data_pkts_num():
            print "<ID",self.mote.id,"Sum",sum(self.get_tx_PDR()),self.get_tx_PDR() ,"Len",len(self.get_tx_PDR()),"Queue Number",self.get_data_pkts_num()
            extra= int(self.get_data_pkts_num()- sum(self.get_tx_PDR()))
            if int(self.get_data_pkts_num()- sum(self.get_tx_PDR())) <self.get_data_pkts_num()- sum(self.get_tx_PDR()):
                extra+=1

            print "ADD",extra #:)
            self._request_adding_cells(
                neighbor=self.mote.rpl.getPreferredParent(),
                num_tx_cells=int(extra)
            )
		#else #:)
        if self.last_asn==-1:
            self.last_asn=asn

        if self.last_asn + self.TimeoutSFloc_tx >= asn:
            self.last_asn=asn
            cell_list=self.get_inactive_cells()

            if len(cell_list)>0 and  len( self.get_tx_PDR()) -len(cell_list)>0:
                print "<ID", self.mote.id, "Sum", sum(self.get_tx_PDR()), self.get_tx_PDR(), "Len", len( self.get_tx_PDR()), "Queue Number", self.get_data_pkts_num()
                print "Delete",cell_list

                # send a DELETE request
                # prepare callback
                callback = self._create_delete_request_callback(
                            self.mote.rpl.getPreferredParent(),
                            self.TX_CELL_OPT
                )

                self.mote.sixp.send_request(
                    dstMac      = self.mote.rpl.getPreferredParent(),
                    command     = d.SIXP_CMD_DELETE,
                    cellOptions = self.TX_CELL_OPT,
                    numCells    = len(cell_list),
                    cellList    = cell_list,
                    callback    = callback
                )
        #print"\n"
#:) -------
    def _adapt_to_traffic(self, neighbor):
        """
        Check the cells counters and trigger 6P commands if cells need to be
        added or removed.

        :param int neighbor:
        :return:
        """
        cell_utilization = self.num_cells_used / float(self.num_cells_elapsed)
        # print "?ID",self.mote.id,"Utilization",cell_utilization
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
            print "ADD" #:)
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
            print "Delete" #:)
            if len(tx_cells) >2 :  #:) >0 default disable
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
        print "Request !", request
        proposed_cells = request['app']['cellList']
        peerMac         = request['mac']['srcMac']

        if self.mote.lock_schedule == 0 and self.mote.id != 0:
            print "Drop Request", self.mote.id, "<--", peerMac
            return

        print "@",self.mote.tsch.slotframes[self.SLOTFRAME_HANDLE].get_cells_by_mac_addr(peerMac)


        # find available cells in the received CellList
        slots_in_cell_list = set(
            map(lambda c: c['slotOffset'], proposed_cells)
        )
        available_slots  = list(
            #slots_in_cell_list.intersection(
                set(self.mote.tsch.get_available_slots(self.SLOTFRAME_HANDLE))
            #    - self.locked_slots
            #)
        )

        #:)
        proposed_cells = []
        slots = []
        print self.Cmin
        print self.Cmax
        for i in range(self.Cmin, self.Cmax):
            proposed_cells.append(i)

        # prepare cell_list
        candidate_cells = [
            c for c in proposed_cells if c in available_slots
        ]
        if len(candidate_cells) < request['app']['numCells']:
            slots = candidate_cells
        else:
            slots = random.sample(
                candidate_cells,
                request['app']['numCells']
            )

        cell_list = []
        for i in range(0, len(slots)):
            slot_offset = slots[i]
            channel_offset = random.randint(0, self.settings.phy_numChans - 1)  # :) select randomly the channel offset
            cell_list.append(
                {
                    'slotOffset': slot_offset,
                    'channelOffset': channel_offset
                }
            )

        print "`ID", self.mote.id
        print "Proposed", proposed_cells
        print "Available", available_slots
        print "Slots", slots
        print "Cellist", cell_list


        # prepare callback
        if len(available_slots) > 0:
            code = d.SIXP_RC_SUCCESS

            #self._lock_cells(cell_list)
            def callback(event, packet):
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
                print "ID", self.mote.id, "Schedule", self.mote.tsch.slotframes[1].slots #:)
            #self._unlock_cells(cell_list)
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
                assert packet['app']['msgType'] == d.SIXP_MSG_TYPE_RESPONSE
                if packet['app']['code'] == d.SIXP_RC_SUCCESS:
                    self.mote.lock_schedule = 1  #:)
                    print "@ID", self.mote.id, self.mote.lock_schedule
                    # add cells on success of the transaction
                    self._add_cells(
                        neighbor     = neighbor,
                        cell_list    = packet['app']['cellList'],
                        cell_options = cell_options
                    )

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
                else:
                    # TODO: request doesn't succeed; how should we do?
                    pass
                print "ID", self.mote.id, "RX Schedule", self.mote.tsch.slotframes[1].slots  #:)
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
                pass

            # unlock the slots used in this transaction
            #self._unlock_cells(cell_list)

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

