# Automated Brain Lesion Segmentation Pipeline (TBI)

This repository provides a **complete neuroimaging pipeline** for automated **brain lesion segmentation** using **ROBEX**, **ANTs**, and **nnU-Net**.  
It is specifically designed for **closed traumatic brain injury (TBI)** lesion segmentation on **T1-weighted MRI scans**.

The pipeline performs:

- Skull stripping  
- Atlas-based registration  
- Intensity normalization  
- Deep learning segmentation with nnU-Net  

Once the Docker container is executed, the entire processing pipeline runs automatically.

This project provides:
- Automated brain extraction (ROBEX)
- Spatial normalization using ANTs
- Intensity normalization methods
- Lesion segmentation using nnU-Net
- A fully reproducible Docker environment

No manual commands are required inside the container.  
All processing is executed automatically when Docker starts.

---

## Instructions

#### 1. Clone the repository

```bash
git clone <this-repository>
