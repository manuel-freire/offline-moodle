# offline-moodle

Una herramienta en python para descargar envíos de Moodle (vía su API REST), y posteriormente subir feedback para los alumnos.

## Guía rápida

- `om <courseid> <destino>` muestra las tareas del curso *courseid*; descarga a *destino* los envíos de la tarea seleccionada; y añade un fichero llamado `feedback.md` en esa carpeta, identificando curso y tarea en sendas cabeceras. Además, para cada envío,
    + crea una carpeta con el nombre del alumno (o, en envíos de grupo, el grupo) que hizo el envío
    + mete dentro lo entregado; si se trata de un zip, lo descomprime antes de copiarlo
    + crea una sección de primer nivel markdown para ese alumno en el fichero `feedback.md`.
 
- `om <fichero-feedback>` lee de *fichero-feedback* el id de curso y tarea; y sube el feedback que se haya introducido para cada alumno.

- el fichero de feedback contendrá, como cabecera, algo similar a 
~~~
# Curso Análisis de Datos Esdrújulos (012345)
# Práctica 1: Envía un fichero .zip con un "hola mundo" (234567)
~~~

Los números entre paréntesis corresponden a identificadores internos de moodle, y *no* se deben modificar.

- y para cada alumno, un epígrafe de la forma 
~~~
# Martín Martínez (345678) ""
~~~

Donde *no* se debe modificar el número entre paréntesis (es el id interno de moodle para ese alumno), y habrá que especificar la nota que le corresponde a continuación, entre comillas.
