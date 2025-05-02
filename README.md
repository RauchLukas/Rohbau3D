# Rohbau3D
A Shell Construction Site 3D Point Cloud Dataset

<p align="center">
  <img width="600" src="https://github.com/user-attachments/assets/725f1d51-7f75-4f2e-aef4-08990b47c42c" alt="Rohbau3D point cloud feature maps">
</p>
<p align="center"><em>Figure: Rohbau3D point cloud feature maps</em></p>

## Abstract

We present a novel 3D point cloud dataset of building shells, representing realistic indoor construction environments. The dataset is designed to support intelligent computing and computer vision applications for geometric processing in structural engineering. It comprises 504 high-quality LiDAR point clouds acquired with a terrestrial laser scanner at 14 distinct construction sites, including residential buildings, office buildings, educational facilities, and underground parking garages, all in various stages of shell construction or renovation. Each point cloud is provided with a comprehensive set of features, including infrared reflectance intensity, RGB colors, point distances to the sensor, and reconstructed surface normal vectors. This dataset is the first of its kind and scale to be publicly available for research and development. It is intended to facilitate benchmarking, algorithm validation, and the advancement of data-driven methods in structural and construction engineering.


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
