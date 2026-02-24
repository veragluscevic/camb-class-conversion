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

- **Rui likely used actual CAMB output only as a comparison template for CDM runs**; all other conversion files for dmeff come from CLASS (even those marked as "camb"). 

- **d_dmeff vs. d_cdm: Rui's script used d_cdm for d_dmeff.** With Omega_dmeff = 1e-15, the two agree at low k but differ by up to 7.6% at k ~ 38 h/Mpc (13.6% in the power spectrum). This is because of the dmeff-baryon scattering drag.

- **for velocity transfers, however, Rui seems to have always used t_dmeff**, rather than t_cdm, which makes sense and I kept that in our conversion script.

- **Rui used only ABSOLUTE VALUES of transfers d**; this is only ok for DMO runs, since the transfer function is squared before the ICs are generated, but it would be a problem for hydro sims where the relative phase of baryons/IDM/CDM might matter.

- **there is some noise in our velocity transfers at k>100** which was not there in Rui's runs. This should not affect the sims.

- **all tests passed, the new conversion script class_to_camb.py** reproduces Rui's transfers for CDM and for one IDM case, for densities and velocities. The remaining differences (see above) are too small to matter in sims. All test plots are in plots/



