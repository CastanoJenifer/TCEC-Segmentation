#!/usr/bin/env python3
import stat
from pathlib import Path
import subprocess

ALLOWED_EXTENSIONS = {'nii.gz'}

"""
Ejecuta un comando del sistema operativo y maneja su output/errores.

Parámetros:
cmd : list
Lista de strings que representa el comando a ejecutar y sus argumentos.

Retorna:
subprocess.CompletedProcess
Objeto con los resultados de la ejecución que incluye:
- returncode: Código de retorno (0 = éxito)
- stdout: Salida estándar del comando como string
- stderr: Salida de error del comando como string

Ejemplo:
resultado = run_cmd(['echo', 'Hola mundo'])
[CMD] echo Hola mundo

Hola mundo
"""
def run_cmd(cmd):
    print(f"\n[CMD] {' '.join(cmd)}\n")
    result = subprocess.run(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True)
    
    if result.returncode != 0:
        print("ERROR:")
        print(result.stderr)
        raise RuntimeError(f"Error running: {' '.join(cmd)}")
    
    print(result.stdout)
    return result


"""
Extrae la extensión del nombre de archivo y comprueba si está en la lista de extensiones permitidas definida en ALLOWED_EXTENSIONS.

Parámetros:
file : str
Nombre completo del archivo (ej: "documento.pdf", "imagen.png").

Retorna:
bool
True si la extensión del archivo está en ALLOWED_EXTENSIONS.
False si la extensión no está permitida o el archivo no tiene extensión.

Ejemplos:
ALLOWED_EXTENSIONS = {'nii.gz'}
allowed_file("sujeto.nii.gz")
True
"""
def allowed_file(file):
    extension = ".".join(file.split(".")[1:])
    return extension in ALLOWED_EXTENSIONS


"""
Esta función comprueba que el directorio especificado contenga archivos y que todos tengan la extensión correcta (.nii.gz) para procesamiento.

Parámetros:
input_dir : str
Ruta al directorio que contiene las imágenes a verificar.

Retorna:
La función no retorna ningún valor, solo valida los archivos.

Lanza:
RuntimeError
En dos casos:
    1. Si no se encuentran archivos en el directorio especificado.
    2. Si algún archivo no tiene la extensión .nii.gz.
"""
def verify_inputs(input_dir):
    print("=== Checking input images ===")

    images = sorted(Path(input_dir).glob("*"))

    if len(images) == 0:
        raise RuntimeError("No files were found in the input")

    for img in images:
        name = img.name
        
        if not allowed_file(name):
            raise RuntimeError(
                f"The file '{name}' is not valid"
                f"Must have the extension .nii.gz"
            )


"""
Esta función ejecuta el script de ROBEX sobre todas las imágenes .nii.gz en el directorio de entrada, guardando los resultados en el directorio de salida especificado.

Parámetros:
input_dir : str
Directorio que contiene las imágenes .nii.gz de entrada a procesar.

robex_dir : str
Directorio donde se guardarán las imágenes procesadas por ROBEX. Se crea automáticamente si no existe.

Retorna:
La función no retorna valores, procesa las imágenes y las guarda en el directorio de salida.
"""
def run_robex(input_dir, robex_dir):
    print("=== Running ROBEX ===")
    print("\n This may take a long time")
    Path(robex_dir).mkdir(parents=True, exist_ok=True)
    
    robex_script = Path("./ROBEX/runROBEX.sh")
    
    try:
        robex_script.chmod(robex_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception as e:
        print(f"Warning: Could not set permissions with Python: {e}") 
        pass 

    for img in Path(input_dir).glob("*.nii.gz"):
        output_img = Path(robex_dir) / img.name
        run_cmd(
            [str(robex_script), str(img.resolve()), str(output_img.resolve())] 
        )


"""
Esta función realiza el registro no lineal de imágenes cerebrales .nii.gz  contra un atlas de referencia usando el script antsRegistrationSyN.sh.

Parámetros:
input_dir : str
Directorio que contiene las imágenes .nii.gz a registrar.

ants_dir : str
Directorio donde se guardarán los resultados del registro ANTs. Se crea automáticamente si no existe.

atlas_path : str
Ruta al archivo del atlas de referencia (.nii.gz) que se usará como objetivo para el registro.

Retorna:
La función no retorna valores, genera archivos de salida de ANTs en el directorio especificado.  
"""
def run_ants(input_dir, ants_dir, atlas_path):
    print("=== Running ANTs Registration ===")
    print("\n This may take a long time")
    Path(ants_dir).mkdir(parents=True, exist_ok=True)
    
    ants_cmd_path = "/usr/local/bin/antsRegistrationSyN.sh"

    for img_path in sorted(Path(input_dir).glob("*.nii.gz")):
        
        file_prefix = img_path.stem.split(".")[0]
        out_prefix = Path(ants_dir) / file_prefix
        
        cmd = [
            ants_cmd_path,
            "-d", "3",
            "-f", atlas_path,
            "-m", str(img_path.resolve()),
            "-o", str(out_prefix)
        ]
        
        try:
            run_cmd(cmd)
        except RuntimeError as e:
            print(f"Warning: ANTs failed for {img_path.name}. Continuing...")
            print(e)
            
    print("=== ANTs Registration completed ===")


"""
Esta función busca las imágenes procesadas por ANTs (archivos *Warped.nii.gz) y las renombra con el sufijo '_0000.nii.gz' requerido por el framework nnUNet para segmentación.

Parámetros:
ants_dir : str
Directorio que contiene los archivos de salida generados por ANTs. Debe incluir archivos con el patrón *Warped.nii.gz.

Retorna:
list
Lista de objetos Path con las rutas de las imágenes renombradas. Cada elemento es la ruta completa a un archivo renombrado.
"""
def rename_after_ants(ants_dir):
    print("=== Renaming registered images for nnUNet ===")

    registered_images = []
    for img in Path(ants_dir).glob("*Warped.nii.gz"):
        if not img.name.endswith("InverseWarped.nii.gz"):
            registered_images.append(img)
    
    registered_images = sorted(registered_images)
    
    if len(registered_images) == 0:
        print("No *Warped.nii.gz files were found")
        all_files = list(Path(ants_dir).glob("*.nii.gz"))
        print(f".nii.gz files found in {ants_dir}:")
        for f in all_files:
            print(f"  - {f.name}")
        raise RuntimeError("ANTs did not generate appropriate Warped.nii.gz images")

    out_list = []
    for img in registered_images:
        if "Warped.nii.gz" in img.name:
            base = img.name.replace("Warped.nii.gz", "")  
            new_name = f"{base}_0000.nii.gz"       
            new_path = Path(ants_dir) / new_name
            
            print(f"Renaming: {img.name} → {new_name}")
            run_cmd(["mv", str(img), str(new_path)])
            out_list.append(new_path)
    
    print(f"{len(out_list)} images were renamed for nnUNet")
    return out_list


"""
Esta función ejecuta el comando de predicción de nnUNet sobre las imágenes previamente procesadas y renombradas en el directorio de ANTs, generando máscaras de segmentación en el directorio de predicciones.

Parámetros:

ants_dir : str
Directorio que contiene las imágenes procesadas por ANTs y renombradas.

pred_dir : str
Directorio donde se guardarán las predicciones/segmentaciones generadas por nnUNet. Se crea automáticamente si no existe.

dataset_id : int
ID numérico del dataset de nnUNet que se usará para la predicción.

configuration : str
Nombre de la configuración del modelo de nnUNet a utilizar: "3d_fullres".

Retorna:
La función no retorna valores, genera archivos de predicción en el directorio especificado.
"""
def run_nnunet(ants_dir, pred_dir, dataset_id, configuration):
    print("=== Running nnUNetv2_predict ===")
    print("\n This may take a long time")
    
    Path(pred_dir).mkdir(parents=True, exist_ok=True)

    cmd = [
        "nnUNetv2_predict",
        "-i", ants_dir,
        "-o", pred_dir,
        "-d", str(dataset_id), 
        "-c", configuration,
        "-f", "all"
    ]
    run_cmd(cmd)
    

"""
Esta función elimina los archivos temporales y de transformación generados por ANTs durante el proceso de registro, manteniendo solo las imágenes registradas finales.

Parámetros:
ants_dir : str
Directorio que contiene los archivos generados por ANTs.

keep_registered : bool, opcional
Si es True (por defecto), conserva las imágenes registradas finales (archivos que terminan en '_0000.nii.gz').
Si es False, elimina TODOS los archivos en el directorio.

Retorna:
La función no retorna valores, elimina archivos del sistema de archivos.
"""    
def cleanup_intermediate(ants_dir, keep_registered=True):
    print("\n === Cleaning intermediate files ===")

    for f in Path(ants_dir).glob("*"):
        if keep_registered and f.name.endswith("_0000.nii.gz"):
            print(f"Keeping final registered image: {f}")
            continue

        print(f"Removing ANTs: {f}")
        f.unlink()


"""
Esta función inicia todo el flujo de trabajo desde el preprocesamiento hasta la predicción, pasando por los siguientes pasos

Parámetros:
input_dir : str
Directorio que contiene las imágenes cerebrales de entrada

atlas_path : str
Ruta completa al archivo del atlas de referencia (.nii.gz) que se usará como objetivo para el registro no lineal.

out_root : str
Directorio raíz donde se crearán todos los subdirectorios de salida.

dataset_id : int
ID numérico del dataset de nnUNet configurado (15).

config : str
Configuración del modelo de nnUNet a utilizar para la segmentación: "3d_fullres".

Retorna:
La función no retorna valores, ejecuta el pipeline completo y genera resultados en los directorios de salida.
"""
def run_process(input_dir, atlas_path, out_root, dataset_id, config):
    robex_dir   = f"{out_root}/ROBEX"
    ants_dir    = f"{out_root}/ants"
    pred_dir    = f"{out_root}/predictions"

    print("=== PIPELINE STARTED ===")

    run_robex(input_dir, robex_dir)
    run_ants(robex_dir, ants_dir, atlas_path)
    rename_after_ants(ants_dir)
    cleanup_intermediate(ants_dir, keep_registered=True)
    run_nnunet(ants_dir, pred_dir, dataset_id, config)

    print("\n=== PIPELINE SUCCESSFULLY COMPLETED ===")


"""
Esta función define los parámetros fijos del pipeline y ejecuta el flujo completo de procesamiento de imágenes cerebrales.
"""
def main():
    input_dir  = "/workspace/input"
    atlas_path = "/workspace/data/atlas/SRI24_atlas.nii"
    out_root   = "/workspace/output"
    dataset_id = 15
    config     = "3d_fullres"

    run_process(
        input_dir   = input_dir,
        atlas_path  = atlas_path,
        out_root    = out_root,
        dataset_id  = dataset_id,
        config      = config
    )


if __name__ == "__main__":
    main()

