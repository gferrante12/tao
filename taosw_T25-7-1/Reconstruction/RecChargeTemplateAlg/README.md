# **Vertex Reconstruction Algorithm in TAO**

## **Introduction**
This is a package which achieves the vertex reconstruction algorithm in TAO. It's basic idea is to predict the hit (time) of the readout channels, construct the likelihood function, and then optimize the likelihood to get the vertex information of a given event.

## **Reconstruction**
### **Preparation**
- Generate the charge template
```bash
$ python share/create_charge_template.py \
$ --det_sim_input /path/to/detsim/file \
$ --elec_sim_input /path/to/elecsim/file \
$ --output /path/to/output/file \
$ --template_radius radius
```
You need to generate two kinds of charge templates, single site (Alpha or electron) charge templates and Ge68 charge template. For each kind of charge template, you need to generate several template with different radius. Once you have generated these charge templates, please organize them in a certain format (refer to the files below directory ./input).

### **Reconstruction**
```bash
$ python share/run.py --evtmax number --input /path/to/CalibAlg/file
```
Now, the input file is the output file of CalibAlg.

## **To do list**
- Use the geometry of TAO
    - Now we get the geometry of TAO detector either by hard-coded variable or self-defined class. It's better to get the geometry information through the sniper function.
- Change the input file
    - Now, we do not have the Calibration package. In the furture, we'd better use the output of the Calibration package to do the vertex reconstruction.
- Add the time likelihood
    - Now, we only use the charge information here, I hope the time information will improve the vertex reconstruction resolution.
