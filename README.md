# Rohbau3D
A Shell Construction Site 3D Point Cloud Dataset

<p align="center">
  <img width="700" src="https://github.com/user-attachments/assets/725f1d51-7f75-4f2e-aef4-08990b47c42c" alt="Rohbau3D point cloud feature maps">
</p>
<p align="center"><em>Figure: Rohbau3D point cloud feature maps</em></p>

## Abstract

We introduce Rohbau3D, a novel dataset of 3D point clouds that realistically represent indoor construction environments. The dataset comprises 504 high-resolution LiDAR scans captured with a terrestrial laser scanner across 14 distinct construction sites, including residential buildings, a large-scale office complex, educational facilities, and an underground parking garage—all in various stages of shell construction or renovation. Each point cloud is enriched with scalar laser reflectance intensity, RGB color values, and reconstructed surface normal vectors. In addition to the 3D data, the dataset includes high-resolution 2D panoramic renderings of each scene and its associated point cloud features. Designed to reflect the complexity and variability of real-world construction sites, Rohbau3D supports research in geometric processing, scene understanding, and intelligent computing in structural and civil engineering. To our knowledge, it is the first dataset of its kind and scale to be publicly released. Rohbau3D is intended as a foundation for ongoing work, with plans to extend it through additional scenes and targeted annotations to support future research.

### Paper
:page_facing_up: [Rohbau3D: A Shell Construction Site 3D Point Cloud Dataset](https://www.nature.com/articles/s41597-025-05827-7)


## Overview 

* [Data Records](#data-records)
  * [The Scope Of The Data](#the-scope-of-the-data) 
  * [The Dataset Structure](#the-dataset-structure)
* [Installation](#installation)
* [Download and Extract the Data](#download-and-extract-the-data)
* [Citation](#citation)
* [Acknowledgement](#acknowledgement)


## Data Records

The Rohbau3D data records can be summarized as a medium-scale repository of terrestrial laser scan point clouds covering static scenes from a wide variety of shell construction sides. The records include the spatial coordinates annotated with the sensor-specific (1) RGB color, (2) surface reflection intensity information, (3) the reconstruction of surface normal vectors, and (4) panoramic 2D image representations of all feature spaces


### The Scope Of The Data

The repository contains in total a set of 504 scenes captured in one of 14 different building environments.


File ID    | Acquisition Site Overview
-----------|--------------------------
site_000   | Multi-story apartment block with small to medium-sized rooms in brick wall construction. Some walls plastered, some exposed. Windows present; no doors. Floor mostly dry.
site_001   | Multi-story apartment block with small to medium-sized rooms. Sloping ceilings, brick wall construction, walls partially plastered. Windows present; no doors. Floor mostly dry.
site_002   | Reinforced concrete underground parking structure with low to high ceilings and column grid. Poor lighting. Water puddles on floor.
site_003   | Multi-story school building with large rooms. Reinforced concrete skeleton construction. Good lighting. Water puddles on floor.
site_004   | Large hall in reinforced concrete with round ceiling elements. Large floor opening. No facade installed.
site_005   | Multi-story school building with rooms of varying sizes. Drywall partitions. Semi-transparent temporary facade covering.
site_006   | Multi-story school building with medium to large rooms. Drywall partitions in some areas. Open facade surfaces. Technical equipment installed on ceilings.
site_007   | Large hall with high ceiling. Reinforced concrete construction.
site_008   | Multi-story office building with small to large rooms and freestanding drywall supports. Glazed facade installed. Technical equipment on ceilings installed.
site_009\* | Multi-story brick building under renovation. Historic features. Small rooms and narrow staircases. Windows present; no doors. Poor lighting.
site_010\* | Vaulted cellar of brick structure. Small rooms. Uneven floors. Poor lighting.
site_011   | Two-story structure with basement. Mixed brick and precast concrete construction. Small to medium rooms. Water on floors. Poor lighting.
site_012   | Multi-story apartment block with basement. Reinforced concrete prefabricated construction. Large window and door openings. Some scenes contain water on the floor and show poor lighting.
site_013\* | Multi-story brick building under renovation. Small rooms connected by corridors. Walls partly plastered, partly exposed. Mostly clean floors.                                            
--------------------------------------
*Renovation sites are indicated with an asterisk (*).*


### The Dataset Structure
```
rohbau3d
|-- metadata
|   |-- site_list.yaml
|   |-- site_metadata.yaml
|   '-- ... 
|
|-- site_00
|   |-- scan_00000
|   |   |-- coord.npy
|   |   |-- color.npy
|   |   |-- intensity.npy
|   |   |-- normal.npy
|   |   |-- panorama.png
|   |   '-- ...
|   |   
|   |-- scan_00001
|   |-- scan_00002
|   '-- ...
|
|-- site_001
|   |-- scan_01000
|   '-- ...
|
... 
'-- site_013
```


## Installation
   
### Requirements
* git 
* pooch
* tqdm
* zstandard
* yaml

### Clone Repository
Clone the Rohbau3D Repository to a local space. 

```bash
git clone https://github.com/RauchLukas/Rohbau3D.git
```

### Conda Environment
Manually create a conda environment and install the package

```bash
conda create -n rohbau3d python=3.11 -y
conda activate rohbau3d

cd Rohbau3D
pip install .
```

## Download and Extract the Data 

The Dataset can be directly downloaded in chunks from Dataverse | OpenData UniBw M:

> Download Link: [https://open-data.unibw.de/dataset](https://open-data.unibw.de/dataset.xhtml?persistentId=doi:10.60776/ZWJFI4)

Conveniently, this repository offers also the option of downloading the entire dataset or individual pieces using scripts. [**RECOMMENDED**]



- **Short Version:**
  
  Inside the `Rohbau3D` folder, run the `scripts/download.py` script to download all dataset point cloud files. 
  
  ```bash
  python scripts/download.py --config config/dataverse.yaml --download --extract
  ```
  **Options:** 
  - `--config` [required] : set the path to the configuration script. 
  - `--download` [optional] : Flag to enable download. Default=False. 
  - `--extract` [optional] : Flag to enable file extraction. Default=True.

 
- **Manual Configuration:**

    Customize the configuration inside the `config/dataverse.yaml` file:

    ```yaml
    # CONFIGURATION
    # Rohbau3D

    # GENERAL
    config_dir: config
    log_dir: log
    log_level: INFO

    # DOWNLOAD
    download_hub: dataverse
    download_dir: data/download
    feature_index_file: dataverse_file_index.json
    feature_selection: [all]
    scene_selection: [all]

    # FILE EXTRACT
    extract_dir: data/extract
    clean_download_files: False
    ```

    **Options:**

    - `config_dir` : Set the *path/to/the/configuration/files* location.
    - `log_dir`: Set the logging *path/to/the/logging* location.
    - `log_level` : Set the logging Level. 
    - `download_hub`: Set the download server / hub. [Allowed options: `dataverse` and `default`]
      > *Note: At the moment, the data can only be downloaded from Dataverse [https://open-data.unibw.de/](https://open-data.unibw.de/)*. 
    - `download_dir` : Set the *path/to/the/download* location. 
    - `feature_index_file` : Name the content index file for the download hub. 
    - `feature_selection` : Select the point cloud features to download as a `list`. Options include: 
      - `coord` : the actual xyz coordinate of the points. 
      - `color` : the RGB color annotation od the points. 
      - `intensity` : the LiDAR reflection intensity annotation of the points. 
      - `normal` : the reconstructed surface normal annotation of the points. 
      - `all` : selects all available point cloud features. 
    - `extract_dir` : Set the *path/to/the/file/extraction* location. 
    - `clean_download_files` : Set the Flag `True`, `False` to delete the download directory at the end of the script. 





## Citation

If you find our work useful in your research, please cite our paper:

```
@article{rauch.Rohbau3D.2025,
  title = {Rohbau3D: A Shell Construction Site 3D Point Cloud Dataset},
  shorttitle = {Rohbau3D},
  author = {Rauch, Lukas and Braml, Thomas},
  year = {2025},
  journal = {Scientific Data},
  volume = {12},
  number = {1},
  pages = {1478},
  publisher = {Nature Publishing Group},
  issn = {2052-4463},
  doi = {10.1038/s41597-025-05827-7},
}
```


## Acknowledgement
The surface normal estimation in this repo is based on/inspired by great works, including but not limited to:   
[SHS-Net](https://github.com/LeoQLi/SHS-Net) 
