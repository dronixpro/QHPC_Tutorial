# Hybrid Slurm Cluster (Multi-Pi Deployment)

This directory contains configuration for deploying a 6-node Slurm cluster across two Raspberry Pi 5 nodes.

## Architecture

```
rasqberry (192.168.4.160)          rasqberry2 (192.168.4.164)
┌──────────────────────────┐       ┌──────────────────────────┐
│  Control Services        │       │                          │
│  - mysql                 │       │                          │
│  - slurmdbd              │       │                          │
│  - slurmctld             │       │                          │
│  - login                 │       │                          │
│                          │       │                          │
│  Compute Nodes           │       │  Compute Nodes           │
│  - c1 (port 6818)        │       │  - c3 (port 6818)        │
│  - c2 (port 6828)        │       │  - c4 (port 6828)        │
│  - q1 (port 6838)        │       │  - q2 (port 6838)        │
└──────────────────────────┘       └──────────────────────────┘
         │                                    │
         └────────────────────────────────────┘
                    NFS Shared Storage
                      (/mnt/shared)
```

## Partitions

- **normal**: c1, c2, c3, c4 (classical compute nodes)
- **quantum**: q1, q2 (quantum nodes with QPU GRES)

## Deployment

```bash
./deploy-hybrid.sh          # Deploy the cluster
./deploy-hybrid.sh stop     # Stop all containers
./deploy-hybrid.sh status   # Show cluster status
```

## MPI Configuration (IMPORTANT)

For MPI jobs to work correctly across nodes in this hybrid Docker setup, your batch scripts **MUST** include the following environment variables:

```bash
#!/bin/bash
#SBATCH --job-name=mpi_job
#SBATCH --nodes=4
#SBATCH --partition=normal

# REQUIRED: Tell OpenMPI to use physical network interface
export OMPI_MCA_btl_tcp_if_include=eth0
export OMPI_MCA_oob_tcp_if_include=eth0

source /shared/pyenv/bin/activate
srun --mpi=pmix python3 your_mpi_script.py
```

### Why is this needed?

The compute nodes use Docker's host networking mode, but they also have Docker bridge network interfaces (172.x.x.x). Without these settings, OpenMPI may try to use the bridge network IPs for inter-process communication, which fails because:

1. Bridge networks are isolated to each Docker host
2. The 172.x.x.x addresses are not routable between rasqberry and rasqberry2

By setting `OMPI_MCA_btl_tcp_if_include=eth0` and `OMPI_MCA_oob_tcp_if_include=eth0`, we force OpenMPI to only use the physical network interface that connects both Raspberry Pi nodes.

## Example MPI Job

See `/shared/daxpy.sh` for a complete working example:

```bash
docker exec login sbatch /shared/daxpy.sh
```

## Testing the Cluster

```bash
# Test simple job across all normal nodes
docker exec login srun -p normal -N4 hostname

# Test quantum partition
docker exec login srun -p quantum --gres=qpu:1 hostname

# Interactive MPI test
docker exec login bash -c 'source /shared/pyenv/bin/activate && \
  export OMPI_MCA_btl_tcp_if_include=eth0 && \
  export OMPI_MCA_oob_tcp_if_include=eth0 && \
  srun -p normal -N4 --mpi=pmix python3 -c "from mpi4py import MPI; print(f\"Rank {MPI.COMM_WORLD.Get_rank()}\")"'
```

## Files

- `deploy-hybrid.sh` - Main deployment script
- `docker-compose-hybrid.yml` - Docker Compose for rasqberry (control + c1, c2, q1)
- `slurm-hybrid.conf` - Slurm configuration for 6-node cluster
- `gres-hybrid.conf` - GRES configuration for QPU resources
- `etc_slurm/` - Generated config directory (created by deploy script)

## Troubleshooting

### MPI jobs hang or timeout

Check that your batch script includes the OpenMPI interface settings:
```bash
export OMPI_MCA_btl_tcp_if_include=eth0
export OMPI_MCA_oob_tcp_if_include=eth0
```

### Nodes show as DOWN

Check if containers are running on both hosts:
```bash
docker ps                                    # on rasqberry
ssh rasqberry2 docker ps                     # on rasqberry2
```

### Permission denied on munge.key

The munge key must have correct permissions:
```bash
# On rasqberry2
sudo chown 998:998 ~/slurm-remote/munge.key
sudo chmod 400 ~/slurm-remote/munge.key
```
