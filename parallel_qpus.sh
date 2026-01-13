#!/bin/bash

#SBATCH --job-name=parallel-qpus
#SBATCH --output=/shared/QHPC_Tutorial/parallel-qpus.out
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=quantum
#SBATCH --gres=qpu:1
#SBATCH --qpu=ibm_torino,ibm_fez,ibm_kingston

source /shared/pyenv/bin/activate
source ~/.cargo/env

NP=${NP:-2}  # Default to 2 if not set
mpirun --allow-run-as-root --oversubscribe -np $NP python parallel_qpus.py
