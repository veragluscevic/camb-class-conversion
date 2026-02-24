# Highlights

- **cosmological parameters Rui used** correspond to those in music.conf; CLASS output agrees perfectly with test_transfer_z99.dat file, once converted to CAMB format.

Omega_cdm = 0.239

Omega_Lambda = 0.714
Omega_b = 0.047
N_ur = 3.044
h = 0.7
sigma8 = 0.82
n_s = 0.96

dmeff_target = hydrogen
Vrel_dmeff = 0.0
N_dmeff = 1

P_k_max_h/Mpc = 200.
z_pk = 99

- **T_tot: Rui's conversion script uses CLASS's radiation-inclusive total, which differs from CAMB's matter-only convention by ~3% at k>30.** She used CLASS's `d_tot` which includes photons and massless neutrinos. Meanwhile, CAMB's "total" column is matter-only: (Omega_cdm * d_cdm + Omega_b * d_b) / (Omega_cdm + Omega_b). 

- **d_dmeff vs. d_cdm: Rui's script used d_cdm for d_dmeff.** With Omega_dmeff = 1e-15, the two agree at low k but differ by up to 7.6% at k ~ 38 h/Mpc (13.6% in the power spectrum). This is because of the dmeff-baryon scattering drag.

- **Rui likely used actual CAMB output only as a comparison template for CDM runs**; all other conversion files for dmeff come from CLASS (even those marked as "camb"). 


