# Vertex and energy reconstruction based on Tweedie GLM

The details of reconstruction algorithm can be found [here](https://juno.ihep.ac.cn/cgi-bin/Dev_DocDB/ShowDocument?docid=9654).

**NOTE: HDF5 format required**

The file format of input file is HDF5.
You need to convert the original `.root` simulation files to `.h5` format. Here we prepare a tool named `tao_cvt` (author: Yuyi Wang),
which can help you to finish this work.
`tao_cvt` is compiled with the TAOSW,
you can find the execuable file in `taosw/InstallArea/bin/tao_cvt.exe`.

Use `-t` to specify the simulation type (`detsim` or `elecsim`) of file:
```shell
$ ./tao_cvt.exe -i input.root -o output.h5 -t {detsim | elecsim}
```

## Reconstruction with QADC

The main program used for reconstruction is `./qadc.py`.

Arguments:
+ `-i`: Input ElecSim file, hdf5 format
+ `-o`: Output file containing the reconstruction results
+ `--en`: Event number you want to use. By default, the first 2000 events will be used
+ `-c`: Response template (Probe). Default: `./probe_coef.h5`
+ `-g`: SiPM position csv file. Default: `./sipm_pos.csv`

The output hdf5 file includes a table named "rec_res",
where the first three columns are the reconstruction results of position, and the fourth column is the reconstructed kinetic energy.

### How to use

```shell
$ python3 ./qadc.py -i input_elecsim.h5 -o output.h5
```

## Reconstruction with QADC and first hit time of SiPM

The main program used for reconstruction is `./qadc_fht.py`.

Arguments:
+ `-i`: Input DetSim file, hdf5 format
+ `--ie`: Input ElecSim file, hdf5 format
+ `-o`: Output file containing the reconstruction results
+ `--en`: Event number you want to use. By default, the first 2000 events will be used
+ `-c`: Response template (Probe). Default: `./probe_coef.h5`
+ `--cs`: Scatter of probe curve. Default: `./probe_mc.h5`
+ `-g`: SiPM position csv file. Default: `./sipm_pos.csv`

The output hdf5 file includes a table named "rec_res",
where the first three columns are the reconstruction results of position, and the fourth and fifth column are the time shift and reconstructed kinetic energy, respectively.

### How to use

```shell
$ python3 ./qadc_fht.py -i input_detsim.h5 --ie input_elecsim.h5 -o output.h5
```