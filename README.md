# offline-moodle

Una herramienta en python para descargar envíos de Moodle (vía su API REST), y posteriormente subir feedback para los alumnos.

## Guía rápida

- `om <assignmentid> <destino>` descarga a *destino* los envíos de la tarea *assignmentid*; y añade un fichero llamado `feedback.md` en esa carpeta. Para cada envío,
    + crea una carpeta con el nombre del alumno que hizo el envío
    + mete dentro lo entregado; si se trata de un zip, lo descomprime antes de copiarlo
    + crea una sección de primer nivel markdown para ese alumno en el fichero `feedback.md`.
 
- `om <assignmentid> <fichero-feedback>` sube a la tarea *assignmentid* lo que encuentre para cada usuario con un epígrafe en *fichero-feedback*.

- el fichero de feedback contendrá, para cada alumno, una línea de la forma

~~~
# Martín Martínez (123456) ""
~~~

Donde *no* se debe modificar el número entre paréntesis (es el id interno de moodle para ese alumno), y habrá que especificar la nota que le corresponde a continuación, entre comillas.
