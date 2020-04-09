

from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
import numpy as np

path = '../plots/'
fz=9

fig = plt.figure()
ax = fig.gca(projection='3d')


# Make data.

X = [1,2,3,4,5,6,7,8,9,10]
Y = [101,501,1001,2001]

X, Y = np.meshgrid(X, Y)



#Z = np.abs(X*Y/2.0)  #MSF
Z = np.abs(Y)
#Z = np.abs(5*X)

print Z

# Plot the surface.
surf = ax.plot_surface(X, Y, Z, cmap=cm.coolwarm,
                       linewidth=0, antialiased=False)

xlabel = []
x1 = []
for i in range(1, 10 + 1):
    xlabel.append(i)
    x1.append(i)

plt.xticks(x1, xlabel, fontsize=fz)

plt.xlabel('Number of Hops' ,fontsize=fz)  #:)

ylabel = [101,501,1001,2001]
y1 = [101,501,1001,2001]
'''
for i in range(1, 10 + 1):
    xlabel.append(i)
    x1.append(i)
'''

plt.yticks(y1, ylabel, fontsize=fz)
plt.ylabel('SlotFrame size (slots)', fontsize=fz)



# Customize the z axis.

for t in ax.zaxis.get_major_ticks():
    print t
    t.label.set_fontsize(fz)

ax.set_zlabel('delay', fontsize=fz)

#plt.savefig(path + 'plot' + '.png', format='png')
plt.savefig('.\msf.png', format='png', dpi=900)

# Add a color bar which maps values to colors.
#fig.colorbar(surf, shrink=0.5, aspect=5)

plt.show()
