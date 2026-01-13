# QHPC Tutorial
## System Overview

This tutorial assumes you have four classical nodes and two quantum nodes added to your slurm-docker-cluster set up in this [tutorial](https://github.ibm.com/kmcmill/hpc-course-demos/tree/kpm).

Your set up should look something like this: 

| Container | Partition | Deployed On |
|-----------|-----------|-------------|
| c1        | classical | rasqberry   |
| c2        | classical | rasqberry   |
| q1        | quantum   | rasqberry   |
| c3        | classical | rasqberry2  |
| c4        | classical | rasqberry2  |
| q2        | quantum   | rasqberry2  |

---


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
│  └─────────────────────────┘    │  │ - 1 CPUs, 1GB RAM       │              │
│  ┌─────────────────────────┐    │  └─────────────────────────┘              │
│  │ slurmdbd                │    │  ┌─────────────────────────┐              │
│  │ - Database daemon       │    │  │ c4 (slurmd)             │              │
│  │ - Job accounting        │    │  │ - Classical compute     │              │
│  └─────────────────────────┘    │  │ - 1 CPUs, 1GB RAM       │              │
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

## Submitting Simultaneous Jobs via CLI
```shell
sbatch daxpy.sh & sbatch parallel_qpus.sh
watch squeue
```

## Submitting Simultaneous Jobs via Bash Scripting

To really visualize the slurm queue distributing resources and collecting results run the following script and watch yout slurm queue process various quantum and classical workloads

```bash
#!/bin/bash
sbatch --export=ALL,NP=1 /shared/QHPC_Tutorial/parallel_qpus.sh
sbatch --nodes=2 /shared/QHPC_Tutorial/daxpy.sh
sbatch --nodes=4 /shared/QHPC_Tutorial/daxpy.sh
sbatch --export=ALL,NP=2 /shared/QHPC_Tutorial/parallel_qpus.sh
sbatch --nodes=1 /shared/QHPC_Tutorial/daxpy.sh
sbatch --nodes=2 /shared/QHPC_Tutorial/daxpy.sh
sbatch --export=ALL,NP=1 /shared/QHPC_Tutorial/parallel_qpus.sh

echo "All jobs submitted"
```

