# Author: Gael Varoquaux <gael.varoquaux@normalesup.org>, Brian Cheung
# Modified by: Amit Kumar <dtu.amit@gmail.com>
# License: BSD 3 clause
import os
import time

import tqdm


import matplotlib.pyplot as plt
import skimage
from skimage.data import coins
from skimage.transform import rescale as skimage_rescale

from sklearn.feature_extraction import image

from sklearn.cluster import spectral_clustering
from sklearn.utils.fixes import parse_version



# these were introduced in skimage-0.14
if parse_version(skimage.__version__) >= parse_version("0.14"):
    rescale_params = {"anti_aliasing": False}
else:
    rescale_params = {}

beta = 10
eps = 1e-6
LABELLING_METHOD = "discretize"

# Apply spectral clustering (this step goes much faster if you have pyamg
# installed)
N_REGIONS = 25

RESIZE_PROPORTIONS = [0.05, 0.1, 0.2, 0.4, 0.6, 0.8, 1]


def create_image_graph(
        coins,
        filter,
        rescale,
        return_as=None,
        resize_proportion=0.2
):
    # Resize it to 20% of the original size to speed up the processing
    # Applying a Gaussian filter for smoothing prior to down-scaling
    # reduces aliasing artifacts.
    if return_as is None:
        raise ValueError("return_as not specified")
    smoothened_coins = filter(coins, sigma=2)
    # Taking the old array for cucim as we don't need to change cucim to support Array API
    # We'll change skimage to support Array API rather.
    # smoothened_coins = smoothened_coins._array if hasattr(smoothened_coins, '_array') else smoothened_coins
    rescaled_coins = rescale(smoothened_coins, resize_proportion, mode="reflect", **rescale_params)

    # Convert the image into a graph with the value of the gradient on the
    # edges.

    graph = image.img_to_graph(rescaled_coins, return_as=return_as)
    return rescaled_coins, graph


# Take a decreasing function of the gradient: an exponential
# The smaller beta is, the more independent the segmentation is of the
# actual image. For beta=1, the segmentation is close to a voronoi
def set_graph_data(array, graph):
    graph.data = array.exp(-beta * array.asarray(graph.data) / array.std(array.asarray(graph.data))) + eps
    graph.row = array.asarray(graph.row)
    graph.col = array.asarray(graph.col)
    return graph


def plot_(rescaled_coins, xp, labels):
    labels = xp.reshape(labels, rescaled_coins.shape)
    plt.figure(figsize=(5, 5))
    if xp.__name__ == 'cupy.array_api':
        rescaled_coins = rescaled_coins._array.get()
        labels = labels._array.get()
    plt.imshow(rescaled_coins, cmap=plt.cm.gray)
    for l in range(N_REGIONS):
        plt.contour(labels == l, colors=[plt.cm.nipy_spectral(l / float(N_REGIONS))])
    plt.xticks(())
    plt.yticks(())
    return plt


def segmentation(xp, coins, gaussian_filter, return_as, show_plot=False, resize_proportion=0.2):
    print(f"Running segmentation for {xp.__name__.split('.')[0]} for Resize proportion {resize_proportion}")
    rescaled_coins, graph = create_image_graph(
        coins, gaussian_filter, skimage_rescale, return_as=return_as, resize_proportion=resize_proportion
    )
    image_shape = rescaled_coins.shape
    graph = set_graph_data(xp, graph)
    t0 = time.time()
    labels = spectral_clustering(
        graph, n_clusters=N_REGIONS,
        assign_labels=LABELLING_METHOD,
        random_state=42
    )
    t1 = time.time()
    time_taken = t1 - t0
    if show_plot:
        plt = plot_(rescaled_coins, xp, labels)
        title = f"Spectral clustering via {xp}: %s, %.2fs" % (LABELLING_METHOD, (time_taken))
        print(title)
        plt.title(title)
        plt.show()
    return time_taken, image_shape


def run_segmentation_performance(xp, gaussian_filter=None, sparse=None):
    run_times = []
    image_sizes = []
    coins_px = xp.asarray(coins())
    for r_proportion in tqdm.tqdm(RESIZE_PROPORTIONS):
        run_time, image_size = segmentation(
            xp=xp,
            coins=coins_px,
            gaussian_filter=gaussian_filter,
            return_as=sparse.coo_matrix,
            resize_proportion=r_proportion
        )
        run_times.append(run_time)
        image_sizes.append(str(image_size))
    return run_times, image_sizes

def run_both():
    import numpy.array_api as npx
    import cupy.array_api as cpx
    from scipy import sparse as scipy_sparse
    from cupyx.scipy import sparse as cupy_sparse
    from scipy.ndimage import gaussian_filter as scipy_gaussian_filter
    from cupyx.scipy.ndimage import gaussian_filter as cupy_gaussian_filter
    numpy_times, numpy_sizes = run_segmentation_performance(npx,
        gaussian_filter=cupy_gaussian_filter,
        sparse=cupy_sparse)
    cupy_times, cupy_sizes = run_segmentation_performance(cpx,
        gaussian_filter=scipy_gaussian_filter,
        sparse=scipy_sparse)
    
    plot_performance([cupy_times[1:], cupy_sizes[1:], 'cupy'],
                     [numpy_times[1:],  numpy_sizes[1:], 'numpy'])


def plot_performance(data, artifacts_path=None):
    colors = ["green", "blue", "red"]
    xticks = data[0][1]
    artifact_name=''
    for i, times, sizes, label in enumerate(data):
        if sizes != xticks:
            raise ValueError('different image sizes cannot be handled')
        plt.plot(times, color=colors[i % len(colors)], label=label)
        artifact_name += label
        artifact_name += '_vs_'
    artifact_name = artifact_name[:-4] + '.png'

    # x-label
    xi = list(range(len(xticks)))
    plt.xticks(xi, xticks)

    plt.legend()
    plt.ylabel('Time Taken (sec)')
    plt.xlabel('Image Dimension')
    if artifacts_path:
        if not os.path.exists(artifacts_path):
            os.mkdir(artifacts_path)
        plot_path = os.path.join(artifacts_path, artifact_name)
        plt.savefig(plot_path)


if __name__ == '__main__':
    print("Running segmentation performance")
    t1 = time.time()
    run_both()
    print(f"Total Time Taken: {time.time() - t1} sec")
