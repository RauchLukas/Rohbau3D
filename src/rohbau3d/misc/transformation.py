# date: 2026-01-28
# author: lukas rauch

from email.policy import default
import numpy as np
from PIL import Image
from matplotlib.pyplot import cm

def euclidean_distance(point, vector):
    """
    Calculate the Euclidean distance between a point and a vector of points.
    
    Parameters:
        point: tuple or array-like, shape (3,)
            Coordinates of the point (x, y, z).
        vector: array-like, shape (n, 3)
            Vector of points with coordinates (x, y, z).
    
    Returns:
        distances: array-like, shape (n,)
            Array containing the Euclidean distances between the point and each point in the vector.
    """
    point = np.array(point)
    vector = np.array(vector)
    
    # Calculate the Euclidean distance using numpy.linalg.norm
    distances = np.linalg.norm(vector - point, axis=1)
    
    return distances


def normals_to_rgb(normals):
    """
    Converts an array of normal vectors to RGB colors.

    Parameters:
    - normals (np.ndarray): Array of shape (N, 3) where N is the number of normals, 
      and each normal is [nx, ny, nz] with values between -1 and 1.

    Returns:
    - rgb (np.ndarray): Array of shape (N, 3) with values between 0 and 255 (RGB format).
    """
    # Ensure normals are numpy array
    normals = np.array(normals)
    
    # Map normals from [-1, 1] to [0, 1] by using (normals + 1) / 2
    rgb = (normals + 1) / 2
    
    # Scale to [0, 255] for RGB values
    rgb = np.clip(rgb * 255, 0, 255).astype(np.uint8)
    
    return rgb


class SphericalProjection:

    def __init__(self, coord, color=None, intensity=None, normal=None, segment=None, instance=None):
        self.coord = coord
        self.color = color
        self.intensity = intensity
        self.normal = normal
        self.segment = segment
        self.instance = instance
    

    def intensity_image(self, upscale=8, img_ratio=(3, 1), crop=True):

        if self.intensity is None:
            raise ValueError("intensity information is missing.")
        
        px, py, pz = self.coord[:, 0], self.coord[:, 1], self.coord[:, 2]
        r = euclidean_distance([0, 0, 0], self.coord)

        w = int(256 * img_ratio[0] * upscale)
        h = int(256 * img_ratio[1] * upscale)

        u = self.get_u(px, py, w=w)
        v = self.get_v(pz, radius=r, fup=90, fdw=90, h=h)

        # Apply viridis colormap
        colormap = cm.get_cmap('gray')
        rgb_color = colormap(self.intensity)[:, :3]  # Extract RGB channels, ignore alpha

        image, mask = self.assemble_image_rgba(u, v, rgb_color, h, w)

        colored_image = (image).astype(np.uint8)
        pil_image = Image.fromarray(colored_image, mode='RGBA')

        if crop:
            pil_image = self.crop_empty_borders(pil_image, mask)

        return pil_image
    
    
    def depth_image(self, normalize, upscale=8, img_ratio=(3, 1), crop=False):
    
        px, py, pz = self.coord[:, 0], self.coord[:, 1], self.coord[:, 2]
        r = euclidean_distance([0, 0, 0], self.coord)

        w = int(256 * img_ratio[0] * upscale)
        h = int(256 * img_ratio[1] * upscale)

        u = self.get_u(px, py, w=w)
        v = self.get_v(pz, radius=r, fup=90, fdw=90, h=h)


        if normalize:
            r = np.asarray(r, dtype=np.float32) / r.max()
        else:
            r = np.asarray(r, dtype=np.float32)

        # Apply viridis colormap
        colormap = cm.get_cmap('viridis_r')
        rgb_color = colormap(r)[:, :3]  # Extract RGB channels, ignore alpha

        image, mask = self.assemble_image_rgba(u, v, rgb_color, h, w)

        colored_image = (image).astype(np.uint8)
        pil_image = Image.fromarray(colored_image, mode='RGBA')

        if crop:
            pil_image = self.crop_empty_borders(pil_image, mask)

        return pil_image


    def color_image(self, upscale=8, img_ratio=(3, 1), crop=True):

        if self.color is None:
            raise ValueError("Color information is missing.")

        px, py, pz = self.coord[:, 0], self.coord[:, 1], self.coord[:, 2]
        r = euclidean_distance([0, 0, 0], self.coord)

        w = int(256 * img_ratio[0] * upscale)
        h = int(256 * img_ratio[1] * upscale)

        u = self.get_u(px, py, w=w)
        v = self.get_v(pz, radius=r, fup=90, fdw=90, h=h)

        image, mask = self.assemble_image_rgba(u, v, self.color/255, h, w)

        colored_image = (image).astype(np.uint8)
        pil_image = Image.fromarray(colored_image, mode='RGBA')

        if crop:
            pil_image = self.crop_empty_borders(pil_image, mask)

        return pil_image
    
    
    def normal_image(self, upscale=8, img_ratio=(3, 1), default_color=[0, 0, 0], crop=True, normalize=True):
        if self.normal is None:
            raise ValueError("Normal information is missing.")
        
        px, py, pz = self.coord[:, 0], self.coord[:, 1], self.coord[:, 2]
        r = euclidean_distance([0, 0, 0], self.coord)

        w = int(256 * img_ratio[0] * upscale)
        h = int(256 * img_ratio[1] * upscale)

        u = self.get_u(px, py, w=w)
        v = self.get_v(pz, radius=r, fup=90, fdw=90, h=h)

        color = normals_to_rgb(self.normal)

        image, mask = self.assemble_image_rgba(u, v, color/255, h, w)

        colored_image = (image).astype(np.uint8)
        pil_image = Image.fromarray(colored_image, mode='RGBA')

        if crop:
            pil_image = self.crop_empty_borders(pil_image, mask)

        return pil_image


    @staticmethod
    def crop_empty_borders(image, mask, threshold=0.999): 
        """
        Crop the image to remove empty borders based on a binary mask.
        """

        # Ensure the mask is 2D and binary (0 or 1)
        assert len(mask.shape) == 2, "Mask should be a 2D array."
        assert image.size[0] == mask.shape[1], "Mask width must match image width."

        # Calculate the proportion of zeros in each row
        row_zero_proportion = np.mean(mask == 0, axis=1)

        # Find rows to keep (where less than threshold are zeros)
        rows_to_keep = row_zero_proportion < threshold

        # Initialize top and bottom rows to crop
        top = 0
        bottom = len(rows_to_keep)

        # Find the first row from the top where rows should be kept
        for i, keep in enumerate(rows_to_keep):
            if keep:
                top = i
                break

        # Find the first row from the bottom where rows should be kept
        for i, keep in enumerate(reversed(rows_to_keep)):
            if keep:
                bottom = len(rows_to_keep) - i
                break

        # Crop the image
        cropped_image = image.crop((0, top, image.size[0], bottom))
        return cropped_image



    @staticmethod
    def get_u(x, y, w=1200):
        return (0.5 * (1 - np.arctan2(y, x) / np.pi) * (w - 1)).astype(int)

    @staticmethod
    def get_v(z, radius, fup=90, fdw=90, h=800):
        fup = fup * np.pi / 180
        fdw = fdw * np.pi / 180
        f = fup + fdw

        phi = np.arcsin(z / radius)
        assert abs(phi.max()) <= fup, "Point is outside the field of view :: fup"
        assert abs(phi.min()) <= fdw, "Point is outside the field of view :: fdw"

        return ((1 - (phi + fdw) / f) * (h - 1)).astype(int)

    @staticmethod
    def assemble_image_rgba(u, v, rgb_colors, height, width):
        """
        Assemble the RGB color values into the (u, v) indexed pixels of an image.

        Parameters:
            u: array-like, shape (n,)
                Vector containing row indices.
            v: array-like, shape (n,)
                Vector containing column indices.
            rgb_colors: array-like, shape (n, 3)
                Array containing RGB color values.
            height: int
                Height of the image.
            width: int
                Width of the image.

        Returns:
            image: array-like, shape (height, width, 3)
                Assembled image with RGB color values.
        """

        default = [1, 1, 1, 0]

    
        # Initialize an empty image with dtype float to handle fractional colors
        image = np.zeros((height, width, 4), dtype=float)
        image[:, :] = default

        # Assemble the RGB color values into the image
        image[v, u, :3] = rgb_colors * 255
        image[v, u, 3] = 255

        mask = np.zeros((height, width), dtype=int)
        mask[v, u] = 1

        return image, mask


    @staticmethod
    def class_voting(u, v, semantic_classes, height, width, default=-1):

        # Initialize an empty image
        image = np.ones((height, width)) * default
        mask = np.zeros((height, width))

        num_semantic_classes = 13

        # Initialize an empty image with dtype float to handle fractional colors
        votes = np.zeros((height, width, num_semantic_classes), dtype=int)

        # Assemble the pixel values into the image
        for i in range(len(u)):
            votes[v[i], u[i], semantic_classes[i]] += 1
            mask[v[i], u[i]] = 1

        weights = [1, 1, 1, 4, 16, 16, 16, 16, 64, 64, 64, 64, 64] 
        votes = votes * weights

        votes = np.argmax(votes, axis=2)

        image[mask == 1] = votes[mask == 1]
        return image 


    # @staticmethod
    # def assemble_image_rgb(u, v, rgb_colors, height, width, default=[0, 0, 0]):
    #     """
    #     Assemble the RGB color values into the (u, v) indexed pixels of an image.

    #     Parameters:
    #         u: array-like, shape (n,)
    #             Vector containing row indices.
    #         v: array-like, shape (n,)
    #             Vector containing column indices.
    #         rgb_colors: array-like, shape (n, 3)
    #             Array containing RGB color values.
    #         height: int
    #             Height of the image.
    #         width: int
    #             Width of the image.

    #     Returns:
    #         image: array-like, shape (height, width, 3)
    #             Assembled image with RGB color values.
    #     """
    #     # Initialize an empty image with dtype float to handle fractional colors
    #     image = np.zeros((height, width, 3), dtype=float)
    #     image[:, :] = default

    #     # Assemble the RGB color values into the image
    #     image[v, u] = rgb_colors / 255

    #     mask = np.zeros((height, width), dtype=int)
    #     mask[v, u] = 1

    #     # Clip the values to ensure they are within the valid range [0, 1]
    #     image = np.clip(image, 0, 1)

    #     return image, mask


    # @staticmethod
    # def assemble_image_scalar(u, v, r, height, width, default=-1):
    #     """
    #     Assemble the pixel values from the r vector into the (u, v) indexed pixels of an image.

    #     Parameters:
    #         u: array-like, shape (n,)
    #             Vector containing row indices.
    #         v: array-like, shape (n,)
    #             Vector containing column indices.
    #         r: array-like, shape (n,)
    #             Vector containing pixel values.
    #         height: int
    #             Height of the image.
    #         width: int
    #             Width of the image.

    #     Returns:
    #         image: array-like, shape (height, width)
    #             Assembled image.
    #     """
    #     # Initialize an empty image
    #     image = np.ones((height, width)) * default

    #     # Assemble the pixel values into the image
    #     image[v, u] = r

    #     mask = np.zeros((height, width), dtype=int)
    #     mask[v, u] = 1

    #     return image, mask


    # def assemble_image_superposition_count(u, v, height, width):

    #     # Initialize an empty image
    #     image = np.zeros((height, width)) 

    #     # Assemble the pixel values into the image
    #     for i in range(len(u)):
    #         image[u[i], v[i]] += 1

    #     return image

    # @staticmethod
    # def assemble_image_rgb_superposition(u, v, rgb_colors, height, width):
    #     """
    #     """
    #     # Initialize an empty image with dtype float to handle fractional colors
    #     image = np.zeros((height, width, 3), dtype=float)

    #     # Assemble the RGB color values into the image
    #     image[v, u] = rgb_colors / 255

    #     # Find unique pixel indices and their counts
    #     uv = np.stack((u, v), axis=1)
    #     unique_pixels, counts = np.unique(uv, axis=0, return_counts=True)

    #     # ReColor the pixels, where assembly count is greater than 1
    #     ids = np.where(counts > 1)[0]

    #     image[unique_pixels[ids, 1], unique_pixels[ids, 0]] = [1, 0, 0]

    #     # Clip the values to ensure they are within the valid range [0, 1]
    #     image = np.clip(image, 0, 1)

    #     return image
