# GenReMur

https://genremur.streamlit.app/

GenReMur es una aplicación experimental para obtener de forma automática información genealógica basada en los datos indexados por el grupo de voluntarios de [Indexación Murcia Genealogía](https://www.facebook.com/groups/Indexacion.Murcia.Genealogia/).

Este grupo recopila principalmente partidas de bautismo, matrimonio y defunción de los pueblos de la Región de Murcia y lo vuelca en documentos de Excel. Estos documentos están disponibles en la [nube](https://onedrive.live.com/?authkey=%21AI%2DjU1MqxB9G8oM&id=BF237BB486352469%21510525&cid=BF237BB486352469).

La idea de GenReMur es aprovechar los datos de estos Excels para buscar automáticamente antepasados en base a los campos que especifican los padres y los abuelos. Principalmente, el programa buscará la persona indicada, sacará los padres y abuelos, y repetirá el proceso para cada padre. Por lo tanto, el programa solo funcionará en caso de que los padres y abuelos estén indicados en el Excel.

Antes de usar el programa lo primero es entender si el Excel que se utiliza contiene el rango de años en el que estás interesado.

### Limitaciones
#### Apellidos compuestos
En los campos de padres y abuelos, el programa espera nombres de 3 palabras como máximo, o de 4 si la segunda palabra está ne la lista de nombres compuestos. Por lo tanto, no es capaz de detectar apellidos compuestos (excepto que estuvieran siempre unidos con un guion como Marin-Ordoñez).

#### Datos particalmente ausentes en Excel
Aunque los padres o abuelos estén presentes en FamilySearch, si estos no aparecen en sus columnas correspondientes en el Excel, el programa no los puede detectar. El programa no puede obtener está información del campo observaciones tampoco.

#### Casos no obvios
El programa es conservador y solo acepta coincidencias si las diferencias son pequeñas: 1 letra de diferencia o un campo vacío. Por lo tanto, si los datos indexados no están muy completos o no es un caso fácil, es improbable que funcione.


### Preguntas frequentes
#### Por qué a mi no me funciona?
Pueden haber varios motivos por los que no funcione. En primer lugar, la persona que se busca debe aparece en el Excel (con padres y abuelos). En segundo lugar revisa la sección limitaciones para entender lo que puede y no puede hacer el programa. También ten en cuenta que la mayoría de Excels no estan 100% completos y faltan años.

#### ¿Dónde descargo el Excel?
https://onedrive.live.com/?authkey=%21AI%2DjU1MqxB9G8oM&id=BF237BB486352469%21510525&cid=BF237BB486352469

#### ¿Puede mejorar el programa?
Aunque el programa tiene mucho margen de mejora, al final es una lucha infinita contra los datos libremente escritos en el Excel. La mejor forma de conseguir que el programa funcione mejor es limpiando los datos del Excel. 

### Detalles técnicos (como funciona)
#### Lógica
La lógica del programa es la siguiente. Dada una persona (nombre, apellido 1, apellido 2) y el nombre de sus padres (obligatorio 4 de los 5 campos):
 1. Busca bautizo
 2. Busca defunción
 3. Busca hermanos (alguien con mismos padres y mismos apellidos)
  3.1 Solo acepta hermanos si los abuelos de todos los candidatos coinciden
 4. Busca matrimonio de los padres (si bautizo no encontrado o faltan abuelos en este)
 5. Si abuelos encontrado en bautizo o matrimonio repite la busqueda para el padre y la madre

#### Definicion de coincidencia
##### Coincidencia por celda
Se considera que el nombre o apellido que aparece en una celda coincide la palabra/s candidatas si:
 - Empieza por la misma palabra
  - Juan es Juan? ✓
  - Juan es Juan Luis? ✓
  - Juan Luis es Juan? ✗
  - Maria es Maria Dolores? ✓
 - Empieza por la misma palabra + Maria (solo para algunos nombre predefinidos)
  - Encarnacion es Maria Encarnacion? ✓
  - Dolores es Maria Dolores? ✓
  - Dolores es Maria? ✗
 - Cambia solo en una letra (excepto si cambia en una 'a' al final)
  - Joan es Juan? ✓
  - Martines es Martinez? ✓
  - Ramon es Ramos? ✓
  - Juana es Juan? ✗
  - Antonio es Antonia? ✗

##### Coincidencia por fila
Para comprobar si una fila coincide, se comprueba nombre, apellido 1, apellido 2, nombre padre y nombre madre. Se usa la comprobacion por celda descrita en la sección anterior.

En el caso de que solo uno de los campos esté vacío, también se considerará válido, aunque se priorizará aquellos resultados donde coinciden todos los campos.


### Limpieza
El principal reto para tratar con estos datos es la falta de estandarización a la hora de especificar cierta información. Algunos ejemplos se muestran a continuación. 

#### Separación de abuelos
El campo abuelos paternos/maternos puede estar separados de distintas formas:
 - Jose y Juana
 - Jose Sanchez /Juana
 - Jose e Isabel
 - Jose Sanchez Juana Perez (no soportado)

#### D, Don, Doña, Dña, D, etc
En ocasiones los nombres pueden incluir una mención a que la persona era Don Juan Perez, por lo que hay que detectar varias formas como esto puede estar especificado y eliminar estos prefijos para el analisis.

#### De, de la, del, de los, de las, etc.
Apellidos como "de la Cuesta" son problemáticos ya que a veces se puede referir a ellos sin los articulos. Por lo tanto, estos se eliminan a la hora de analizar:
 - Juan de la Cuesta Martinez -> Juan Cuesta Martinez
 - Maria de los Dolores -> Maria Dolores

#### Eliminaciones varias
 - Tildes
 - Signos de interrogacion
 - Parentesis

#### Natural/es de
A menudo la casilla de abuelos incluye la procedencia, esto requiere detectarlo para no confundirlo con los apellidos:
 - Jose Natural de Abaran y Juana -> Jose y Juana
 - Jose y Juana Naturales de Blanca -> Jose y Juana

#### Estandarización de nombres
  - "Gimenez","Ximenez" ->  "Jimenez"
  - "Salbador" ->  "Salvador"
  - "Salbadora" ->  "Salvadora"
  - "Ysabel","Ysavel","Isavel" ->  "Isabel"
  - "Joachina" ->  "Joaquina"
  - "Joquin","Joachin" ->  "Joaquin"
  - "Josepha" ->  "Josefa"
  - "Joseph","Josef" ->  "Jose"
  - "Bartholome" ->  "Bartolome"
  - "Cathalina" ->  "Catalina"
  - "Thomas" ->  "Tomas"
  - "Matheo" -> "Mateo"
  - "Jines" ->  "Gines"
  - "Ysidra" ->  "Isidra"
  - "Pasqual" ->  "Pascual"
  - "Pasquala" ->  "Pascuala"
  - "Covarro" ->  "Cobarro"
  - "Maxima" ->  "Maximina"
  - "Quadrado" ->  "Cuadrado"
  - "Hoios", "Oios", "Hoyos" ->  "Oyos"
  - "Penalba" -> "Penalva"
  - "Anna" -> "Ana"
  - "Baquero","Baquelo","Vaquelo" -> "Vaquero"
  - "Xaime" -> "Jaime"
  - "Xavier" -> "Javier"
  - "Aº" -> "Antonio"
  - "Mª" -> "Maria"
  - "Ygnacio" -> "Ignacio"
  - "Ygnacia" -> "Ignacia"
  - "No constan", "n/c","nc" -> ""

## Separación de nombres y apellidos
El segundo reto para el programa es determinar dado un nombre completo, que parte es nombre, apellido 1 y apellido 2. Esto no suele ser problema para la persona principal pues tiene campos separados para nombre, apellido 1 y apellido 2, pero si es un problema con padres y abuelos. Por lo tanto la función de separación de nombres solo a los campos de padres y abuelos.

En general, para cadenas de 3 palabras o menos, la logica es simplemente considerar la primera palabra nombre, y las siguientes apellidos. Por ejemplo:
- Juan -> Juan | _ | _
- Juan Perez -> Juan | Perez | _
- Juan Perez Sanchez -> Juan | Perez | Sanchez

No obstante esto no es suficiente para nombres compuestos como Juan Luis Perez. No hay una forma fácil para un ordenador de distinguir nombres de apellidos así que hay una lista manualmente creada con nombres que pueden aparecen en segunda posición:
 - "Jesus", "Dolores", "Maria", "Encarnacion", "Jose", "Antonio", "Ana"
 - "Rosa", "Carmen", "Josefa", "Pablo", "Antonia", "Angeles", "Rosario"
 - "Trinidad", "Pedro", "Juana", "Francisca", "Visitacion", "Dios", "Alejandro"
 - "Elisa", "Angel","Casimiro","Casimira", "Pascual", "Pascuala", "Cruz", "Catalina"
 - "Bautista", "Fermina", "Joaquin", "Joaquina","Biviano", "Lazaro"
 - "Luis", "Juan", "Amador", "Luisa", "Jorge", "Vicente","Vicenta"
 - "Isabel","Javier", "Cayetano", "Cayetana", "Rodrigo"

De tal modo que si en un nombre compuesto el segundo nombre es uno de esos, lo detectará correctamente. Ejemplos:
 - Juan Luis Perez -> Juan Luis | Perez | _
 - Rosa Elisa -> Rosa Elisa | _ | _
 - Maria Visitacion Martinez Sanchez -> Maria Visitacion | Martinez | Sanchez

#### Apellidos compuestos (no soportado)
Si a pesar de la lógica de la sección anterior siguen habiendo más de 2 palabras después del nombre, el programa tira la toalla, pues no puede detectar apellidos compuestos. Por ejemplo:
 - Jose Antonio Marin Blazquez Marin Ordoñez
