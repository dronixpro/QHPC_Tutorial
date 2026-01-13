from mpi4py import MPI
import numpy as np
import time

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

N = 10000000
a = 50

if rank == 0:
    x = np.arange(N, dtype = 'd')
    y = np.ones(N, dtype = 'd')
else:
    x = None
    y = None

local_n = N // size

local_x = np.empty(local_n, dtype = 'd')
local_y = np.empty(local_n, dtype = 'd')


comm.Scatter(x, local_x, root = 0)
comm.Scatter(y, local_y, root = 0)

n = 1000
start = time.time()
for i in range(n):
    local_y = a * local_x + local_y
    # print(f"Rank {rank} - Iteration {i+1}/{n}", flush=True)
comm.Gather(local_y, y, root= 0)
stop = time.time()

if rank == 0:
    print(y)
    print(f"Total Time with {size} ranks: {stop-start}")