import os
from os import walk


RootPath = 'C:\Users\Vassilios\Desktop\data'

#RootPath = 'C:\Users\Vassilios\Desktop\\a'
count = 0
for (dirpath, dirnames, filenames) in walk(RootPath):


    for fl in filenames:
        fichstat = open( dirpath+"\\"+fl, "r")
        # trace file processing
        #print ".",
        found=False

        for line in fichstat:
            if line.find("Error Relay") != -1:
                #print "\n", fl,line

                found=True
        if found==True:
            print fl
            count +=1
        fichstat.close()

    print "Total Files",count