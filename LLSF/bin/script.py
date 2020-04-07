import os
# Number 8 - number of nodes, 18 CBR
file='.\config.json'
def change_parameter(par_no,value):
    f=open(file,"r")
    file_lines=[]
    i=0
    for line in f:
        #print i,":",line
        if par_no==i:
            l=line.split(":")
            if par_no==8:
                new_line=l[0]+":"+"["+str(value)+"]"+"\n"
            elif par_no==18:
                new_line=l[0]+":"+str(value)+","+"\n"

            file_lines.append(new_line)
        else:
            file_lines.append(line)

        i+=1
    f.close()

    f = open(file, "w")
    for line in file_lines:
        f.write(line)
    f.close()
#change_parameter(8,90)
#change_parameter(18,10)
app_period=[80,100,120]#1,2,3,5,10,
app_period= [20,60,40,80,100,120]
nodes=[80,100]

for period in app_period:
    change_parameter(18,period)
    for i in range(0,10):
        print "Packet Rate",period,"Run",i
        cmd="python runSim.py"+" > "+".\dat_"+str(period)+"_"+str(i)
        os.system(cmd)
'''
for nd in nodes:
    change_parameter(8,nd)
    for i in range(0,20):
        cmd="python runSim.py"+" > "+".\dataNd_"+str(nd)+"_"+str(i)
        os.system(cmd)
'''
