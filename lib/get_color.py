import webcolors, cv2
import numpy as np

def closest_colour(requested_colour):
    distances = {}
    for name in webcolors.names():
        r_c, g_c, b_c = webcolors.name_to_rgb(name)
        rd = (r_c - requested_colour[0]) ** 2
        gd = (g_c - requested_colour[1]) ** 2
        bd = (b_c - requested_colour[2]) ** 2
        distances[name] = rd + gd + bd
    return min(distances, key=distances.get)

def get_colour_name(requested_colour):
    try:
        closest_name = actual_name = webcolors.rgb_to_name(requested_colour)
    except ValueError:
        closest_name = closest_colour(requested_colour)
        actual_name = None
    return actual_name, closest_name

def get_common_color(img):
    data = np.reshape(img, (-1,3))
    #print(data.shape)
    data = np.float32(data)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    flags = cv2.KMEANS_RANDOM_CENTERS
    compactness,labels,centers = cv2.kmeans(data,1,None,criteria,10,flags)
    common = centers[0].astype(np.int32)
    return common

def most_common_color_RGB(image: np.ndarray):
    """input image ndarray shape should be RGB shape, for example: (512, 512, 3)"""
    a2D = image.reshape(-1, image.shape[-1])

    col_range = (256, 256, 256)  # generically : a2D.max(0)+1
    a1D = np.ravel_multi_index(a2D.T, col_range)
    return np.unravel_index(np.bincount(a1D).argmax(), col_range)

def most_common_color_RGBA(image_RGBA: np.ndarray):
    """input image ndarray shape should be RGBA shape, for example: (512, 512, 4)"""
    RGB_pixels = image_RGBA.reshape(-1, 4)
    # remove transparent pixels
    just_non_alpha = RGB_pixels[RGB_pixels[:, 3] != 0]
    if just_non_alpha.shape[0] == 0:
        return False
    # delete alpha channel
    just_non_alpha = np.delete(just_non_alpha, 3, axis=1)
    col_range = (256, 256, 256)  # generically : a2D.max(0)+1
    a1D = np.ravel_multi_index(just_non_alpha.T, col_range)
    return np.unravel_index(np.bincount(a1D).argmax(), col_range)

def func(img):
    common = get_common_color(img)
    actual_name, closest_name = get_colour_name((common[2],common[1],common[0]))
    if actual_name is not None:
        return actual_name
    else:
        return closest_name
        
#img = cv2.imread("example.png", cv2.IMREAD_COLOR)
#print(func(img))