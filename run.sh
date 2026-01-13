#!/bin/bash

#SBATCH --job-name=parallel-qpus
#SBATCH --output=/shared/QHPC_Tutorial/parallel-qpus.out
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=quantum
#SBATCH --gres=qpu:1
#SBATCH --qpu=ibm_torino,ibm_fez,ibm_kingston

export SLURM_JOB_QPU_RESOURCES=ibm_torino,ibm_fez,ibm_kingston
export SLURM_JOB_QPU_TYPES=qiskit-runtime-service,qiskit-runtime-service,qiskit-runtime-service
export ibm_kingston_QRMI_IBM_QRS_ENDPOINT=https://quantum.cloud.ibm.com/api/v1
export ibm_kingston_QRMI_IBM_QRS_IAM_ENDPOINT=https://iam.cloud.ibm.com
export ibm_kingston_QRMI_IBM_QRS_IAM_APIKEY=ZK_Vb9m4u5mtAQlBURrYx_DxrsxXvRnO_yiHJbD3uEzZ
export ibm_kingston_QRMI_IBM_QRS_SERVICE_CRN=crn:v1:bluemix:public:quantum-computing:us-east:a/266254cf897e4930b0e3cee07ccda7a4:d98d3b96-367b-4d56-85fd-4be372ca3240::
export ibm_fez_QRMI_IBM_QRS_ENDPOINT=https://quantum.cloud.ibm.com/api/v1
export ibm_fez_QRMI_IBM_QRS_IAM_ENDPOINT=https://iam.cloud.ibm.com
export ibm_fez_QRMI_IBM_QRS_IAM_APIKEY=ZK_Vb9m4u5mtAQlBURrYx_DxrsxXvRnO_yiHJbD3uEzZ
export ibm_fez_QRMI_IBM_QRS_SERVICE_CRN=crn:v1:bluemix:public:quantum-computing:us-east:a/266254cf897e4930b0e3cee07ccda7a4:d98d3b96-367b-4d56-85fd-4be372ca3240::
export ibm_torino_QRMI_IBM_QRS_ENDPOINT=https://quantum.cloud.ibm.com/api/v1
export ibm_torinoz_QRMI_IBM_QRS_IAM_ENDPOINT=https://iam.cloud.ibm.com
export ibm_torino_QRMI_IBM_QRS_IAM_APIKEY=ZK_Vb9m4u5mtAQlBURrYx_DxrsxXvRnO_yiHJbD3uEzZ
export ibm_torino_QRMI_IBM_QRS_SERVICE_CRN=crn:v1:bluemix:public:quantum-computing:us-east:a/266254cf897e4930b0e3cee07ccda7a4:d98d3b96-367b-4d56-85fd-4be372ca3240::


# The sourcing may need to change depending you venv name and location
source /shared/pyenv/bin/activate
source ~/.cargo/env

# python qrmi_methods.py
mpirun --allow-run-as-root --oversubscribe -np 2 python parallel_qpus.py
