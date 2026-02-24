import numpy as np
from scipy.interpolate import Akima1DInterpolator
import matplotlib.pyplot as plt

index = 11

plt.figure()
#data_class = np.loadtxt('output/CDM_class_tk.dat')
#data_camb = np.loadtxt('output/CDM_camb_tk.dat')
data_class = np.loadtxt('test2.dat')
data_camb = np.loadtxt('test_transfer_z99.dat')

k_camb = data_camb[:,0]
tk_camb = data_camb[:, index]

k_class = data_class[:,0]
tk_class = data_class[:, index]


# Hybrid interpolation: use log-log for positive data, Akima for oscillatory/negative
# Clip k to valid range to prevent extrapolation artifacts at boundaries
k_min, k_max = k_camb.min(), k_camb.max()
k_clipped = np.clip(k_class, k_min, k_max)

# Check if all values are positive (use log-log interpolation if so)
if np.all(tk_camb > 0):
    # Log-log interpolation: best for smooth positive transfer functions
    tk_camb_interp = np.exp(np.interp(np.log(k_clipped), np.log(k_camb), np.log(tk_camb)))
else:
    # Akima interpolation: handles negative values and oscillatory behavior
    sort_idx = np.argsort(k_camb)
    k_camb_sorted = k_camb[sort_idx]
    tk_camb_sorted = tk_camb[sort_idx]
    akima_interp = Akima1DInterpolator(k_camb_sorted, tk_camb_sorted)
    tk_camb_interp = akima_interp(k_clipped)


#plt.semilogx(k_clipped, (-tk_camb_interp*k_camb**2*0.7**2/tk_class)**2, color='k', label='(class/camb)^2')

plt.semilogx(k_clipped, (tk_camb_interp/tk_class)**2, color='k', label='(camb/class)^2')

#plt.semilogx(k_camb,tk_camb**2, '--',color='r', label='(camb)^2')
#plt.xlim(0.1,200)
plt.ylim(0.5, 1.5)



plt.xlabel('k')
plt.legend()
plt.show()
#plt.savefig('n2_1e-2GeV_7.1e-24_pk_ratio.pdf', dpi=300)

