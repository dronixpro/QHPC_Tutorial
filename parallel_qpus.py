import numpy as np
from dotenv import load_dotenv
import qiskit.transpiler.target as Target
from qiskit.circuit.library import efficient_su2
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qrmi.primitives import QRMIService
from qrmi.primitives.ibm import SamplerV2, get_target
from mpi4py import MPI

def create_pub(target : Target):
    # Create a circuit - You need at least one circuit as the input to the Sampler primitive.
    circuit = efficient_su2(127, entanglement="linear")
    circuit.measure_all()
    # The circuit is parametrized, so we will define the parameter values for execution
    param_values = np.random.rand(circuit.num_parameters)

    # The circuit and observable need to be transformed to only use instructions
    # supported by the QPU (referred to as instruction set architecture (ISA) circuits).
    # We'll use the transpiler to do this.
    pm = generate_preset_pass_manager(
        optimization_level=1,
        target=target,
    )
    isa_circuit = pm.run(circuit)
    pub = (isa_circuit, param_values)
    return pub

if __name__ == "__main__":
    num_processes = 2
    
    service = QRMIService()
    resources = service.resources()
    
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    
    load_dotenv()

    if rank < num_processes:
        qrmi = resources[rank]
        print(qrmi.metadata())
        # Generate transpiler target from backend configuration & properties
        target = get_target(qrmi)
        pub = create_pub(target)
        # Initialize QRMI Sampler
        options = {
            "default_shots": 10000,
        }
        sampler = SamplerV2(qrmi, options=options)

        # Next, invoke the run() method to generate the output. The circuit and optional
        # parameter value sets are input as primitive unified bloc (PUB) tuples.
        job = sampler.run([pub])
        print(f">>> Job ID: {job.job_id()}")
        print(f">>> Job Status: {job.status()}")
        result = job.result()[0].data.meas.get_counts()
    else:
        result = None

    results = comm.gather(result, root=0)

    if rank == 0:
        print("All tasks completed.")

        # Calculate fidelity
        all_keys = sorted(set(results[0].keys()).union(results[0].keys()))
        
        counts_0 = np.array([results[0].get(k, 0) for k in all_keys], dtype=float)
        counts_1 = np.array([results[1].get(k, 0) for k in all_keys], dtype=float)
        
        fidelity = (np.sum(np.sqrt(counts_0 * counts_1)) / np.sum(counts_0)) ** 2

        print("Circuit Fidelity:", fidelity)