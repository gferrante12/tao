# The Tao Event Reconstruction Analysis Tool User Guide

This document provides instructions on how to use the Charge-Center Analysis tool for event reconstruction.

## Parameters Description

### Required Parameters

- `--input`
  - **Description**: Specify the input filename(s). You can provide multiple files. The file is from after the calibration simulation.
  - **Example**: `--input file1.root file2.root`

### Optional Parameters

- `--evtmax`
  - **Type**: `int`
  - **Default**: `10`
  - **Description**: Specify the number of events to be processed. If it is set to `-1`, it will analyze the entire input file.

- `--seed`
  - **Type**: `int`
  - **Default**: `1`
  - **Description**: Set the random seed.

- `--input_ElecFile`
  - **Type**: `string`
  - **Default**: `user-input_ElecFile.root`
  - **Description**: Specify the ElecSim input filename.
  - **Note**: If `--isRealData` is set to `true`, the user does not need to provide this parameter.

- `--output`
  - **Type**: `string`
  - **Default**: `rec-output.root`
  - **Description**: Specify the output filename. This filename follows the offline framework output format and cannot be changed.

- `--user-output`
  - **Type**: `string`
  - **Default**: `user-ana-output.root`
  - **Description**: Specify the user-defined output filename. The content saved in this file can be modified by the user.

- `--algorithm`
  - **Type**: `string`
  - **Default**: `ChargeCenterRec`
  - **Description**: Specify the analysis algorithm to use.

- `--isRealData`
  - **Type**: `string`
  - **Choices**: `true` or `false`
  - **Default**: `false`
  - **Description**: Specify whether the input data is real data. If set to `true`, the user does not need to provide the `--input_ElecFile` parameter.
- `--isOpeningsCorrection`
  - **Type**: `bool`
  - **Default**: `true`
  - **Description**: Specify whether to correct the opening angle of the Cherenkov light.
- `--isDarkNoiseCorrection`
  - **Type**: `bool`
  - **Default**: `true`
  - **Description**: Specify whether to correct the dark noise.
- `CurveCorrectionPattern`
  - **Type**: `string`
  - **Default**: `0`
  - **Description**: Specify the curve correction pattern. The default value is 'None', which means no curve correction. 
                      The value 'AllCalibcurve' means the curve correction is based on the CLS & ACU. 
                      The value 'multicurve' means the curve correction is also based on the CLS & ACU, but fit with diffrent R.

## Usage Example

Here is an example of how to run the Tao Detector Simulation Analysis:

```bash
$ python /junofs/users/shihangyu/taosw-main/Reconstruction/RecChargeCenterAlg/share/run.py \
$    --input path/CalibrationSim.root \
$    --input_ElecFile path/ElecSim.root \
$    --user-output user_defined_output.root \
$    --output rec_EDM_output.root \
$    --isRealData false 
$    --isOpeningsCorrection true
$    --isDarkNoiseCorrection true
$    --CurveCorrectionPattern multicurve
```