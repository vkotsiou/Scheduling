import os

for i in range(0, 20):
    cmd = "python runSim.py" + " > " + "data_"  + "_" + str(i)
    os.system(cmd)
