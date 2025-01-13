# Arquitectura Distribuida

Para este proyecto, se requiere una arquitectura que permita lo siguiente:

1. Almacenar todos los archivos proporcionados por el usuario sin riesgo de pérdida.
2. Reducir la carga en cada nodo individual.
3. Evitar la pérdida de información, asegurando que ningún archivo se pierda, permitiendo al sistema tiempo suficiente para recuperarse.

Para lograr esto, implementaremos las siguientes ideas fundamentales:

1. Un archivo no se compartirá entre varios nodos del sistema; es decir, un nodo tendrá el archivo completo o no lo tendrá.
2. El sistema contará con "copias de seguridad de los archivos", de modo que si un nodo que contiene uno de los archivos falla, este no se perderá. Para ello, definimos un factor de replicación $k$, que indica que un archivo cualquiera está presente en al menos $k$ nodos.
3. Los metadatos se almacenan en una base de datos separada de los archivos, la cual será local a todos los nodos.
4. En caso de que se desee obtener el conjunto de todos los archivos, un nodo puede realizar consultas sucesivas a los demás y luego realizar una operación de unión para obtener el total.

## Diseño del sistema

El sistema tiene nodos servidor y nodos cliente. 

Los nodos cliente son los más simples desde el punto de vista del código puesto que solo contienen un servidor de `Vue.js` el cual solo se le hace una petición para obtener la página web que verá el usuario. Dado que luego las peticiones se harán desde un navegador web en la máquina host, estas se hacen pasar por un proxy en el mismo nodo del que se obtuvo con el propósito de que las conexiones utilicen la red de Docker y en partimcular el nodo router que une las redes de clientes y servidores respectivamente.

Los nodos servidor son los que tienen una arquitectura distribuida _per-se_ que se encargará de mantener la consistencia de los datos y mejorar la eficiencia del sistema. Los nodos estarán organizados en forma de anillo, cada uno conociendo únicamente a su antecesor y sucesor. El orden dentro del anillo está determinado por un identificador único de $m$ bits para cada nodo; esto permite utilizar un algoritmo como la tabla de hash distribuida de CHORD para, dado el `id` de un archivo, determinar qué nodo debe ser el responsable de ese archivo. Para mantener la consistencia y evitar pérdidas de datos, un archivo tendrá copias de seguridad en los $k - 1$ nodos siguientes al responsable del mismo, con lo que tenemos un factor de replicación $k$ el cual nos permite perder hasta $k - 1$ nodos sin que se afecten los datos. En cuanto a los metadatos puesto que son extremadamente ligeros lo más conveniente es que se almacenen en todos los nodos, de esta manera en caso de un fallo catastrófico es posible que cada nodo conozca los datos que se pierden o los que deben recuperarse dependiendo del caso.

En la red de docker los nodos se organizan de la siguiente manera:

- Los clientes son independientes uno del otro puesto que son autocontenidos. Estos nodos levantan un cliente web que los usuarios pueden usar para ver las listas de canciones y reproducirlas.
- Los nodos servidor están en constante comunicación entre ellos para mantener la consistencia y replicación de datos. Estos nodos se encargan de las tareas de almacenamiento de archivos y metadatos así como organizar y responder a las peticiones de los usuarios.

## Tipos de procesos

En este proyecto, se utiliza un enfoque basado en **hilos** tanto para el manejo de los nodos como para la gestión de los clientes de la API REST. Aunque la gestión de los clientes de la API REST es manejada por Django Rest Framework, el uso de hilos en Python ofrece varias ventajas sobre el uso de procesos o el enfoque `async-await`.

### Ventajas del uso de hilos en Python:

1. **Facilidad de uso**: Los hilos son más fáciles de implementar y manejar en Python, especialmente cuando se trabaja con operaciones de entrada/salida, como las que se realizan en la gestión de nodos y clientes de API.

2. **Menor consumo de recursos**: Los hilos comparten el mismo espacio de memoria, lo que reduce el consumo de recursos en comparación con los procesos, que requieren su propio espacio de memoria.

3. **Compatibilidad con I/O intensivo**: Python, con su Global Interpreter Lock (GIL), maneja mejor las operaciones de I/O intensivo con hilos, ya que el GIL no es un problema significativo en estos casos. Esto hace que las escrituras y lecturas de los archivos sean más eficientes.

4. **Simplicidad en la sincronización**: La sincronización entre hilos es más sencilla y directa, lo que facilita la implementación de mecanismos de control de concurrencia.

Este enfoque permite que el sistema sea más eficiente y escalable, aprovechando al máximo las capacidades de Python para manejar múltiples tareas concurrentemente sin la sobrecarga de procesos adicionales.

## Comunicación entre los nodos

En este proyecto, la comunicación se maneja de manera eficiente para asegurar la integridad y disponibilidad de los datos. Se utilizan diferentes tipos de comunicación para abordar las necesidades específicas de cada interacción:

1. **Comunicación Cliente-Servidor**: Los usuarios interactúan con los nodos servidor a través de una API REST. Este tipo de comunicación es ideal para las interacciones cliente-servidor debido a su simplicidad y capacidad para manejar solicitudes HTTP de manera eficiente. La API REST permite a los clientes realizar operaciones como cargar, descargar y gestionar archivos de manera sencilla y efectiva.

2. **Comunicación Servidor-Servidor**: Los nodos servidor se comunican entre sí utilizando sockets TCP. Este enfoque es necesario para mantener un estado compartido y permitir la sincronización continua entre nodos. A diferencia de REST, que es sin estado, los sockets TCP permiten una comunicación bidireccional y persistente, lo cual es crucial para tareas como la replicación de datos, la detección de fallos y la coordinación de nodos en el anillo.

3. **Comunicación entre Procesos**: Dentro de cada nodo, la comunicación entre procesos se maneja mediante hilos, lo que permite una gestión eficiente de las tareas concurrentes. Los hilos facilitan la ejecución simultánea de múltiples operaciones, como la gestión de solicitudes de clientes y la sincronización de datos entre nodos, sin la sobrecarga de crear procesos separados.

## Coordinación entre los nodos

La coordinación en un sistema distribuido es crucial para asegurar que todos los nodos trabajen de manera armoniosa y eficiente. En este proyecto, la coordinación se maneja de la siguiente manera:

1. **Sincronización de Acciones**: Aunque los nodos son independientes y pueden decidir cuándo realizar acciones como copiar un archivo, la sincronización es necesaria para asegurar que las operaciones críticas se realicen de manera ordenada. El algoritmo de CHORD se encarga de mantener la consistencia y coordinar las acciones entre nodos, asegurando que las copias de seguridad y la replicación de datos se realicen correctamente.

2. **Acceso Exclusivo a Recursos**: Para evitar condiciones de carrera, donde múltiples nodos intentan acceder o modificar el mismo recurso simultáneamente, se implementan mecanismos de bloqueo. Estos mecanismos aseguran que solo un nodo pueda acceder a un recurso crítico a la vez, previniendo inconsistencias y corrupción de datos.

3. **Toma de Decisiones Distribuidas**: La toma de decisiones en un entorno distribuido se realiza de manera colaborativa entre los nodos. Utilizando el algoritmo de CHORD, los nodos pueden determinar de manera eficiente qué acciones tomar en función del estado actual de la red y los datos. Esto permite que el sistema se adapte dinámicamente a cambios, como la adición o eliminación de nodos, sin necesidad de intervención manual.

## Nombrado y Localización

### Identificación de los Datos y Servicios

- **Identificadores Únicos**: Cada recurso, ya sea un archivo o un servicio, se identifica mediante un identificador único. En el contexto del algoritmo CHORD, este identificador se utiliza para determinar el nodo responsable de almacenar o gestionar el recurso.
- **Consistencia de Identificadores**: Los identificadores deben ser consistentes y persistentes, incluso si los nodos entran o salen de la red, para asegurar que los recursos puedan ser localizados de manera confiable.

### Ubicación de los Datos y Servicios

- **Distribución en el Anillo**: Los datos y servicios se distribuyen entre los nodos organizados en un anillo, donde cada nodo conoce a su antecesor y sucesor. Esta estructura permite una ubicación eficiente de los recursos.
- **Replicación de Datos**: Para asegurar la disponibilidad, los datos se replican en múltiples nodos. El factor de replicación $k$ garantiza que los datos estén presentes en al menos $k$ nodos, permitiendo la recuperación en caso de fallos.

### Localización de los Datos y Servicios

- **Búsqueda Logarítmica**: Utilizando el algoritmo CHORD, la localización de un nodo responsable de un identificador específico se realiza en tiempo logarítmico, lo que mejora la eficiencia del sistema.
- **Manejo de Cambios en la Red**: Cuando un nodo deja la red, el sistema automáticamente ajusta la localización de los datos, asignando la responsabilidad al sucesor del nodo saliente. Esto asegura que los datos permanezcan accesibles y consistentes.
- **Actualización Dinámica**: La entrada de nuevos nodos en la red se maneja de manera dinámica, ajustando la localización de los datos para incluir al nuevo nodo en el conjunto de nodos responsables, manteniendo así la consistencia y disponibilidad de los recursos.

## Consistencia y Replicación

### Distribución de los Datos

- **Estrategia de Distribución**: Los datos se distribuyen de manera uniforme entre los nodos del anillo, asegurando que cada nodo maneje una carga equilibrada. Esto se logra mediante el uso de un algoritmo de hash que asigna identificadores a los nodos y datos.
- **Balanceo de Carga**: La distribución equitativa de datos previene la sobrecarga de nodos individuales, mejorando la eficiencia y el rendimiento del sistema.

### Replicación, Cantidad de Réplicas

- **Factor de Replicación**: Se define un factor de replicación $k$, que determina el número de copias de cada dato en el sistema. Esto asegura que los datos estén disponibles incluso si algunos nodos fallan.
- **Gestión de Réplicas**: Las réplicas se almacenan en los nodos sucesores del nodo responsable, permitiendo una recuperación rápida y eficiente en caso de fallos.

### Confiabilidad de las Réplicas de los Datos tras una Actualización

- **Consistencia Eventual**: Las actualizaciones se propagan a todas las réplicas, asegurando que todas las copias de un dato sean consistentes a lo largo del tiempo.
- **Mecanismos de Sincronización**: Se implementan protocolos de sincronización para garantizar que las réplicas se actualicen de manera oportuna y precisa.

## Tolerancia a Fallas

### Respuesta a Errores

- **Detección de Fallos**: El sistema incluye mecanismos para detectar fallos de nodos y activar procedimientos de recuperación automáticamente.
- **Recuperación Automática**: Al detectar un fallo, el sistema redistribuye los datos afectados a otros nodos disponibles, asegurando la continuidad del servicio.

### Nivel de Tolerancia a Fallos Esperado

- **Redundancia de Datos**: Gracias al factor de replicación, el sistema puede tolerar la pérdida de hasta $k-1$ nodos sin afectar la disponibilidad de los datos.
- **Resiliencia del Sistema**: La arquitectura está diseñada para manejar fallos parciales sin interrupciones significativas en el servicio.

### Fallos Parciales

- **Nodos Caídos Temporalmente**: Los nodos que caen temporalmente pueden reintegrarse al sistema sin pérdida de datos, gracias a las réplicas.
- **Incorporación de Nodos Nuevos**: Los nuevos nodos se integran dinámicamente, recibiendo datos y responsabilidades de manera automática para mantener el equilibrio del sistema.

## Seguridad

### Seguridad con Respecto a la Comunicación

- **Cifrado de Datos**: Todas las comunicaciones entre nodos y clientes están cifradas para proteger la integridad y confidencialidad de los datos.
- **Autenticación de Conexiones**: Se utilizan protocolos de autenticación para verificar la identidad de los nodos y clientes antes de permitir el acceso.

### Seguridad con Respecto al Diseño

- **Aislamiento de Nodos**: Cada nodo opera en un entorno aislado, minimizando el riesgo de que un fallo o ataque afecte a otros nodos.
- **Control de Acceso**: Se implementan políticas de control de acceso para asegurar que solo usuarios autorizados puedan interactuar con el sistema.