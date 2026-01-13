# RasQberry Slurm Cluster Architecture

This document describes the architecture of the Raspberry Pi 5 Slurm HPC cluster with quantum computing capabilities, including the evolution from single-node to multi-node deployment.

## Table of Contents

1. [System Overview](#system-overview)
2. [Container Architecture](#container-architecture)
3. [Network Architecture](#network-architecture)
4. [Phase 1: Base Cluster Deployment (c1, c2)](#phase-1-base-cluster-deployment-c1-c2)
5. [Phase 2: Quantum Node Addition (q1)](#phase-2-quantum-node-addition-q1)
6. [Phase 3: Multi-Node Swarm Deployment (c3, c4, q2)](#phase-3-multi-node-swarm-deployment-c3-c4-q2)

---

## System Overview

The RasQberry cluster is a hybrid classical-quantum HPC system built on Raspberry Pi 5 hardware, using Docker containers to run Slurm workload manager components. The system supports:

- **Classical computing** via standard Slurm compute nodes
- **Quantum computing** via QRMI (Quantum Resource Management Interface) integration
- **MPI parallel jobs** via PMIx and OpenMPI

### Final Architecture (After All Phases)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RASPBERRY PI 5 CLUSTER                            │
├─────────────────────────────────┬───────────────────────────────────────────┤
│  rasqberry (Swarm Manager)      │  rasqberry2 (Swarm Worker)                │
│  ┌─────────────────────────┐    │  ┌─────────────────────────┐              │
│  │ mysql (MariaDB 10.11)   │    │  │ c3 (slurmd)             │              │
│  │ - Slurm accounting DB   │    │  │ - Classical compute     │              │
│  └─────────────────────────┘    │  │ - 4 CPUs, 1GB RAM       │              │
│  ┌─────────────────────────┐    │  └─────────────────────────┘              │
│  │ slurmdbd                │    │  ┌─────────────────────────┐              │
│  │ - Database daemon       │    │  │ c4 (slurmd)             │              │
│  │ - Job accounting        │    │  │ - Classical compute     │              │
│  └─────────────────────────┘    │  │ - 4 CPUs, 1GB RAM       │              │
│  ┌─────────────────────────┐    │  └─────────────────────────┘              │
│  │ slurmctld               │    │  ┌─────────────────────────┐              │
│  │ - Central controller    │    │  │ q2 (slurmd)             │              │
│  │ - Job scheduling        │    │  │ - Quantum compute       │              │
│  │ - Resource management   │    │  │ - QPU GRES resource     │              │
│  └─────────────────────────┘    │  │ - QRMI integration      │              │
│  ┌─────────────────────────┐    │  └─────────────────────────┘              │
│  │ c1 (slurmd)             │    │                                           │
│  │ - Classical compute     │    │                                           │
│  │ - 4 CPUs, 1GB RAM       │    │                                           │
│  └─────────────────────────┘    │                                           │
│  ┌─────────────────────────┐    │                                           │
│  │ c2 (slurmd)             │    │                                           │
│  │ - Classical compute     │    │                                           │
│  │ - 4 CPUs, 1GB RAM       │    │                                           │
│  └─────────────────────────┘    │                                           │
│  ┌─────────────────────────┐    │                                           │
│  │ q1 (slurmd)             │    │                                           │
│  │ - Quantum compute       │    │                                           │
│  │ - QPU GRES resource     │    │                                           │
│  │ - QRMI integration      │    │                                           │
│  └─────────────────────────┘    │                                           │
│  ┌─────────────────────────┐    │                                           │
│  │ login                   │    │                                           │
│  │ - User access point     │    │                                           │
│  │ - Job submission        │    │                                           │
│  └─────────────────────────┘    │                                           │
├─────────────────────────────────┴───────────────────────────────────────────┤
│                    Docker Swarm Overlay Network (slurm-net)                 │
│                              10.0.1.0/24                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Container Architecture

### Container Purposes

| Container | Daemon | Purpose |
|-----------|--------|---------|
| **mysql** | MariaDB | Stores Slurm accounting data (jobs, users, associations) |
| **slurmdbd** | slurmdbd | Slurm Database Daemon - interfaces between slurmctld and MySQL |
| **slurmctld** | slurmctld | Central controller - schedules jobs, manages resources |
| **c1, c2, c3, c4** | slurmd | Classical compute nodes - execute batch jobs |
| **q1, q2** | slurmd | Quantum compute nodes - execute quantum jobs via QRMI |
| **login** | (none) | User login node - job submission, no computation |

### Container Image

All Slurm containers use the same Docker image: `slurm-docker-cluster:25.05.3-dev`

**Base:** Rocky Linux 9

**Key Components:**
- Slurm 25.05.3 (built from source with `--with-pmix` and `--with-hwloc`)
- PMIx 4.2.9 (Process Management Interface for Exascale)
- OpenMPI 4.1.6 (with Slurm and PMIx support)
- Munge authentication
- Python 3.12 with virtual environment support
- QRMI SPANK plugin for quantum resource management

### Slurm Partitions

| Partition | Nodes | Default | Description |
|-----------|-------|---------|-------------|
| `normal` | c1, c2, c3, c4 | No | Classical compute jobs |
| `quantum` | q1, q2 | Yes | Quantum jobs requiring QPU GRES |

### GRES (Generic Resources)

Quantum nodes advertise a `qpu` (Quantum Processing Unit) resource:

```
# gres.conf
NodeName=q1 Name=qpu Count=1
NodeName=q2 Name=qpu Count=1
```

Jobs request quantum resources via:
```bash
sbatch --gres=qpu:1 -p quantum job.sh
```

---

## Network Architecture

### Phase 1-2: Docker Compose (Single Host)

```
┌─────────────────────────────────────────┐
│           rasqberry (single host)       │
│  ┌───────────────────────────────────┐  │
│  │   Docker Bridge Network           │  │
│  │   slurm-network (172.x.x.0/24)    │  │
│  │                                   │  │
│  │mysql ◄──► slurmdbd ◄──► slurmctld |  │
│  │                 │                 │  │
│  │     ┌───────────┼───────────┐     │  │
│  │     ▼           ▼           ▼     │  │
│  │    c1          c2          q1     │  │
│  │     ▲           ▲           ▲     │  │
│  │     └───────────┴───────────┘     │  │
│  │                 │                 │  │
│  │               login               │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

- All containers on same Docker bridge network
- Communication via container names (Docker DNS)
- Shared volumes for `/etc/munge`, `/etc/slurm`, `/data`

### Phase 3: Docker Swarm (Multi-Host)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Docker Swarm Overlay Network                    │
│                        slurm-net (10.0.1.0/24)                      │
│                                                                     │
│    ┌─────────────────────┐          ┌─────────────────────┐         │
│    │     rasqberry       │          │     rasqberry2      │         │
│    │  (Swarm Manager)    │          │   (Swarm Worker)    │         │
│    │                     │          │                     │         │
│    │  mysql, slurmdbd    │◄────────►│  c3, c4, q2         │         │
│    │  slurmctld          │  VXLAN   │                     │         │
│    │  c1, c2, q1, login  │  Tunnel  │                     │         │
│    │                     │          │                     │         │
│    └─────────────────────┘          └─────────────────────┘         │
│             │                                │                      │
│             └────────────────────────────────┘                      │
│                    Physical Network (WiFi/Ethernet)                 │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Differences:**
- Overlay network spans multiple hosts via VXLAN tunneling
- Docker configs/secrets distribute configuration (not shared volumes)
- Placement constraints determine which node runs each service
- All containers can communicate regardless of physical host
- NFS shares the `/shared` directory (SPANK plugin, Python env) across hosts
- Custom entrypoint handles munge key permission issues with Docker secrets

---

## Phase 1: Base Cluster Deployment (c1, c2)

**Source:** [INSTALL.md from spank-plugins repository](https://github.com/qiskit-community/spank-plugins/blob/main/demo/qrmi/slurm-docker-cluster/INSTALL.md)

### Overview

This phase establishes the base Slurm cluster with classical compute capability using Docker Compose on a single Raspberry Pi 5.

### Steps

#### 1. Clone Repositories

```bash
mkdir -p <workspace>
cd <workspace>
git clone -b 0.9.0 https://github.com/giovtorres/slurm-docker-cluster.git
cd slurm-docker-cluster
mkdir shared
cd shared
git clone https://github.com/qiskit-community/spank-plugins.git
git clone https://github.com/qiskit-community/qrmi.git
```

#### 2. Apply Configuration Patches

```bash
patch -p1 < ./shared/spank-plugins/demo/qrmi/slurm-docker-cluster/file.patch
```

The patch modifies:
- `docker-compose.yml` - Container definitions
- `slurm.conf` - Slurm configuration
- `Dockerfile` - Container image build

#### 3. Build Docker Images

```bash
docker compose build --no-cache
```

This builds the `slurm-docker-cluster` image containing:
- Rocky Linux 9 base
- Slurm 25.x compiled from source
- Munge authentication
- Python 3.12 environment

#### 4. Start the Cluster

```bash
docker compose up -d
```

**Containers started:**
| Container | Purpose |
|-----------|---------|
| mysql | MariaDB database for Slurm accounting |
| slurmdbd | Slurm database daemon |
| slurmctld | Slurm controller daemon |
| c1 | Compute node 1 |
| c2 | Compute node 2 |
| login | User login node |

#### 5. Build QRMI and SPANK Plugin

From within the c1 container:

```bash
docker exec -it c1 bash

# Create Python environment
python3.12 -m venv /shared/pyenv
source /shared/pyenv/bin/activate
pip install --upgrade pip

# Build QRMI
source ~/.cargo/env
cd /shared/qrmi
pip install -r requirements-dev.txt
maturin build --release
pip install /shared/qrmi/target/wheels/qrmi-*.whl

# Build SPANK plugin
cd /shared/spank-plugins/plugins/spank_qrmi
mkdir build && cd build
cmake ..
make
```

#### 6. Configure Plugin

Create `/etc/slurm/plugstack.conf`:
```
optional /shared/spank-plugins/plugins/spank_qrmi/build/spank_qrmi.so /etc/slurm/qrmi_config.json
```

### Result After Phase 1

```
PARTITION  AVAIL  NODES  STATE  NODELIST
normal*    up     2      idle   c[1-2]
```

- 2 classical compute nodes (c1, c2)
- QRMI plugin available but no quantum nodes yet
- Single `normal` partition

---

## Phase 2: Quantum Node Addition (q1)

**Source:** `/home/rasqberry/QCSC/hpc-course-demos/source/q1_container.sh`

### Overview

This phase adds the first quantum compute node (q1) and configures MPI support for parallel quantum workloads.

### What the Script Does

#### 1. Dockerfile Modifications

The script modifies the Dockerfile to add:

**PMIx Build (Process Management Interface for Exascale):**
```dockerfile
ARG MY_PMIX_VERSION=4.2.9
RUN cd /tmp \
    && wget https://github.com/openpmix/openpmix/releases/download/v${MY_PMIX_VERSION}/pmix-${MY_PMIX_VERSION}.tar.gz \
    && tar xzf pmix-${MY_PMIX_VERSION}.tar.gz \
    && cd pmix-${MY_PMIX_VERSION} \
    && ./configure --prefix=/usr --libdir=/usr/lib64 --with-libevent --with-hwloc \
    && make -j$(nproc) && make install
```

**OpenMPI Build (with Slurm/PMIx integration):**
```dockerfile
ARG OPENMPI_VERSION=4.1.6
RUN cd /tmp \
    && wget https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-${OPENMPI_VERSION}.tar.gz \
    && ./configure --prefix=/usr/local --with-pmix=/usr --with-slurm --with-hwloc \
    && make -j$(nproc) && make install
```

**Slurm Build Modification:**
```
--with-pmix=/usr --with-hwloc
```

#### 2. slurm.conf Updates

```conf
# MPI configuration
MpiDefault=pmix

# GRES (Generic Resource) for quantum
GresTypes=qpu

# Quantum node definition
NodeName=q1 CPUs=1 RealMemory=1000 CoresPerSocket=1 Gres=qpu:1 State=UNKNOWN

# Partitions
PartitionName=normal Default=NO Nodes=c[1-2] ...
PartitionName=quantum Default=YES Nodes=q1 MaxTime=INFINITE State=UP
```

#### 3. gres.conf Creation

```conf
# GRES Configuration for Quantum Queue
NodeName=q1 Name=qpu Count=1
```

#### 4. docker-compose.yml Update

Adds q1 service:
```yaml
q1:
  image: slurm-docker-cluster:${IMAGE_TAG}
  command: ["slurmd"]
  hostname: q1
  container_name: q1
  volumes:
    - etc_munge:/etc/munge
    - etc_slurm:/etc/slurm
    - slurm_jobdir:/data
    - var_log_q1:/var/log/slurm
    - ./shared:/shared
  depends_on:
    - slurmctld
  networks:
    - slurm-network
```

#### 5. Container Operations

```bash
# Rebuild image with PMIx/OpenMPI
docker compose build --no-cache
docker compose down
docker compose up -d

# Copy updated configs
docker cp slurm.conf slurmctld:/etc/slurm/slurm.conf
docker cp slurm.conf c1:/etc/slurm/slurm.conf
docker cp slurm.conf c2:/etc/slurm/slurm.conf

# Start q1 and reconfigure
docker compose up -d q1
docker exec slurmctld scontrol reconfigure
```

### Result After Phase 2

```
PARTITION  AVAIL  NODES  STATE  NODELIST
normal     up     2      idle   c[1-2]
quantum*   up     1      idle   q1
```

- 2 classical nodes + 1 quantum node
- MPI support via PMIx/OpenMPI
- `quantum` partition with QPU GRES
- QRMI SPANK plugin for quantum job submission

---

## Phase 3: Multi-Node Swarm Deployment (c3, c4, q2)

**Source:** `/home/rasqberry/QCSC/hpc-course-demos/source/rasqberry2/slurm-swarm-deploy.sh`

### Overview

This phase extends the cluster to a second Raspberry Pi 5 (rasqberry2) using Docker Swarm, adding 2 more classical nodes and 1 quantum node.

### Prerequisites

1. **Docker Swarm Initialization:**
   ```bash
   # On rasqberry (manager)
   docker swarm init --advertise-addr <rasqberry-ip>

   # On rasqberry2 (worker)
   docker swarm join --token <token> <rasqberry-ip>:2377
   ```

2. **Docker Image on Both Nodes:**
   ```bash
   # Build on rasqberry
   docker build -t slurm-docker-cluster:25.05.3-dev .

   # Copy to rasqberry2
   docker save slurm-docker-cluster:25.05.3-dev | ssh rasqberry2 "docker load"
   ```

3. **NFS Server for /shared Directory:**
   ```bash
   # Setup NFS (one-time)
   ./slurm-swarm-deploy.sh --setup-nfs
   ```

   This exports the `/shared` directory from rasqberry so that all containers (including those on rasqberry2) can access the SPANK plugin and Python environment.

### What the Script Does

#### 1. Check Prerequisites

```bash
# Verify Swarm is active
docker info | grep "Swarm: active"

# Verify rasqberry2 is in swarm
docker node ls | grep rasqberry2
```

#### 2. Create Overlay Network

```bash
docker network create \
    --driver overlay \
    --attachable \
    --subnet 10.0.1.0/24 \
    slurm-net
```

The overlay network:
- Spans both physical hosts
- Uses VXLAN encapsulation
- Provides DNS-based service discovery
- All containers see each other regardless of host

#### 3. Create Docker Secret (Munge Key)

```bash
# Extract existing key or generate new
dd if=/dev/urandom bs=1 count=1024 > /tmp/munge.key
docker secret create munge_key /tmp/munge.key
```

Docker secrets:
- Encrypted at rest
- Automatically distributed to swarm nodes
- Mounted read-only in containers
- Ensures all nodes have identical munge key

#### 4. Deploy Stack

Uses `docker-stack.yml` which defines:

**Services with Placement Constraints:**
```yaml
# On rasqberry
slurmctld:
  deploy:
    placement:
      constraints:
        - node.hostname == rasqberry

# On rasqberry2
c3:
  deploy:
    placement:
      constraints:
        - node.hostname == rasqberry2
```

**Custom Entrypoint for Munge Key Handling:**

Docker secrets are mounted read-only with root ownership, but munge requires the key owned by the munge user. The `docker-entrypoint-swarm.sh` script solves this:

```yaml
# Each service uses custom entrypoint
slurmctld:
  entrypoint: ["/bin/bash", "/entrypoint-swarm.sh"]
  command: ["slurmctld"]
  configs:
    - source: entrypoint
      target: /entrypoint-swarm.sh
      mode: 0755
```

The entrypoint copies the munge key to a writable location with correct ownership before starting services.

**Docker Configs (distributed across swarm):**
```yaml
configs:
  slurm_conf:
    file: ./slurm-swarm.conf
  gres_conf:
    file: ./gres-swarm.conf
  slurmdbd_conf:
    file: ../slurm-docker-cluster/slurmdbd.conf
  cgroup_conf:
    file: ../slurm-docker-cluster/cgroup.conf
  qrmi_conf:
    file: ../slurm-docker-cluster/qrmi_config.json
  plugstack_conf:
    file: ../slurm-docker-cluster/plugstack.conf
  entrypoint:
    file: ./docker-entrypoint-swarm.sh
```

**NFS Volume for /shared:**
```yaml
volumes:
  shared:
    driver: local
    driver_opts:
      type: nfs
      o: addr=192.168.4.160,rw,nolock,soft  # Use IP address, not hostname
      device: ":/home/rasqberry/QCSC/hpc-course-demos/source/slurm-docker-cluster/shared"
```

**Important:** The NFS address must use rasqberry's IP address (not hostname) because rasqberry2 may not be able to resolve the hostname via DNS.

All Slurm services mount `shared:/shared` to access the SPANK plugin and Python environment.

#### 5. slurm-swarm.conf Differences

Key differences from docker-compose slurm.conf:

```conf
# No NodeAddr - uses DNS via overlay network
NodeName=c[1-2] CPUs=4 RealMemory=1000 State=UNKNOWN
NodeName=c[3-4] CPUs=4 RealMemory=1000 State=UNKNOWN
NodeName=q1 CPUs=1 RealMemory=1000 CoresPerSocket=1 Gres=qpu:1 State=UNKNOWN
NodeName=q2 CPUs=1 RealMemory=1000 CoresPerSocket=1 Gres=qpu:1 State=UNKNOWN

# Updated partitions
PartitionName=normal Default=NO Nodes=c[1-4] ...
PartitionName=quantum Default=YES Nodes=q[1-2] ...

# Auto-return nodes when they reconnect
ReturnToService=2
```

#### 6. Wait and Verify

```bash
# Wait for all services
docker service ls --filter "name=slurm"

# Verify Slurm
docker exec <slurmctld> sinfo
docker exec <slurmctld> scontrol show nodes
```

### Result After Phase 3

```
PARTITION  AVAIL  NODES  STATE  NODELIST
normal     up     4      idle   c[1-4]
quantum*   up     2      idle   q[1-2]
```

**Service Distribution:**

| Host | Services |
|------|----------|
| rasqberry | mysql, slurmdbd, slurmctld, c1, c2, q1, login |
| rasqberry2 | c3, c4, q2 |

---

## Configuration Files Summary

| File | Location | Purpose |
|------|----------|---------|
| `docker-compose.yml` | slurm-docker-cluster/ | Single-node deployment (Phase 1-2) |
| `docker-stack.yml` | rasqberry2/ | Multi-node Swarm deployment (Phase 3) |
| `docker-entrypoint-swarm.sh` | rasqberry2/ | Custom entrypoint for munge key handling |
| `slurm-swarm-deploy.sh` | rasqberry2/ | Deployment automation script |
| `slurm.conf` | slurm-docker-cluster/ | Original Slurm config |
| `slurm-swarm.conf` | rasqberry2/ | Swarm-optimized Slurm config |
| `gres.conf` | (generated) | Single-node GRES config |
| `gres-swarm.conf` | rasqberry2/ | Multi-node GRES config |
| `slurmdbd.conf` | slurm-docker-cluster/ | Database daemon config |
| `cgroup.conf` | slurm-docker-cluster/ | Cgroup settings |
| `qrmi_config.json` | slurm-docker-cluster/ | QRMI quantum backend config |
| `plugstack.conf` | slurm-docker-cluster/ | SPANK plugin configuration |

---

## Job Submission Examples

### Classical Job (any node)

```bash
srun -N 2 -p normal hostname
sbatch -N 4 -p normal my_classical_job.sh
```

### Quantum Job

```bash
# Request QPU resource
srun -p quantum --gres=qpu:1 hostname
sbatch -p quantum --gres=qpu:1 quantum_job.sh

# Using QRMI SPANK plugin
sbatch --qpu=ibm_brisbane quantum_circuit.sh
```

### MPI Job

```bash
srun -N 4 -p normal --mpi=pmix mpi_program
```

---

## Technical Challenges and Solutions

### Challenge 1: Munge Key Permissions with Docker Secrets

**Problem:** Docker secrets are mounted read-only with root ownership (uid 0, gid 0). Munge requires the key file to be owned by the munge user (uid 998) with mode 0400.

**Error:**
```
munged: Error: Keyfile is insecure: "/etc/munge/munge.key" should be owned by UID 998
```

**Solution:** Created `docker-entrypoint-swarm.sh` that:
1. Copies the munge key from the secret mount to `/var/lib/munge/munge.key`
2. Sets ownership to `munge:munge`
3. Sets permissions to `0400`
4. Starts munged with `--key-file=/var/lib/munge/munge.key`

### Challenge 2: slurmdbd.conf Permissions

**Problem:** The `slurmdbd.conf` file contains database credentials and must be readable only by the slurm user (uid 990). Docker configs default to root ownership.

**Error:**
```
error: s_p_parse_file: unable to read "/etc/slurm/slurmdbd.conf": Permission denied
```

**Solution:** Specify uid/gid in the config mount:
```yaml
configs:
  - source: slurmdbd_conf
    target: /etc/slurm/slurmdbd.conf
    uid: "990"
    gid: "990"
    mode: 0600
```

### Challenge 3: Shared /shared Directory Across Hosts

**Problem:** The `/shared` directory contains the SPANK plugin and Python environment. Docker Compose uses bind mounts, but these don't work across hosts in Docker Swarm.

**Solution:** NFS-based shared storage:
1. Install NFS server on rasqberry: `./slurm-swarm-deploy.sh --setup-nfs`
2. Export the shared directory in `/etc/exports`
3. Define NFS volume in `docker-stack.yml`:
```yaml
volumes:
  shared:
    driver: local
    driver_opts:
      type: nfs
      o: addr=192.168.4.160,rw,nolock,soft  # Use IP, not hostname
      device: ":/home/rasqberry/QCSC/hpc-course-demos/source/slurm-docker-cluster/shared"
```

### Challenge 4: NFS Hostname Resolution

**Problem:** When using `addr=rasqberry` in the NFS volume definition, rasqberry2 fails to mount with:
```
error resolving passed in network volume address: lookup rasqberry on 10.42.0.1:53: no such host
```

**Solution:** Use rasqberry's IP address instead of hostname:
```yaml
o: addr=192.168.4.160,rw,nolock,soft
```

**Note:** After changing the volume definition, you must remove the cached volume on rasqberry2:
```bash
docker stack rm slurm
ssh rasqberry2 "docker volume rm slurm_shared"
```

### Challenge 5: Service Discovery Across Hosts

**Problem:** In docker-compose, containers communicate via container names on a bridge network. In Swarm, containers may be on different hosts.

**Solution:** Docker Swarm overlay network with DNS:
- Overlay network (`slurm-net`) spans all swarm nodes
- Uses VXLAN tunneling for cross-host communication
- Built-in DNS resolves service names to container IPs
- No `NodeAddr` needed in slurm.conf - DNS handles resolution
