

CBR=3# in sec
SlotFrameSize=101
BlockSize=5
StartASN=8
Block_Timeslot=2
BLOCK_Turn=1

Period=CBR*100

startup_delay=[]

def NeXT_ASN(curr_ASN):
    tempASN=curr_ASN+Period
    curr_slotFrame= tempASN/SlotFrameSize
    rem=tempASN% SlotFrameSize

    if rem !=0 :
        block_id = (rem-1)/BlockSize

    else:
        block_id=0

    #print "@!",block_id
    if block_id %2 <> BLOCK_Turn :
        block_id+=1

    add_share=0
    if (block_id)*BlockSize >=SlotFrameSize-1:
        add_share=1


    next_ASN = curr_slotFrame * SlotFrameSize +(block_id)*BlockSize+ Block_Timeslot+add_share+1

    if next_ASN <tempASN :
        block_id+=2
        add_share = 0
        if (block_id) * BlockSize >= SlotFrameSize - 1:
            add_share = 1

        next_ASN = curr_slotFrame * SlotFrameSize + (block_id) * BlockSize + Block_Timeslot + add_share + 1

    #print tempASN,curr_slotFrame,rem,block_id
    print "ASN",curr_ASN, "NxtASN",next_ASN, "Timeslot",next_ASN % SlotFrameSize,next_ASN-tempASN
    startup_delay.append(next_ASN-tempASN)


    return next_ASN


for i in range(2,1000000,100*CBR):
    StartASN=NeXT_ASN(i)

avg=sum(startup_delay)/float(len(startup_delay))
print "Avg",avg
