#!/bin/bash
# Deploy Slurm cluster with hybrid networking
#
# This setup uses:
#   - Bridge network for control services (mysql, slurmdbd, slurmctld)
#   - Host network for compute nodes (c1-c4, q1-q2) and login for MPI compatibility
#
# Architecture:
#   rasqberry (192.168.4.160):  control services + c1, c2, q1
#   rasqberry2 (192.168.4.164): c3, c4, q2
#
# Port assignments (multiple slurmd on same host):
#   c1: 6818, c2: 6828, q1: 6838 (on rasqberry)
#   c3: 6818, c4: 6828, q2: 6838 (on rasqberry2)
#
# MPI Configuration (IMPORTANT):
#   OpenMPI is configured via environment variables in docker-compose.
#   The containers set OMPI_MCA_btl_tcp_if_include=wlan0 and
#   OMPI_MCA_oob_tcp_if_include=wlan0 to use the WiFi interface.
#   This prevents OpenMPI from using Docker bridge network IPs (172.x.x.x)
#   which are not routable between hosts.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLUSTER_DIR="$SCRIPT_DIR/../slurm-docker-cluster"
RASQBERRY2_HOST="rasqberry2"
RASQBERRY2_REMOTE_DIR="/home/rasqberry/slurm-remote"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Prepare local etc_slurm directory with proper permissions
prepare_configs() {
    log_info "Preparing Slurm configuration files..."

    mkdir -p "$SCRIPT_DIR/etc_slurm"

    # Copy config files - use existing files if CLUSTER_DIR doesn't exist
    cp "$SCRIPT_DIR/slurm-hybrid.conf" "$SCRIPT_DIR/etc_slurm/slurm.conf"
    cp "$SCRIPT_DIR/gres-hybrid.conf" "$SCRIPT_DIR/etc_slurm/gres.conf"

    # Copy additional config files if they exist in CLUSTER_DIR, otherwise keep existing ones
    if [[ -f "$CLUSTER_DIR/cgroup.conf" ]]; then
        cp "$CLUSTER_DIR/cgroup.conf" "$SCRIPT_DIR/etc_slurm/"
    elif [[ ! -f "$SCRIPT_DIR/etc_slurm/cgroup.conf" ]]; then
        log_error "cgroup.conf not found in $CLUSTER_DIR or $SCRIPT_DIR/etc_slurm"
        exit 1
    fi

    if [[ -f "$CLUSTER_DIR/qrmi_config.json" ]]; then
        cp "$CLUSTER_DIR/qrmi_config.json" "$SCRIPT_DIR/etc_slurm/"
    elif [[ ! -f "$SCRIPT_DIR/etc_slurm/qrmi_config.json" ]]; then
        log_error "qrmi_config.json not found in $CLUSTER_DIR or $SCRIPT_DIR/etc_slurm"
        exit 1
    fi

    if [[ -f "$CLUSTER_DIR/plugstack.conf" ]]; then
        cp "$CLUSTER_DIR/plugstack.conf" "$SCRIPT_DIR/etc_slurm/"
    elif [[ ! -f "$SCRIPT_DIR/etc_slurm/plugstack.conf" ]]; then
        log_error "plugstack.conf not found in $CLUSTER_DIR or $SCRIPT_DIR/etc_slurm"
        exit 1
    fi

    # slurmdbd.conf requires special handling - may be owned by uid 990 from previous run
    # Check if we need to restore it from CLUSTER_DIR or if it already exists
    if [[ -f "$CLUSTER_DIR/slurmdbd.conf" ]]; then
        sudo rm -f "$SCRIPT_DIR/etc_slurm/slurmdbd.conf"
        cp "$CLUSTER_DIR/slurmdbd.conf" "$SCRIPT_DIR/etc_slurm/"
    elif [[ ! -f "$SCRIPT_DIR/etc_slurm/slurmdbd.conf" ]]; then
        log_error "slurmdbd.conf not found in $CLUSTER_DIR or $SCRIPT_DIR/etc_slurm"
        exit 1
    fi

    # Set proper ownership for slurmdbd.conf (uid 990 = slurm user in container)
    sudo chown 990:990 "$SCRIPT_DIR/etc_slurm/slurmdbd.conf"
    sudo chmod 600 "$SCRIPT_DIR/etc_slurm/slurmdbd.conf"

    log_ok "Configuration files prepared"
}

# Stop existing deployments
stop_all() {
    log_info "Stopping existing deployments..."

    # Stop Swarm stack if running
    docker stack rm slurm 2>/dev/null || true

    # Stop local compose
    cd "$SCRIPT_DIR"
    docker compose -f docker-compose-hybrid.yml down 2>/dev/null || true

    # Stop on rasqberry2
    ssh "$RASQBERRY2_HOST" "cd $RASQBERRY2_REMOTE_DIR && docker compose down 2>/dev/null" 2>/dev/null || true

    sleep 5
    log_ok "Stopped existing deployments"
}

# Deploy main cluster on rasqberry
deploy_main() {
    log_info "Deploying main cluster on rasqberry..."

    cd "$SCRIPT_DIR"
    docker compose -f docker-compose-hybrid.yml up -d

    # Wait for services to start
    log_info "Waiting for services to initialize..."
    sleep 15

    # Verify
    if docker exec slurmctld sinfo &>/dev/null; then
        log_ok "Main cluster is running"
    else
        log_error "Main cluster failed to start"
        docker compose -f docker-compose-hybrid.yml logs
        exit 1
    fi
}

# Setup and deploy remote nodes on rasqberry2
deploy_remote() {
    log_info "Setting up remote nodes on rasqberry2..."

    # Create remote directory structure
    ssh "$RASQBERRY2_HOST" "mkdir -p $RASQBERRY2_REMOTE_DIR/etc_slurm"

    # Copy munge key from local volume (requires sudo to read)
    log_info "Copying munge key..."
    MUNGE_VOL="/var/lib/docker/volumes/rasqberry2_etc_munge/_data"
    if ! sudo test -f "$MUNGE_VOL/munge.key"; then
        log_error "Could not find munge key at $MUNGE_VOL/munge.key"
        log_info "Make sure main cluster is running."
        exit 1
    fi

    # Remove old munge key if exists
    ssh "$RASQBERRY2_HOST" "sudo rm -f $RASQBERRY2_REMOTE_DIR/munge.key" 2>/dev/null || true

    sudo cp "$MUNGE_VOL/munge.key" /tmp/munge.key
    sudo chmod 644 /tmp/munge.key
    scp /tmp/munge.key "$RASQBERRY2_HOST:$RASQBERRY2_REMOTE_DIR/"
    ssh "$RASQBERRY2_HOST" "sudo chown 998:998 $RASQBERRY2_REMOTE_DIR/munge.key && sudo chmod 400 $RASQBERRY2_REMOTE_DIR/munge.key"
    sudo rm /tmp/munge.key

    # Copy etc_slurm directory (excluding slurmdbd.conf which has restricted permissions)
    log_info "Copying configuration files..."
    scp "$SCRIPT_DIR/etc_slurm/slurm.conf" "$RASQBERRY2_HOST:$RASQBERRY2_REMOTE_DIR/etc_slurm/"
    scp "$SCRIPT_DIR/etc_slurm/gres.conf" "$RASQBERRY2_HOST:$RASQBERRY2_REMOTE_DIR/etc_slurm/"
    scp "$SCRIPT_DIR/etc_slurm/cgroup.conf" "$RASQBERRY2_HOST:$RASQBERRY2_REMOTE_DIR/etc_slurm/"
    scp "$SCRIPT_DIR/etc_slurm/qrmi_config.json" "$RASQBERRY2_HOST:$RASQBERRY2_REMOTE_DIR/etc_slurm/"
    scp "$SCRIPT_DIR/etc_slurm/plugstack.conf" "$RASQBERRY2_HOST:$RASQBERRY2_REMOTE_DIR/etc_slurm/"
    # slurmdbd.conf - use sudo to read
    sudo cat "$SCRIPT_DIR/etc_slurm/slurmdbd.conf" | ssh "$RASQBERRY2_HOST" "cat > $RASQBERRY2_REMOTE_DIR/etc_slurm/slurmdbd.conf"

    # Create docker-compose for remote (c3, c4, q2)
    log_info "Creating remote docker-compose..."
    cat << 'COMPOSE_EOF' | ssh "$RASQBERRY2_HOST" "cat > $RASQBERRY2_REMOTE_DIR/docker-compose.yml"
# Docker Compose for rasqberry2 - Remote compute nodes
# Runs c3, c4, q2 with host networking

services:
  # Classical compute nodes
  c3:
    image: slurm-docker-cluster:25.05.3-dev
    command: ["slurmd", "-N", "c3"]
    hostname: c3
    container_name: c3
    network_mode: host
    environment:
      - OMPI_MCA_btl_tcp_if_include=wlan0
      - OMPI_MCA_oob_tcp_if_include=wlan0
    extra_hosts:
      - "slurmctld:192.168.4.160"
      - "slurmdbd:192.168.4.160"
    volumes:
      - ./munge.key:/etc/munge/munge.key:ro
      - ./etc_slurm:/etc/slurm:ro
      - /mnt/shared:/shared
      - var_log_c3:/var/log/slurm
    restart: unless-stopped

  c4:
    image: slurm-docker-cluster:25.05.3-dev
    command: ["slurmd", "-N", "c4"]
    hostname: c4
    container_name: c4
    network_mode: host
    environment:
      - OMPI_MCA_btl_tcp_if_include=wlan0
      - OMPI_MCA_oob_tcp_if_include=wlan0
    extra_hosts:
      - "slurmctld:192.168.4.160"
      - "slurmdbd:192.168.4.160"
    volumes:
      - ./munge.key:/etc/munge/munge.key:ro
      - ./etc_slurm:/etc/slurm:ro
      - /mnt/shared:/shared
      - var_log_c4:/var/log/slurm
    restart: unless-stopped

  # Quantum node
  q2:
    image: slurm-docker-cluster:25.05.3-dev
    command: ["slurmd", "-N", "q2"]
    hostname: q2
    container_name: q2
    network_mode: host
    environment:
      - OMPI_MCA_btl_tcp_if_include=wlan0
      - OMPI_MCA_oob_tcp_if_include=wlan0
    extra_hosts:
      - "slurmctld:192.168.4.160"
      - "slurmdbd:192.168.4.160"
    volumes:
      - ./munge.key:/etc/munge/munge.key:ro
      - ./etc_slurm:/etc/slurm:ro
      - /mnt/shared:/shared
      - var_log_q2:/var/log/slurm
    restart: unless-stopped

volumes:
  var_log_c3:
  var_log_c4:
  var_log_q2:
COMPOSE_EOF

    # Start remote nodes
    log_info "Starting c3, c4, q2 on rasqberry2..."
    ssh "$RASQBERRY2_HOST" "cd $RASQBERRY2_REMOTE_DIR && docker compose up -d"

    sleep 10
    log_ok "Remote nodes deployed"
}

# Verify cluster
verify_cluster() {
    log_info "Verifying cluster..."

    echo ""
    echo "Cluster status (sinfo):"
    echo "------------------------"
    docker exec login sinfo 2>/dev/null || docker exec slurmctld sinfo

    echo ""
    echo "Node details:"
    echo "-------------"
    docker exec login scontrol show nodes 2>/dev/null || docker exec slurmctld scontrol show nodes
}

# Main
case "${1:-deploy}" in
    deploy)
        echo "=============================================="
        echo "  Slurm Hybrid Cluster Deployment (6 nodes)"
        echo "=============================================="
        echo ""
        echo "Architecture:"
        echo "  rasqberry:  c1, c2, q1 + control services"
        echo "  rasqberry2: c3, c4, q2"
        echo ""
        stop_all
        prepare_configs
        deploy_main
        deploy_remote
        verify_cluster
        echo ""
        echo "=============================================="
        echo "  Deployment Complete"
        echo "=============================================="
        echo ""
        echo "Partitions:"
        echo "  normal:  c1, c2, c3, c4 (classical compute)"
        echo "  quantum: q1, q2 (quantum with QPU GRES)"
        echo ""
        echo "Access the cluster:"
        echo "  docker exec -it login bash"
        echo ""
        echo "Test jobs:"
        echo "  docker exec login srun -p normal -N4 hostname"
        echo "  docker exec login srun -p quantum --gres=qpu:1 hostname"
        echo ""
        echo "MPI Jobs:"
        echo "  OpenMPI is pre-configured in the containers to use wlan0."
        echo "  Just run your MPI jobs normally:"
        echo "    srun --mpi=pmix python3 your_mpi_script.py"
        ;;
    stop)
        stop_all
        ;;
    status)
        verify_cluster
        ;;
    *)
        echo "Usage: $0 [deploy|stop|status]"
        exit 1
        ;;
esac
