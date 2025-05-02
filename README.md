# Rohbau3D
A Shell Construction Site 3D Point Cloud Dataset

<p align="center">
  <img width="600" src="https://github.com/user-attachments/assets/725f1d51-7f75-4f2e-aef4-08990b47c42c" alt="Rohbau3D point cloud feature maps">
</p>
<p align="center"><em>Figure: Rohbau3D point cloud feature maps</em></p>

## Abstract

We introduce Rohbau3D, a novel dataset of 3D point clouds that realistically represent indoor construction environments. The dataset comprises 504 high-resolution LiDAR scans captured with a terrestrial laser scanner across 14 distinct construction sites, including residential buildings, a large-scale office complex, educational facilities, and an underground parking garage—all in various stages of shell construction or renovation. Each point cloud is enriched with scalar laser reflectance intensity, RGB color values, and reconstructed surface normal vectors. In addition to the 3D data, the dataset includes high-resolution 2D panoramic renderings of each scene and its associated point cloud features. Designed to reflect the complexity and variability of real-world construction sites, Rohbau3D supports research in geometric processing, scene understanding, and intelligent computing in structural and civil engineering. To our knowledge, it is the first dataset of its kind and scale to be publicly released. Rohbau3D is intended as a foundation for ongoing work, with plans to extend it through additional scenes and targeted annotations to support future research.


## Data Records

The Rohbau3D data records can be summarized as a medium-scale repository of terrestrial laser scan point clouds covering static scenes from a wide variety of shell construction sides. The records include the spatial coordinates annotated with the sensor-specific (1) RGB color, (2) surface reflection intensity information, (3) the reconstruction of surface normal vectors, and (4) panoramic 2D image representations of all feature spaces

### The Scope Of The Data

> Table of contents


### The Dataset Structure
```shell



```


### Download The Data: 

> Download Link:


### Extract The Data: 

```python
from src.download import Rohbau3DDataset

config = {}
Rohbau3DDataset(config).download()

```

### Technical Validation 

```python
from src.download import Rohbau3DDataset

config = {}
Rohbau3DDataset(config).validate(features='all')
```

## Documentation 






## Citation

If you find our work useful in your research, please cite our paper:

```


```

## Acknowledement
The surface normal estimation in this repo is based on/inspired by great works, including but not limited to:   
[SHS-Net](https://github.com/LeoQLi/SHS-Net) 
