# OrsaClassification Framework
*(partly AI-generated README and documentation)

## Table of Contents

- [Introduction](#introduction)
- [Structural Architecture](#structural-architecture)
- [Directory Structure and Key Components](#directory-structure-and-key-components)
- [CNAF Deployment: Cloning, Building, and Execution](#cnaf-deployment-cloning-building-and-execution)
  - [1. Cloning the Repository](#1-cloning-the-repository)
  - [2. Initiating Target Environments and Compilation](#2-initiating-target-environments-and-compilation)
  - [3. Local Execution Sequences](#3-local-execution-sequences)
  - [4. High-Throughput Cluster Submission at CNAF](#4-high-throughput-cluster-submission-at-cnaf)
- [JINR Deployment: Cloning, Building, and Execution](#jinr-deployment-cloning-building-and-execution)
  - [1. Cloning the Repository](#1-cloning-the-repository-1)
  - [2. Initiating Target Environments and Compilation](#2-initiating-target-environments-and-compilation-1)
  - [3. Local Execution Sequences](#3-local-execution-sequences-1)
  - [4. High-Throughput Cluster Submission at JINR](#4-high-throughput-cluster-submission-at-jinr)
- [Parameterization Schemas](#parameterization-schemas)
  - [Available Correlation Rules](#available-correlation-rules)
  - [JSON Implementation Example](#json-implementation-example)
- [Serialization Architecture](serialization-architecture)

## Introduction

The OrsaClassification library provides a rigorous and highly configurable event classification and delayed coincidence correlation engine tailored specifically for the JUNO and TAO neutrino observatory data models. Operating directly within the SNiPER algorithmic architecture, the framework systematically interprets reconstructed event topology geometries (ESD files), applies structured single-event parameter cuts, and actively cross-correlates multi-event physics signatures including inverse beta decay coincidence matching, transient muon spallation vetoing, and extended cosmogenic isotope temporal tracking.

The analytical pipeline is exclusively parameterized via a centralized JSON configuration dictionary, structurally separating the foundational physics implementation from the fluid definition of event selection categories and structural temporal matching rules. This explicitly provides continuous optimization iterations without necessitating core framework recompilation.

## Structural Architecture

The architecture relies strictly on lazy-evaluation paradigms to minimize computational overhead when interfacing with complex native data models. The logical flow is visualized below:

```text
  ESD file (RecHeaders, CalibHeaders, OecHeaders, ...)
       │
       ▼
  ┌──────────────────┐
  │     OrsaAlg      │  SNiPER algorithm entry point
  │  (execute loop)  │
  └───────┬──────────┘
          │  encapsulates each EvtNavigator via JunoEventWrapper
          ▼
  ┌──────────────────┐
  │  EventWrapper    │  lazy-loaded accessor for physical parameters
  └───────┬──────────┘
          │  snapshot translates into a lightweight Candidate
          ▼
  ┌──────────────────┐
  │   Selectors      │  isolated single-event thresholds
  │  (Categories)    │  categorizes and assigns descriptive Tag IDs
  └───────┬──────────┘
          │  tagged Candidate proceeds to structural correlation:
          ▼
  ┌──────────────────┐       ┌─────────────────┐
  │ CorrelationEngine│──────▶│  MuonManager    │  continuous muon boundary tracker
  │ (sliding window) │       └─────────────────┘
  │                  │       ┌─────────────────┐
  │ evaluates rules: │──────▶│ HistoryManager  │  macro-temporal spatial indexing
  │                  │       └─────────────────┘
  └───────┬──────────┘
          │  verified correlations define output mappings:
          ▼
  ┌──────────────────┐
  │  OutputManager   │  allocates and serializes ROOT TTrees dynamically
  └──────────────────┘
```

## Directory Structure and Key Components

The repository separates abstract logic structures from concrete execution binaries. Essential files required for modification are detailed below:

```text
OrsaClassification/
├── include/             Structural C++ headers defining logic frameworks
│   ├── OrsaAlg.h            Top-level SNiPER algorithm initialization
│   ├── EventWrapper.h       Detector-agnostic event data encapsulation
│   ├── Candidate.h          Immutable event snapshot for temporal windows
│   ├── Selector.h           Single-event topological evaluation criteria
│   ├── CorrelationEngine.h  Chronological sliding-window logic handler
│   ├── CorrelationRules.h   Concrete multi-event logical evaluation rules
│   ├── IsolationBurstRule.h High-multiplicity spatial clustering logic
│   ├── MuonManager.h        Topological muon proximity calculations
│   ├── HistoryManager.h     Long-baseline multi-variable spatial index
│   ├── OutputManager.h      Dynamic ROOT TTree branch serialization
│   ├── TagRegistry.h        Bidirectional tag nomenclature synchronization
│   └── ConfigLoader.h       JSON interpretation for framework parameterization
├── src/                 C++ implementation files
│   ├── OrsaAlg.cc           Primary execution timeline management
│   ├── CorrelationEngine.cc Window pruning and sequential processing logic
│   ├── ConfigLoader.cc      JSON categorical interpretation methods
│   └── OutputManager.cc     TTree binding and output normalization
├── config/              Standardized JSON parameterizations
│   └── config_tao.json      TAO implementation template
├── share/               Operational steering scripts
│   └── run.py               Python interface initializing SNiPER parameters
├── build.sh             Master parallel compilation automation
├── build_juno.sh        JUNO-specific CMake configuration compiler
├── build_tao.sh         TAO-specific CMake configuration compiler
├── submit_jobs.py       Cluster submission configuration logic via HTCondor
└── CMakeLists.txt       CMake macro architectural definitions
```

## CNAF Deployment: Cloning, Building, and Execution

The framework is actively maintained and executed on the regular CNAF distributed infrastructure. Given the differing offline models between JUNO and TAO, accurate CVMFS environments must be initialized prior to code compilation.

### 1. Cloning the Repository
Acquire the source code from the primary version control repository executing the following routine on the CNAF terminal:

```bash
git clone https://code.ihep.ac.cn/orsa/orsa_classification.git
cd OrsaClassification
```

### 2. Initiating Target Environments and Compilation
The system strictly requires compilation against the validated JUNO and TAO experimental software releases distributed via CVMFS. Initialize the respective offline environment, and run the designated build sequence:

```bash
# Initialize CNAF CVMFS Environment (Example for TAO):
source /cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.6.4/setup-tao.sh

# Run explicit TAO compilation process (similarly ./build_juno.sh for JUNO):
./build_tao.sh

# Load generated local library variables
source InstallArea/taosw/setup.sh
```

### 3. Local Execution Sequences
Standard operational invocation connects target event datasets directly:

```bash
# Execute selection over isolated sample file
python share/run.py --input /path/to/data.esd --output output.root \
       --config config/config_tao.json --evtmax -1

# Process large scale textual listing
python share/run.py --input-list files.list --output output.root \
       --config config/config_tao.json --evtmax -1 --loglevel 3
```

### 4. High-Throughput Cluster Submission at CNAF
For massive dataset parallelization on the CNAF framework, standard HTCondor allocation scripts orchestrate automated job chunking.

The standard submission procedure respects distributed queue restrictions automatically using the HTCondor `junosub` tracking utility dynamically executed by the helper script:

```bash
# Generate localized submission files and background the job submission safely using `junosub` limits.
python submit_jobs.py --run 00120 --type TAO --nfiles 10 \
       --outdir ../experiments --config config/config_tao.json
```
*(The scripts log `junosub` output securely inside your specified `--outdir` folder).*

For unrestricted immediate submission (warning: bypasses user queue limitations entirely), utilize the `--FORCE` flag:
```bash
# Bypass 'junosub' allocating jobs dynamically via 'c_submit' directly.
python submit_jobs.py --run 00120 --type TAO --nfiles 10 \
       --outdir ../experiments --config config/config_tao.json --FORCE
```

Pre-computation structural verification (Single Job Logic Check) can be run concurrently:
```bash
python submit_jobs.py --run 00120 --type TAO --test-one
```

## JINR Deployment: Cloning, Building, and Execution

VM for submission: 10.220.18.43. Use your JINR SSO account to log in. The built project can be found at
/juno/tao_analysis/orsa_classification

### 1. Cloning the Repository

```bash
cd /juno/tao_analysis/your_folder
git clone https://code.ihep.ac.cn/orsa/orsa_classification.git
cd orsa_classification
git switch gromov
```

### 2. Initiating Target Environments and Compilation

```bash
# Initialize JINR CVMFS Environment (Example for TAO):
source /cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.2/setup-tao.sh

# Run explicit TAO compilation process (similarly ./build_juno.sh for JUNO):
./build_tao.sh

# Load generated local library variables
source InstallArea/taosw/setup.sh
```

### 3. Local Execution Sequences

```bash
# Go to the project folder
cd path_to_the_orsa_classification_folder

# Initialize JINR CVMFS Environment (Example for TAO):
source /cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.2/setup-tao.sh

# Load generated local library variables
source InstallArea/taosw/setup.sh

# Execute selection over isolated sample file
python share/run.py --input /path/to/data.esd --output output.root \
       --config config/config_tao.json --evtmax -1

# Process large scale textual listing
python share/run.py --input-list files.list --output output.root \
       --config config/config_tao.json --evtmax -1 --loglevel 3
```

### 4. High-Throughput Cluster Submission at JINR
The HTCondor system is used to parallelize the processing of massive datasets on the JINR cluster. 

But first you need to configure access to the dCache storage. 

Initialize your proxy (the --valid key can be omitted, the proxy will be valid for 12 hours by default):

```bash
voms-proxy-init --voms juno --valid 240:00 
```

You are activating xrootd for the needs of the python submission script. Just source the entire ROOT package:

```bash
source /cvmfs/sft.cern.ch/lcg/releases/LCG_109/ROOT/6.38.00/x86_64-el9-gcc15-opt/ROOT-env.sh
```

The python script manages automated job chunking and submission.

```bash
python submit_jobs_universal.py --run 1400 --type TAO \
        --nfiles 10 --outdir ../your_output_folder \
        --cluster JINR --config config/config_tao.json
```
*(The scripts log output securely inside your specified `--outdir` folder).*

Pre-computation structural verification (Single Job Logic Check) can be run concurrently:
```bash
python submit_jobs_universal.py --run 1400 --type TAO \ 
        --cluster JINR --test-one
```

## Parameterization Schemas

Analytical parameterization structurally delineates logical event characterization `Categories` and systematic combinatorial matching `Rules`. This format offers explicit configuration logic manipulation without altering internal implementation code.

### Available Correlation Rules

The extensive rule mapping syntax dynamically allocates concrete analysis operations:

| Identifier           | Analytical Evaluation Purpose                                   |
|:---------------------|:----------------------------------------------------------------|
| `Pair`               | Delayed coincidence (evaluates standard and accidental windows) |
| `MuonVeto`           | Temporal exclusions following identified primary transversals   |
| `MuonNeutron`        | Identifies muons coupled with neutron-like secondary ejections  |
| `Spallation`         | Space-time correlation tracing interactions to muon tracks      |
| `Coincidence`        | Generic dual-tag chronological overlap verification             |
| `IsolationBurst`     | Sub-window spatial multiplicity clustering detection            |
| `LongHistory`        | Extended historical search locating macro-delayed signatures    |
| `DataQuality`        | Temporal gap monitoring and systematic dead-time application    |
| `IsolationQuality`   | Post-correlation background proximity thresholds on candidates  |
| `Compound`           | Internal boolean composition (AND/OR integration limits)        |
| `Category`           | Promotes isolated tag designations across compound pathways     |

### JSON Implementation Example

An excerpt illustrating an elementary prompt-delayed topological parameterization:

```json
{
    "Categories": {
        "PromptCandidate": {
            "cuts": {
                "energy_min": 0.7,
                "energy_max": 12.0,
                "detector": "CD",
                "radius_max": 16000.0
            }
        },
        "DelayedCandidate": {
            "cuts": {
                "energy_min": 1.9,
                "energy_max": 2.5,
                "detector": "CD"
            }
        }
    },
    "Rules": {
        "IBD_Selection": {
            "type": "Pair",
            "prompt": "PromptCandidate",
            "delayed": "DelayedCandidate",
            "dt_min": 1000,
            "dt_max": 2000000,
            "dr_max": 2000.0,
            "new_tag": "IBDPair",
            "output": {
                "save_muon_info": true,
                "save_tags": true
            }
        }
    }
}
```

## Serialization Architecture

Processed mathematical topologies permanently resolve into persistent ROOT TTree structures. Individual topological rules independently instantiate dedicated data branches housing fundamental candidate kinematics, explicitly reconstructed distance intervals, temporal offsets referencing isolated background tracking buffers, extensive PMT channel multiplicity arrays, and complete event tag vectors.

Accidental background spectra estimations concurrently compile paired distributions utilizing structured temporal shifting algorithms. Furthermore, the base JSON configuration sequence embeds directly as `ProductionConfig` alongside `TagMap` matrices identically within ROOT objects, securing comprehensive verification parity through unified self-documentation methodologies.
