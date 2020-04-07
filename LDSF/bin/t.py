import seaborn as sns; sns.set()
import matplotlib.pyplot as plt
import pandas as pd
#dat = pd.read_csv("data.csv")
#print dat
xv=[1,2,3,4,1,2,3,4]
yv=[10,20,30,40,20,10,20,40]
alg=['a','b','a','b','a','b','a','b']
plot_data = {'x': xv, 'y': yv,'alg':alg}


ax = sns.lineplot(x='x', y='y',data=plot_data)#,hue='alg'
plt.show()