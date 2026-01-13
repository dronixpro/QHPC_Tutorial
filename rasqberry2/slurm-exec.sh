#!/bin/bash
#
# slurm-exec.sh - Simple wrapper to exec into Slurm containers
#
# Usage:
#   ./slurm-exec.sh login          # Interactive shell on login node
#   ./slurm-exec.sh login sinfo    # Run sinfo on login node
#   ./slurm-exec.sh slurmctld scontrol show nodes
#
# Shortcuts:
#   ./slurm-exec.sh sinfo          # Runs sinfo on login
#   ./slurm-exec.sh squeue         # Runs squeue on login
#   ./slurm-exec.sh sacct          # Runs sacct on login

STACK_NAME="slurm"

# Color output
RED='\033[0;31m'
NC='\033[0m'

error() {
    echo -e "${RED}Error:${NC} $1" >&2
    exit 1
}

show_help() {
    echo "Usage: $0 <container> [command...]"
    echo ""
    echo "Containers:"
    echo "  login      - Login node (interactive shell or run commands)"
    echo "  slurmctld  - Controller daemon"
    echo "  slurmdbd   - Database daemon"
    echo "  c1-c4      - Compute nodes"
    echo "  q1-q2      - Quantum nodes"
    echo "  mysql      - Database server"
    echo ""
    echo "Shortcuts (run on login node):"
    echo "  sinfo, squeue, sacct, scontrol, sbatch, srun, scancel"
    echo ""
    echo "Examples:"
    echo "  $0 login                    # Shell on login node"
    echo "  $0 sinfo                    # Show partition info"
    echo "  $0 srun -N4 hostname        # Run job across 4 nodes"
    echo "  $0 c1 cat /etc/hostname     # Run command on c1"
    echo ""
}

# Handle help
if [[ "$1" == "-h" || "$1" == "--help" || -z "$1" ]]; then
    show_help
    exit 0
fi

# Check for shortcut commands (run on login node)
case "$1" in
    sinfo|squeue|sacct|scontrol|sbatch|srun|scancel|sacctmgr)
        container="login"
        cmd="$@"
        ;;
    *)
        container="$1"
        shift
        cmd="$@"
        ;;
esac

# Find container ID
container_id=$(docker ps -qf "name=${STACK_NAME}_${container}\." 2>/dev/null | head -1)

if [[ -z "$container_id" ]]; then
    # Try without the dot (in case exact match)
    container_id=$(docker ps -qf "name=${STACK_NAME}_${container}" 2>/dev/null | head -1)
fi

if [[ -z "$container_id" ]]; then
    error "Container '${container}' not found. Is the cluster running?"
fi

# Execute command or interactive shell
if [[ -z "$cmd" ]]; then
    exec docker exec -it "$container_id" bash
else
    exec docker exec "$container_id" $cmd
fi
