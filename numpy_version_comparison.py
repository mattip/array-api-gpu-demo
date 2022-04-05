#! /bin/env/python3

import subprocess
import sys

import numpy as np
from scipy import sparse as scipy_sparse
from scipy.ndimage import gaussian_filter as scipy_gaussian_filter

import segmentation_performance
# Shorten the run
segmentation_performance.RESIZE_PROPORTIONS = segmentation_performance.RESIZE_PROPORTIONS[:-4]
nPts = len(segmentation_performance.RESIZE_PROPORTIONS)


def run_benchmark():
    data = segmentation_performance.run_segmentation_performance(
        np,
        gaussian_filter=scipy_gaussian_filter,
        sparse=scipy_sparse,
    )
    print('x' * 30)
    print(data)


def main():
    np_versions = ('1.18.0', '1.19.0', '1.20.0', '1.21.0', '1.22.0')
    data = np.empty([len(np_versions)],
                    dtype=[('times', 'f4', [nPts]),
                           # ('sizes', 'U10', [nPts]),
                           ('np_ver', 'U8')])
    for i, version in enumerate(np_versions):
        install_cmd = [sys.executable, '-m', 'pip', 'install', 'numpy==%s' % version]
        subprocess.check_call(install_cmd)
        print(f"Calling 'run_benchmark' with numpy {version}")
        print("*" * 20)
        bench_cmd = [sys.executable, "-c", "from {0} import run_benchmark; run_benchmark()".format(__file__.split('.')[0])]
        # print('running', bench_cmd)
        output = subprocess.check_output(bench_cmd, universal_newlines=True)
        print("*" * 20)
        # Split and take the last line
        results = eval(output.split('\n')[-2])
        data[i][0] = results[0]
        # data[i][1] = results[1]
        data[i][-1] = version

    print(data)

if __name__ == '__main__':
    main()
