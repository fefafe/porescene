import h5py
import numpy as np

arrays = {}
f = h5py.File('./data/data-sample-hd5.mat')
for k, v in f.items():
    arrays[k] = np.array(v)

print(arrays)
