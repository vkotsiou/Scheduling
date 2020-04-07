import os

for i in range(0, 1):
    cmd = "python runSim.py" + " > " +".\data\\"+ "dtC"  + "_" + str(i)
    os.system(cmd)
