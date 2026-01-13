#!/bin/bash
#
#SBATCH --job-name=daxpy
#SBATCH --output=/shared/daxpy_%j.out
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=normal

echo "Job starting on $(hostname) at $(date)"

source /shared/pyenv/bin/activate
cd /shared

# Tell OpenMPI to only use the eth0 interface (not Docker bridge networks)
export OMPI_MCA_btl_tcp_if_include=eth0
export OMPI_MCA_oob_tcp_if_include=eth0

echo "Running MPI job..."
srun --mpi=pmix python3 daxpy.py

echo "Job completed at $(date)"
