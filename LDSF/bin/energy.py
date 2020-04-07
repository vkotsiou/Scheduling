active=[]
start_asn=[]
start_exp=[]

end=101*3600
prev_act=[]
for i in range(0,40):
    t=[]
    active.append(t)
    start_asn.append(-1)
    prev_act.append(-1)
    start_exp.append(-1)

print active

fd = open(".\\log1.txt", "r")
for line in fd:
    tmp = line.split()
    id=int(tmp[1])
    asn=int(tmp[3])
    actv=int(tmp[5])


    print tmp
    print prev_act[id],actv
    if start_exp[id]==-1 :
        start_exp[id]=asn

    if prev_act[id]==0 and actv ==1:
      start_asn[id]=asn
    elif prev_act[id]==1 and actv==0:
      duration=asn-start_asn[id]
      print id, duration,active[id]
      active[id].append(duration)

    prev_act[id]=actv


fd.close

for i in range(0,40):
    if prev_act[i]==1:
        print i ,end - start_asn[i],start_asn[i],end,start_exp[i]
        active[i].append(end - start_asn[i])

for i in range(0,40):
    closed=sum(active[i])
    duration =end - start_exp[i]


    print i,closed,duration,"Closed",closed/float(duration), "Open", 1.0-closed/float(duration)