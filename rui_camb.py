import numpy as np
from scipy.interpolate import InterpolatedUnivariateSpline

files = ['wdm_100kev_camb_z99_sync_tk.dat','wdm_100kev_class_z99_new_tk.dat','wdm_100kev_class_z99_new_background.dat']
data_camb_sync = np.loadtxt(files[0])
data_class_new=np.loadtxt(files[1])
data_back=np.loadtxt(files[2])

funH_z=InterpolatedUnivariateSpline(np.flip(data_back[:,0]),np.flip(data_back[:,3]))
z=99
H=funH_z(z) #1/Mpc

header = '{0:^15s} {1:^15s} {2:^15s} {3:^15s} {4:^15s} {5:^15s} {6:^15s} {7:^15s} {8:^15s} {9:^15s} {10:^15s} {11:^15s} {12:^15s}'.format('k/h','CDM','baryon','photon','nu','mass_nu','total','no_nu','total_de','Weyl','v_CDM','v_b','v_b-v_c')

h=0.7

dummy=[]
vc=[]
vb=[]
for i in range(len(data_class_new[:,0])):
    dummy.append(0.0)
    vc.append((1+z)*data_class_new[i,11]/((data_class_new[i,0]*h)**2*H))
    vb.append((1+z)*data_class_new[i,10]/((data_class_new[i,0]*h)**2*H))

np.savetxt('wdm_100kev_Tk.dat', np.column_stack((data_camb_sync[:,0], np.abs(data_camb_sync[:,1]), np.abs(data_camb_sync[:,4]),dummy,dummy,dummy,np.abs(data_camb_sync[:,9]),dummy,dummy,dummy,np.abs(vc),np.abs(vb),dummy)),fmt='%15.6e', header=header)