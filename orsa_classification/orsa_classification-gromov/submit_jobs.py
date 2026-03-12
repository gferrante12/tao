#!/usr/bin/env python3
"""
Batch Submission Script for OrsaClassification
==============================================

This script automates the submission of analysis jobs to HTCondor (or compatible
batch systems). It handles:
  1. Locating input files for a given run number.
  2. Splitting the file list into chunks for parallel processing.
  3. Generating a job-specific file list, shell wrapper, and Condor submit file.
  4. Creating a master submission script to launch all jobs.

Usage:
    python submit_jobs.py --run <RunNum> --type <TAO|JUNO> [options]

Options:
    --nfiles    : Number of files to process per job (default: 10).
    --outdir    : Base directory for output (logs, scripts, root_output).
    --config    : Path to analysis configuration JSON.
    --FORCE     : Bypass junosub and force direct submission with c_submit.
    --test-one  : If set, submits only the first job chunk for testing.
"""

import os
import argparse
import glob
import subprocess
import math

def get_input_files(run_number, exp_type):
    """
    Locate input files based on run number and experiment type.
    Modify the base path pattern to match your actual data location.
    
    Returns:
        List of absolute file paths sorted by name.
    """
    if exp_type == "TAO":
        base_dir = f"/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-kup/*/mix_stream/*/*/{run_number}/"
        pattern = os.path.join(base_dir, "*.esd")
    else: # JUNO
        # Placeholder for JUNO data path
        base_dir = f"/storage/gpfs_data/juno/junofs/production/data/juno/{run_number}/"
        pattern = os.path.join(base_dir, "*.root")

    files = glob.glob(pattern)
    files.sort()
    return files

def create_job_scripts(run_number, exp_type, file_chunks, output_base, config_path, dry_run=False, test_one=False):
    """
    Generates all necessary scripts (file list, .sh, .sub) for each job chunk.
    
    Structure of output_base:
      /logs        -> stdout, stderr, condor logs
      /scripts     -> .sh wrappers, .sub submit files
      /lists       -> input file lists
      /root_output -> output ROOT files
    """
    logs_dir = os.path.join(output_base, "logs")
    scripts_dir = os.path.join(output_base, "scripts")
    lists_dir = os.path.join(output_base, "lists")
    root_out_dir = os.path.join(output_base, "root_output")

    for d in [logs_dir, scripts_dir, lists_dir, root_out_dir]:
        os.makedirs(d, exist_ok=True)

    submit_files = []

    # Determine environment setup command based on experiment type.
    if exp_type == "TAO":
        setup_cmd = "source /cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/Jlatest/setup-tao.sh"
    else:
        setup_cmd = "source /cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/Jlatest/setup.sh"

    cwd = os.getcwd() # Jobs will start in the current working directory.
    config_path = os.path.abspath(config_path)
    
    # Locate the run.py script and local setup.sh relative to this script.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    if exp_type == "TAO":
        run_script = os.path.join(script_dir, "InstallArea", "taosw", "share", "run.py")
        setup_path = os.path.join(script_dir, "InstallArea", "taosw", "setup.sh")
    else:
        run_script = os.path.join(script_dir, "InstallArea", "junosw", "share", "run.py")
        setup_path = os.path.join(script_dir, "InstallArea", "junosw", "setup.sh")

    # Iterate over file chunks and create job scripts.
    for i, chunk in enumerate(file_chunks):
        job_id = f"{run_number}_{i:04d}"
        
        # 1. Create File List: writes the subset of files for this job.
        list_file = os.path.abspath(os.path.join(lists_dir, f"{job_id}.list"))
        with open(list_file, "w") as f:
            for line in chunk:
                f.write(line + "\n")

        # 2. Create Shell Script: sets up env and runs run.py.
        sh_file = os.path.abspath(os.path.join(scripts_dir, f"job_{job_id}.sh"))
        log_file = os.path.abspath(os.path.join(logs_dir, f"job_{job_id}.log"))
        root_file = os.path.abspath(os.path.join(root_out_dir, f"output_{job_id}.root"))
        
        script_content = f"""#!/bin/bash
echo "--- Job {job_id} started on $(hostname) at $(date) ---" > {log_file}
cd {cwd}
echo "Setting up environment..." >> {log_file}
{setup_cmd}
source {setup_path}
echo "Setup complete." >> {log_file}

echo "Running OrsaAlg..." >> {log_file}
# Execute with infinite max events (-1) since file list limits the scope.
python {run_script} --input-list {list_file} --output {root_file} --config {config_path} --evtmax -1 --loglevel 3 >> {log_file} 2>&1

EXIT_CODE=$?
echo "--- Job finished with code $EXIT_CODE at $(date) ---" >> {log_file}
exit $EXIT_CODE
"""
        with open(sh_file, "w") as f:
            f.write(script_content)
        os.chmod(sh_file, 0o755)

        # 3. Create Condor Submit File
        sub_file = os.path.join(scripts_dir, f"job_{job_id}.sub")
        # Automatically infer Junosub's HTCondor accounting parameters.
        user = os.environ.get("USER", "")
        sub_content = f"""
universe = vanilla
executable = {sh_file}
output = {log_file}.out
error = {log_file}.err
log = {log_file}.condor
+PrimaryUnixGroup = "juno"
+AccountingGroup = "juno.{user}"
getenv = True
+JobFlavour = "testmatch"
queue
"""
        with open(sub_file, "w") as f:
            f.write(sub_content)
        
        submit_files.append(sub_file)

        if test_one:
            break

    return submit_files

def main():
    parser = argparse.ArgumentParser(description="Submit Analysis Jobs")
    parser.add_argument("--run", required=True, type=str, help="Run Number")
    parser.add_argument("--type", choices=["TAO", "JUNO"], required=True, help="Experiment Type")
    parser.add_argument("--nfiles", type=int, default=10, help="Files per job")
    parser.add_argument("--outdir", default="../tests", help="Output base directory")
    parser.add_argument("--config", default="share/config_tao_production.json", help="Config file path")
    parser.add_argument("--FORCE", action="store_true", help="Force direct submission using c_submit (bypasses junosub limit checker)")
    parser.add_argument("--test-one", action="store_true", help="Submit only the first job for testing")
    
    args = parser.parse_args()

    # 1. Locate Input Files
    files = get_input_files(args.run, args.type)
    if not files:
        print(f"No files found for Run {args.run} ({args.type})")
        return

    print(f"Found {len(files)} files.")

    # 2. Chunk Files
    chunks = [files[i:i + args.nfiles] for i in range(0, len(files), args.nfiles)]
    print(f"Split into {len(chunks)} jobs.")

    # 3. Generate Scripts
    sub_files = create_job_scripts(args.run, args.type, chunks, args.outdir, args.config, test_one=args.test_one)

    # 4. Submit or Create Master Script
    submit_cmd = "c_submit"

    if args.test_one:
        print(f"Test mode: submitting only 1 job: {sub_files[0]}")
        subprocess.run([submit_cmd, sub_files[0]])
    else:
        # Generate a master bash script to submit all jobs sequentially.
        master_list = os.path.join(args.outdir, f"submit_all_{args.run}.sh")
        with open(master_list, "w") as f:
            f.write("#!/bin/bash\n")
            for sub in sub_files:
                f.write(f"{submit_cmd} {os.path.abspath(sub)}\n")
        
        os.chmod(master_list, 0o755)
        
        if not args.FORCE:
            print(f"Submitting securely using junosub...")
            junosub_log = os.path.join(args.outdir, f"junosub_submission_{args.run}.out")
            with open(junosub_log, "w") as log_file:
                subprocess.Popen(
                    ["junosub", os.path.abspath(master_list)],
                    stdout=log_file,
                    stderr=subprocess.STDOUT
                )
            print(f"Junosub background process fully deployed. Logs visible in {junosub_log}")
        else:
            print(f"FORCE is set. Submitting directly with c_submit completely bypassing limits.")
            for sub in sub_files:
                subprocess.run([submit_cmd, sub])
            print("Direct submission script generation complete.")

if __name__ == "__main__":
    main()
