#!/bin/bash
# Script para compilar, limpiar y ejecutar el modelo

# --- Compilación en build ---
echo "Accediendo al directorio 'build'..."
cd build/ || { echo "No se pudo acceder al directorio 'build'."; exit 1; }

# Preguntar si se desea limpiar la carpeta build antes de generar el makefile
read -p "¿Desea limpiar la carpeta build antes de generar el makefile? [y/n]: " respuesta
if [[ "$respuesta" == [yY] ]]; then
    echo "Ejecutando make clean..."
    make clean
    echo "Eliminando archivos con rm * ..."
    rm -f *
fi


GENMAKE2_PATH="../../../tools/genmake2"
BUILD_OPTIONS_PATH="../../../tools/build_options/darwin_arm64_gfortran"

echo "Generando makefile con genmake2..."
$GENMAKE2_PATH -mods ../code/ -optfile $BUILD_OPTIONS_PATH
if [ $? -ne 0 ]; then
    echo "Error al generar el makefile."
    exit 1
fi

echo "Ejecutando 'make depend'..."
make depend
if [ $? -ne 0 ]; then
    echo "Error en 'make depend'."
    exit 1
fi

echo "Ejecutando 'make' para compilar el modelo..."
make
if [ $? -ne 0 ]; then
    echo "Error durante la compilación."
    exit 1
fi

# --- Limpieza del directorio run_expand ---
echo "Accediendo al directorio 'run_expand'..."
cd ../run_expand || { echo "No se pudo acceder al directorio 'run_expand'."; exit 1; }

# Preguntar si se desea limpiar la simulación anterior antes de generar el makefile
read -p "¿Desea limpiar la carpeta build antes de generar el makefile? [y/n]: " respuesta
if [[ "$respuesta" == [yY] ]]; then
    echo "Limpiando archivos antiguos en 'run_expand'..."
    rm -f pickup* 2>/dev/null
    rm -rf mnc_000* 2>/dev/null
    rm -f PHref* 2>/dev/null
    rm -f RhoRef.* 2>/dev/null
    rm -f output.txt 2>/dev/null
    rm -f STDERR.0000 2>/dev/null
    rm -f mitgcmuv 2>/dev/null
fi 

# --- Copiar el nuevo ejecutable ---
echo "Copiando el nuevo ejecutable desde '../build/mitgcmuv'..."
cp ../build/mitgcmuv .
if [ $? -ne 0 ]; then
    echo "Error al copiar el ejecutable."
    exit 1
fi

# --- Ejecutar el modelo ---
echo "Estableciendo límite de archivos abiertos con 'ulimit -n 6000'..."
ulimit -n 6000

echo "Ejecutando el modelo en segundo plano..."
time ./mitgcmuv > output.txt &
if [ $? -eq 0 ]; then
    echo "El modelo se está ejecutando en segundo plano. Revisa 'output.txt' para ver la salida."
else
    echo "Error al ejecutar el modelo."
    exit 1
fi

exit 0
