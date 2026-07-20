import numpy as np

def trimmed_mean(coords, proportiontocut):  
    coords = np.array(coords)
    n = coords.shape[0]
    trim_count = int(n * proportiontocut)
    result = np.zeros(3)    
  
    for dim in range(3):     
        sorted_vals = np.sort(coords[:, dim])
        trimmed_vals = sorted_vals[trim_count:n - trim_count]
        result[dim] = np.mean(trimmed_vals) if len(trimmed_vals) > 0 else 0
    
    return result