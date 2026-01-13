# Raspberry Pi 5 Slurm Cluster - Deployment Guide

This directory contains configurations for deploying a Slurm HPC cluster across two Raspberry Pi 5 nodes: `rasqberry` (192.168.4.160) and `rasqberry2` (192.168.4.164).

## Deployment Options

There are two deployment methods available:

| Method | Description | MPI Support | Complexity |
|--------|-------------|-------------|------------|
| **Hybrid (Recommended)** | Bridge + Host networking | Full MPI across nodes | Simple |
| Docker Swarm | Overlay networking | Limited (single-host MPI only) | Complex |

The **Hybrid approach** is recommended for MPI workloads as it allows direct TCP communication between nodes.

---

## Hybrid Deployment (Recommended)

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  rasqberry (192.168.4.160)           │  rasqberry2 (192.168.4.164)          │
│  ┌─────────────────────────────────┐ │  ┌─────────────────────────────────┐ │
│  │ Bridge Network                  │ │  │ Host Network                    │ │
│  │  ├── mysql                      │ │  │  ├── c3 (slurmd, port 6818)     │ │
│  │  ├── slurmdbd (port 6819)       │ │  │  ├── c4 (slurmd, port 6828)     │ │
│  │  └── slurmctld (port 6817)      │ │  │  └── q2 (slurmd, port 6838)     │ │
│  └─────────────────────────────────┘ │  └─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │        ↑                             │
│  │ Host Network                    │ │        │ NFS mount                   │
│  │  ├── login                      │ │        │ /mnt/shared                 │
│  │  ├── c1 (slurmd, port 6818)     │ │        │                             │
│  │  ├── c2 (slurmd, port 6828)     │ └────────┼─────────────────────────────┘
│  │  └── q1 (slurmd, port 6838)     │          │
│  └─────────────────────────────────┘          │
│        │                                      │
│        └── NFS Server ────────────────────────┘
│            /home/.../shared
└─────────────────────────────────────────────────────────────────────────────┘
```

### Nodes and Partitions

| Partition | Nodes | Description |
|-----------|-------|-------------|
| `normal` | c1, c2, c3, c4 | Classical compute nodes (4 CPUs each) |
| `quantum` (default) | q1, q2 | Quantum nodes (1 CPU, 1 QPU GRES each) |

**Node Distribution:**
- **rasqberry**: c1, c2, q1 + control services (mysql, slurmdbd, slurmctld, login)
- **rasqberry2**: c3, c4, q2

**Port Assignments** (multiple slurmd on same host requires unique ports):
- c1/c3: port 6818
- c2/c4: port 6828
- q1/q2: port 6838

### Prerequisites

1. **Docker** installed on both Pis
2. **NFS packages**: `nfs-kernel-server` on rasqberry, `nfs-common` on rasqberry2
3. **SSH access** from rasqberry to rasqberry2 (passwordless recommended)
4. **Docker image** `slurm-docker-cluster:25.05.3-dev` on both nodes

### Quick Start

```bash
cd /home/rasqberry/QCSC/hpc-course-demos/source/rasqberry2

# Deploy the entire cluster (both Pis)
./deploy-hybrid.sh

# Or start manually on rasqberry
docker compose -f docker-compose-hybrid.yml up -d

# Wait for services to initialize (~20 seconds)
sleep 20

# Verify the cluster
docker exec login sinfo
```

Then deploy c3, c4, q2 on rasqberry2:

```bash
# SSH to rasqberry2 and start remote nodes
ssh rasqberry2 "cd ~/slurm-remote && docker compose up -d"
```

### Files for Hybrid Deployment

| File | Description |
|------|-------------|
| `docker-compose-hybrid.yml` | Main cluster on rasqberry (mysql, slurmdbd, slurmctld, login, c1, c2, q1) |
| `slurm-hybrid.conf` | Slurm config with NodeAddr and Port for host networking |
| `gres-hybrid.conf` | GRES configuration for quantum nodes (q1, q2) |
| `deploy-hybrid.sh` | Automated deployment script for full cluster |

### NFS Setup

NFS synchronizes the `/shared` directory between both Pis:

**On rasqberry (already configured):**
```bash
# /etc/exports contains:
/home/rasqberry/QCSC/hpc-course-demos/source/slurm-docker-cluster/shared *(rw,sync,no_subtree_check,no_root_squash,insecure)
```

**On rasqberry2:**
```bash
# Mount the NFS share
sudo mkdir -p /mnt/shared
sudo mount -t nfs 192.168.4.160:/home/rasqberry/QCSC/hpc-course-demos/source/slurm-docker-cluster/shared /mnt/shared -o rw,nolock,soft

# Add to /etc/fstab for persistence
192.168.4.160:/home/rasqberry/QCSC/hpc-course-demos/source/slurm-docker-cluster/shared /mnt/shared nfs rw,nolock,soft 0 0
```

### Deploying Remote Nodes on rasqberry2

The `deploy-hybrid.sh` script automates this, or manually:

```bash
# On rasqberry2, create the working directory
mkdir -p ~/slurm-remote
cd ~/slurm-remote

# Copy configs from rasqberry (the deploy script does this for you)
# Required files: munge.key, slurm.conf, gres.conf, cgroup.conf, qrmi_config.json, plugstack.conf

# Create docker-compose.yml for c3, c4, q2:
cat > docker-compose.yml << 'EOF'
services:
  c3:
    image: slurm-docker-cluster:25.05.3-dev
    command: ["slurmd", "-N", "c3"]
    hostname: c3
    container_name: c3
    network_mode: host
    extra_hosts:
      - "slurmctld:192.168.4.160"
      - "slurmdbd:192.168.4.160"
    volumes:
      - ./munge.key:/etc/munge/munge.key:ro
      - ./slurm.conf:/etc/slurm/slurm.conf:ro
      - ./cgroup.conf:/etc/slurm/cgroup.conf:ro
      - ./gres.conf:/etc/slurm/gres.conf:ro
      - ./qrmi_config.json:/etc/slurm/qrmi_config.json:ro
      - ./plugstack.conf:/etc/slurm/plugstack.conf:ro
      - /mnt/shared:/shared
      - var_log_c3:/var/log/slurm
    restart: unless-stopped

  c4:
    image: slurm-docker-cluster:25.05.3-dev
    command: ["slurmd", "-N", "c4"]
    hostname: c4
    container_name: c4
    network_mode: host
    extra_hosts:
      - "slurmctld:192.168.4.160"
      - "slurmdbd:192.168.4.160"
    volumes:
      - ./munge.key:/etc/munge/munge.key:ro
      - ./slurm.conf:/etc/slurm/slurm.conf:ro
      - ./cgroup.conf:/etc/slurm/cgroup.conf:ro
      - ./gres.conf:/etc/slurm/gres.conf:ro
      - ./qrmi_config.json:/etc/slurm/qrmi_config.json:ro
      - ./plugstack.conf:/etc/slurm/plugstack.conf:ro
      - /mnt/shared:/shared
      - var_log_c4:/var/log/slurm
    restart: unless-stopped

  q2:
    image: slurm-docker-cluster:25.05.3-dev
    command: ["slurmd", "-N", "q2"]
    hostname: q2
    container_name: q2
    network_mode: host
    extra_hosts:
      - "slurmctld:192.168.4.160"
      - "slurmdbd:192.168.4.160"
    volumes:
      - ./munge.key:/etc/munge/munge.key:ro
      - ./slurm.conf:/etc/slurm/slurm.conf:ro
      - ./cgroup.conf:/etc/slurm/cgroup.conf:ro
      - ./gres.conf:/etc/slurm/gres.conf:ro
      - ./qrmi_config.json:/etc/slurm/qrmi_config.json:ro
      - ./plugstack.conf:/etc/slurm/plugstack.conf:ro
      - /mnt/shared:/shared
      - var_log_q2:/var/log/slurm
    restart: unless-stopped

volumes:
  var_log_c3:
  var_log_c4:
  var_log_q2:
EOF

# Fix munge key ownership
sudo chown 998:998 munge.key

# Start the nodes
docker compose up -d
```

### Usage

```bash
# Check cluster status
docker exec login sinfo

# Run a job on all classical nodes
docker exec login srun -p normal -N4 hostname

# Run a quantum job with QPU resource
docker exec login srun -p quantum --gres=qpu:1 hostname

# Submit an MPI job
docker exec login sbatch /shared/mpi_test.sh

# Access the login node interactively
docker exec -it login bash
```

### MPI Jobs

For MPI jobs across multiple nodes, use `mpirun` inside batch scripts:

```bash
#!/bin/bash
#SBATCH --job-name=mpi_job
#SBATCH --output=/shared/mpi_job.out
#SBATCH --nodes=4
#SBATCH --ntasks=4
#SBATCH --partition=normal

# Get hostfile from Slurm
scontrol show hostnames $SLURM_NODELIST > /tmp/hostfile

# Run with mpirun
mpirun --allow-run-as-root --hostfile /tmp/hostfile -np $SLURM_NTASKS /shared/pyenv/bin/python3 /shared/my_mpi_script.py
```

### Stopping the Cluster

```bash
# On rasqberry
docker compose -f docker-compose-hybrid.yml down

# On rasqberry2
ssh rasqberry2 "cd ~/slurm-remote && docker compose down"

# Or use the script
./deploy-hybrid.sh stop
```

---

## Docker Swarm Deployment (Alternative)

The Docker Swarm approach uses an overlay network but has limitations with MPI across nodes due to NAT.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  rasqberry (Swarm Manager)         │  rasqberry2 (Swarm Worker)         │
│  ├── mysql                         │  ├── c3 (compute)                  │
│  ├── slurmdbd                      │  ├── c4 (compute)                  │
│  ├── slurmctld                     │  └── q2 (quantum)                  │
│  ├── c1, c2 (compute)              │                                    │
│  ├── q1 (quantum)                  │                                    │
│  └── login                         │                                    │
│           │                        │                                |   │
│           └── Docker Swarm Overlay Network (slurm-net) ─────────────┘   |
└─────────────────────────────────────────────────────────────────────────┘
```

### Limitations

- **MPI across hosts fails** due to overlay network NAT
- Jobs using `srun` across rasqberry and rasqberry2 have connectivity issues
- Best for single-host MPI or non-MPI workloads

### Quick Start (Swarm)

```bash
# Initialize swarm (on rasqberry)
docker swarm init --advertise-addr 192.168.4.160

# Join worker (on rasqberry2)
docker swarm join --token <token> 192.168.4.160:2377

# Deploy
./slurm-swarm-deploy.sh --clean
```

### Files for Swarm Deployment

| File | Description |
|------|-------------|
| `docker-stack.yml` | Docker Swarm stack definition |
| `slurm-swarm.conf` | Slurm config for overlay network |
| `gres-swarm.conf` | GRES configuration |
| `docker-entrypoint-swarm.sh` | Custom entrypoint for munge key |
| `slurm-swarm-deploy.sh` | Deployment script |
| `slurm-exec.sh` | Helper script for container access |

---

## Troubleshooting

### Nodes in UNKNOWN State

```bash
# Check if slurmd is running
docker logs c1
ssh rasqberry2 "docker logs c3"

# Verify connectivity from login to compute node
docker exec login bash -c 'echo > /dev/tcp/192.168.4.164/6818 && echo OK'
```

### Munge Authentication Failures

Munge keys get out of sync when containers on rasqberry are recreated (which generates a new key) or when the `deploy-hybrid.sh` script fails partway through.

**Symptoms:**
- Nodes on rasqberry2 show as `unk*` or `NOT_RESPONDING` in `sinfo`
- Container logs show: `Protocol authentication error`

**Diagnose:**
```bash
# Check container logs on rasqberry2
ssh rasqberry2 "docker logs c3 2>&1 | tail -5"

# If you see "Protocol authentication error", resync the key
```

**Manual Munge Key Resync:**
```bash
# 1. Copy the munge key from rasqberry to rasqberry2
sudo cp /var/lib/docker/volumes/rasqberry2_etc_munge/_data/munge.key /tmp/munge.key
sudo chmod 644 /tmp/munge.key
scp /tmp/munge.key rasqberry2:/home/rasqberry/slurm-remote/
ssh rasqberry2 "sudo chown 998:998 /home/rasqberry/slurm-remote/munge.key && sudo chmod 400 /home/rasqberry/slurm-remote/munge.key"
sudo rm /tmp/munge.key

# 2. Restart containers on rasqberry2
ssh rasqberry2 "cd /home/rasqberry/slurm-remote && docker compose restart"

# 3. Verify nodes are back online
docker exec slurmctld sinfo
```

**Other munge checks:**
```bash
# Test munge on a node
docker exec c1 bash -c 'munge -n | unmunge'

# Check munge key ownership on rasqberry2
ssh rasqberry2 "ls -la ~/slurm-remote/munge.key"
# Should be owned by uid 998 (munge user)

# Fix ownership if wrong
ssh rasqberry2 "sudo chown 998:998 ~/slurm-remote/munge.key && sudo chmod 400 ~/slurm-remote/munge.key"
```

### Clock Sync Issues

Munge credentials have a 5-minute TTL (time-to-live). If the clocks on rasqberry and rasqberry2 are out of sync by more than a few minutes, munge authentication will fail with "Expired credential" errors.

**Symptoms:**
- Same as munge authentication failures above
- Cross-node munge test shows `STATUS: Expired credential (15)`
- ENCODE_TIME and DECODE_TIME in unmunge output differ significantly

**Diagnose:**
```bash
# Compare system times
date && ssh rasqberry2 date

# Test cross-node munge (look for "Expired credential" error)
ssh rasqberry2 "docker exec c3 munge -n" | docker exec -i c1 unmunge
```

**Fix clock sync:**
```bash
# Set timezone on both Pis (use same timezone on both!)
sudo timedatectl set-timezone America/New_York
ssh rasqberry2 "sudo timedatectl set-timezone America/New_York"

# Enable NTP for automatic sync
sudo timedatectl set-ntp true
ssh rasqberry2 "sudo timedatectl set-ntp true"

# If NTP doesn't sync quickly, force manual sync from rasqberry to rasqberry2
ssh rasqberry2 "sudo date -s '\$(date +%Y-%m-%dT%H:%M:%S)'"

# Restart containers to pick up correct time
ssh rasqberry2 "cd /home/rasqberry/slurm-remote && docker compose restart"

# Reconfigure SLURM
docker exec slurmctld scontrol reconfigure
```

### NFS Issues

```bash
# Check NFS server status
sudo systemctl status nfs-kernel-server

# Check exports
showmount -e localhost

# Test mount from rasqberry2
ssh rasqberry2 "ls /mnt/shared"

# Remount if needed
ssh rasqberry2 "sudo mount -a"
```

### MPI Connectivity Problems

For MPI to work across nodes:
1. Both nodes must be able to reach each other directly (host networking)
2. Use `mpirun` with hostfile, not `srun` for PMIx
3. Verify nodes can ping each other: `ping 192.168.4.164`

### Port Conflicts

With host networking, each slurmd needs a unique port on the same host:
- c1/c3 use port 6818
- c2/c4 use port 6828
- q1/q2 use port 6838

Check for conflicts:
```bash
# On rasqberry
ss -tlnp | grep -E '681[8]|682[8]|683[8]'

# On rasqberry2
ssh rasqberry2 "ss -tlnp | grep -E '681[8]|682[8]|683[8]'"
```

---

## Comparison: Hybrid vs Swarm

| Aspect | Hybrid | Docker Swarm |
|--------|--------|--------------|
| **MPI Support** | Full (cross-node) | Limited (single-host only) |
| **Networking** | Host + Bridge | Overlay |
| **Complexity** | Lower | Higher |
| **Container isolation** | Less | More |
| **Node scaling** | Manual | Orchestrated |
| **Config distribution** | Manual copy | Docker configs/secrets |
| **Use case** | MPI/HPC workloads | Microservices |

**Recommendation:** Use the Hybrid approach for HPC workloads that require MPI communication between nodes.
