import pandas as pd
import io
import re
import datetime
from dataclasses import dataclass, replace, field
from collections import defaultdict
from typing import Tuple


# Wheter to print logs
_LOGGING = True

_VERIFY_SAME_SURNAMES_PER_ROW = False

####################

# When looking for a person based on parents, if the birth and death certificate
# of a person is missing, search for siblings and infer the grandparents
_INFER_PARENTS_FROM_SIBLINGS = True

# Assume that parents must always be >16 years older than children
_MIN_AGE_PARENTING = 16
# Assume that parents must always less than 60 years older than children
# i.e. max age at which they can have a child
_MAX_AGE_PARENTING = 60
# How many years can a person live after giving birth
_MAX_LIFESPAN_AFTER_PARENTING = 60


context_map : dict[int, list[str]]= defaultdict(list)

class Logger:
  id: int
  nombre_completo: str
  context: str = ""

  def __init__(self, id:int, nombre_completo:str):
    self.id = id
    self.nombre_completo = nombre_completo

  def log_line(self, s:str=""):
    if _LOGGING:
      print(f"{self.nombre_completo} - {s}")
    context_map[self.id].append(s+"<br>")

  def log_accum(self, s:str=""):
    if _LOGGING:
      if not self.context:
        print(f"{self.nombre_completo} - {s}")
      else:
        print(f"{s}")
    self.context+= str(s)+"<br>"

  def log_flush(self):
    if not self.context:
      return
    context_map[self.id].append(self.context)
    self.context = ""
    print()

def log(s:str=""):
  if _LOGGING:
    print(s)

def upload_file():
  from google.colab import files
  uploaded = files.upload()

  if not uploaded:
    print("No file uploaded.")
    return None

  filename = list(uploaded.keys())[0]
  print(f"Uploaded file: {filename}")

  return uploaded[filename]


def extract_year(value):
  if isinstance(value, datetime.datetime):
    return value.year
  try:
    return int(value)
  except Exception:
    return pd.NA

import functools

@functools.cache
def compute_rewrite_rules():
  _REWRITE_RULES = [
      (["Gimenez","Ximenez"], "Jimenez"),
      (["Salbador"], "Salvador"),
      (["Salbadora"], "Salvadora"),
      (["Ysabel","Ysavel","Isavel"], "Isabel"),
      (["Joachina"], "Joaquina"),
      (["Joquin","Joachin"], "Joaquin"),
      (["Josepha"], "Josefa"),
      (["Joseph","Josef"], "Jose"),
      (["Bartholome"], "Bartolome"),
      (["Cathalina"], "Catalina"),
      (["Thomas"], "Tomas"),
      (["Matheo"],"Mateo"),
      (["Jines"], "Gines"),
      (["Ysidra"], "Isidra"),
      (["Pasqual"], "Pascual"),
      (["Pasquala"], "Pascuala"),
      (["Covarro"], "Cobarro"),
      (["Maxima"], "Maximina"),
      (["Quadrado"], "Cuadrado"),
      (["Hoios", "Oios", "Hoyos"], "Oyos"),
      (["Penalba"],"Penalva"),
      (["No constan", "n/c","nc"],""),
      (["x", "xx","xxx","xxxx"],""),
      (["…","……","………","…………"], ""),
      (["Anna"],"Ana"),
      (["Baquero","Baquelo","Vaquelo"],"Vaquero"),
      (["Xaime"],"Jaime"),
      (["Xavier"],"Javier"),
      (["Aº"],"Antonio"),
      (["Mª"],"Maria"),
      (["Ygnacio"],"Ignacio"),
      (["Ygnacia"],"Ignacia"),
  ]
  compiled_rules = []
  for patterns, replacement in _REWRITE_RULES:
    patterns_regex = "|".join( patterns)
    regex = f"\\b({patterns_regex})\\b"
    compiled_rules.append((re.compile(regex, re.IGNORECASE), replacement))
  return compiled_rules

def apply_rewrite_rules(v):
  compiled_rules = compute_rewrite_rules()
  for regex, replacement in compiled_rules:
    v = regex.sub(replacement, v)
  return v

def remove_tildes(v):
  replacements = {
    'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
    'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U'
  }
  return ''.join(replacements.get(c, c) for c in v)

def remove_de(v):
  # Remove de/del/de la
  v = re.sub(r"(\b(de la|del|de los|de las|de)\b)","", v, flags=re.IGNORECASE)
  # Remove parentesis and question marks
  v = re.sub(r"\)|\(|\?|\¿","", v, flags=re.IGNORECASE)
  # Remove D. y Dña.
  v = re.sub(r"^(Dña\.|Dña |Doña |Don |D\.|Dº|D )| (Dña\.|Dña |Doña |Don |D\.|Dº|D )"," ", v, flags=re.IGNORECASE)
  # Remove points
  v = re.sub(r"…+","", v, flags=re.IGNORECASE)
  v = re.sub(r"\.+"," ", v, flags=re.IGNORECASE)

  # Remove trailing spaces after deleting (if de at the beginning of end)
  v = v.strip()
  # Remove repeated spaces after deletion (if de in the middle)
  v = re.sub(r" +", " ",v)
  return v

def clean_names(v):
  v = remove_de(v)
  v = remove_tildes(v)
  v = apply_rewrite_rules(v)
  v = v.title() # Capitalize first letter every word
  return v




def load_all_sheets_in_colab(data_bytes):
  io_buffer = io.BytesIO(data_bytes)
  # Read all sheets into a dictionary of DataFrames
  cols_baut = {"N°":None,"Observaciones": None,"Año": extract_year}
  for x in ["Nombre","Apellido 1","Apellido 2", "Nombre Padre", "Nombre Madre",
           "Abuelos Paternos", "Abuelos Maternos"]:
    cols_baut[x] = clean_names
  baut: pd.DataFrame = pd.read_excel(io_buffer, sheet_name="Bautismos", converters=cols_baut, usecols=list(cols_baut.keys()))
  baut.rename(columns=clean_column_name, inplace=True)
  baut.dropna(subset=["Año", "Nombre"], inplace=True)
  baut.drop_duplicates(inplace=True)
  baut = baut.replace({float('nan'): None})

  cols_matr = {"N°":None,"Observaciones": None,"Año": extract_year}
  for x in ["Nombre_El","Apellido 1_El","Apellido 2_El","Nombre_Ella","Apellido 1_Ella","Apellido 2_Ella", "Padres_El", "Padres_Ella"]:
    cols_matr[x] = clean_names
  matr: pd.DataFrame = pd.read_excel(io_buffer, sheet_name="Matrimonios", converters=cols_matr, usecols=cols_matr)
  matr.rename(columns=clean_column_name, inplace=True)
  matr.dropna(subset=["Año", "Nombre_El", "Nombre_Ella"], inplace=True)
  matr.drop_duplicates(inplace=True)
  matr = matr.replace({float('nan'): None})

  cols_defu = {"N°":None,"Observaciones": None,"Año": extract_year}
  for x in ["Nombre","Apellido 1","Apellido 2", "Nombre Padre", "Nombre Madre"]:
    cols_defu[x] = clean_names
  defu: pd.DataFrame = pd.read_excel(io_buffer, sheet_name="Defunciones", converters=cols_defu, usecols=list(cols_defu.keys()))
  defu.rename(columns=clean_column_name, inplace=True)
  defu.dropna(subset=["Año", "Nombre"], inplace=True)
  defu.drop_duplicates(inplace=True)
  defu = defu.replace({float('nan'): None})


  print("All sheets loaded successfully into a dictionary of DataFrames.")
  return baut, matr, defu

def clean_column_name(name):
    name = name.replace(" ", "_")  # Replace spaces with underscores
    name = re.sub(r"[^\w]", "", name)  # Remove any non-alphanumeric character (except underscore)
    return name



########################

# TODO: Pascual suele ser apellido, Vicente a veces
NAME_FOLLOWUPS = set([
    "Jesus", "Dolores", "Maria", "Encarnacion", "Jose", "Antonio", "Ana",
    "Rosa", "Carmen", "Josefa", "Pablo", "Antonia", "Angeles", "Rosario",
    "Trinidad", "Pedro", "Juana", "Francisca", "Visitacion", "Dios", "Alejandro",
    "Elisa", "Angel","Casimiro","Casimira", "Pascual", "Pascuala", "Cruz", "Catalina",
    "Bautista", "Fermina", "Joaquin", "Joaquina","Biviano", "Lazaro",
    "Luis", "Juan", "Amador", "Luisa", "dJorge", "Vicente","Vicenta",
    "Isabel","Javier", "Cayetano", "Cayetana", "Rodrigo"
])

MARIA_FOLLOWUPS = set([
 "Dolores",  "Encarnacion", "Ana",
    "Rosa", "Carmen", "Josefa", "Antonia", "Angeles", "Rosario",
    "Trinidad", "Juana", "Francisca", "Visitacion", "Catalina",
 "Pascuala", "Fermina", "Joaquina", "Pascual", "Purificacion", "Luisa",
 "Isabel","Ignacia","Vicenta"
])

def split_name_surnames(s: str):
  splits = re.split(r' ', s, flags=re.IGNORECASE)
  origen = None
  # Quitar Natural(es) de
  # TODO: Hacer algo con esta informacion
  # Juan Perez Natural (de) Cieza
  for i,v in enumerate(splits):
    if v == "Natural" or v== "Naturales":
      origen = " ".join(splits[i:])
      splits = splits[:i]
      break

  # Handle Maria Jesus, Maria Dolores, Jose Maria, etc
  if len(splits) > 1 and splits[1] in NAME_FOLLOWUPS:
    splits[0] += " " + splits[1]
    splits.pop(1)


  if len(splits) > 3:
    # Assume the 2 last are surnames and the rest the name
    # Doesn't work for sth like Juana Perez (de los) Cobos Martinez
    z =  FullName(" ".join(splits[0:-2]), splits[-2], splits[-1])
    # TODO:
    log("Persona con >3 apellidos, no se puede procesar : "+str(z))
    return z
  if len(splits) == 3:
    return FullName(splits[0], splits[1], splits[2], origen)
  if len(splits) == 2:
    return FullName(splits[0], splits[1], None, origen)
  if len(splits) == 1:
    return  FullName(splits[0], None, None, origen)
  raise ValueError("Unexpected error")

def get_abuelos(s: str):
  separator = r"\s+[ye]\s+|\s*[/]\s*"
  try:
    abuelo_paterno, abuela_paterna = re.split(separator, s, maxsplit=1, flags=re.IGNORECASE)
  except Exception:
    #print("Invalid grandparents:"+ s)
    return None
  abuelo_paterno = split_name_surnames(abuelo_paterno)
  abuela_paterna = split_name_surnames(abuela_paterna)
  return abuelo_paterno, abuela_paterna


from enum import Enum
class Match(Enum):
    TOTAL = 1
    MISSING_INFO = 2
    NO =3

def missing_one_char(str1, str2):
  if abs(len(str1) - len(str2)) != 1:
    return False

  # Ensure str1 is the longer string
  if len(str1) < len(str2):
    str1, str2 = str2, str1

  i, j = 0, 0,
  diff_found=  False

  while i < len(str1) and j < len(str2):
    if str1[i] != str2[j]:
      if diff_found:
        return False
      diff_found= True
      i += 1  # Skip the differing char in the longer string
    else:
      i += 1
      j += 1

  # Juana vs Juan, Joaquin y Joaquina
  if not diff_found and str1[i] == "a":
    return False
  return diff_found


def startswith_differ_by_one_char(cell, candidate):
  if missing_one_char(cell, candidate):
    return Match.TOTAL

  if len(cell) != len(candidate):
    cell = cell.split(" ")[0]

  if len(cell) != len(candidate):
    return Match.NO


  last_two_chars = sorted([cell[-1], candidate[-1]])
  # Cannot match Antonia y Antonio
  if last_two_chars == ["a","o"]:
    return Match.NO

  # Avoid Fernandez y Hernandez
  if sorted([cell, candidate]) == ["Fernandez","Hernandez"]:
    return Match.MISSING_INFO

  diff_count = 0
  for a, b in zip(cell, candidate):
    if a != b:
      diff_count += 1
      if diff_count > 1:
        return Match.NO
  if diff_count == 1:
    return Match.TOTAL

def match_cell(cell: str, candidate: str):
  if not cell:
    return Match.MISSING_INFO
  if not candidate:
    return Match.MISSING_INFO

  starts_with_candidate = re.match(pattern=f"^{re.escape(candidate)}\\b",string=cell)
  starts_with_maria_candidate =  re.match(pattern=f"^Maria {re.escape(candidate)}\\b",string=cell)
  if starts_with_candidate:
    return Match.TOTAL
  elif candidate in MARIA_FOLLOWUPS and starts_with_maria_candidate:
      return Match.TOTAL
  # Si difiere en un solo caracter (mismas posiciones) lo damos por bueno
  elif r:=startswith_differ_by_one_char(cell, candidate):
    return r
  else:
    return Match.NO


def print_row(r):
  d = r.to_dict()
  nombre = d["Nombre"]
  apellido_1 = replace_none(d["Apellido_1"],"_")
  apellido_2 = replace_none(d["Apellido_2"],"_")
  padre = replace_none(d["Nombre_Padre"],"_")
  madre = replace_none(d["Nombre_Madre"],"_")
  year = d["Año"]
  obs = d["Observaciones"]
  obs = f" [Observaciones: {obs}]" if obs else ""
  if "Abuelos_Paternos" in d.keys():
    abuelos_p = replace_none(d["Abuelos_Paternos"],"_")
    abuelos_m = replace_none(d["Abuelos_Maternos"],"_")
    log(f"({nombre} {apellido_1} {apellido_2}) Padres:({padre} \ {madre}) ({year}-) {obs}")
    log(f"AbuelosP:({abuelos_p})")
    log(f"AbuelosM:({abuelos_m})")
  else:
    log(f"({nombre} {apellido_1} {apellido_2}) Padres:({padre} \ {madre}) (-{year}) {obs}")

def replace_none(v,s):
  if v is None:
    return s
  return v

@dataclass
class FullName:
  nombre: str
  apellido_1: str | None = None
  apellido_2: str | None = None
  origen: str | None = None # Sin usar de momento

  def __str__(self):
    apellido_1 = replace_none(self.apellido_1, "")
    apellido_2 = replace_none(self.apellido_2, "")
    nombre = replace_none(self.nombre, "_")
    origen = f" (de {self.origen})" if self.origen else ""
    s =  " ".join(x for x in [nombre, apellido_1, apellido_2,origen] if x)
    if not self.nombre:
      raise ValueError(f"Unexpected error, there shouldn't be a FullName object without name: {s}")
    return s

  def str_explicit(self):
    nombre = self.nombre if self.nombre else "_"
    apellido_1 = self.apellido_1 if self.apellido_1 else "_"
    apellido_2 = self.apellido_2 if self.apellido_2 else "_"
    return f"{nombre} | {apellido_1} | {apellido_2}"



from typing import Optional
@dataclass
class Defuncion:
  # Campos obligatorios para que sea valido
  nombre: str
  year: int

  apellido_1: str | None = None
  apellido_2: str | None = None
  padre: FullName | None = None # Normalmente solo incluye nombre, sin apellidos
  madre: FullName | None = None# Normalmente solo incluye nombre, sin apellidos
  fecha: str | None = None
  observaciones: str | None = None # TODO: Buscar patron XX año(s) para saber edad y estimar nacimiento
  n_excel: int | None = None

  @classmethod
  def defu_from_series(cls, row: pd.Series) -> Optional['Defuncion']:
    nombre = row.get('Nombre')
    year = row.get('Año')
    padre = row.get('Nombre_Padre')
    madre = row.get('Nombre_Madre')
    padre = split_name_surnames(padre) if padre else None
    madre = split_name_surnames(madre) if madre else None
    apellido_1=row.get('Apellido_1')
    apellido_2=row.get('Apellido_2')

    if _VERIFY_SAME_SURNAMES_PER_ROW:
      if not nombre or not year:
        log(f"Fila descartada, falta nombre o año:\n{row}")
        return None

      if apellido_1 and padre and padre.apellido_1 and apellido_1 != padre.apellido_1:
        log(f"Apellidos padre e hijo no coinciden: {padre.apellido_1} → {apellido_1}")
        print_row(row)
        log()
      if apellido_2 and madre and madre.apellido_1 and apellido_2 != madre.apellido_1:
        log(f"Apellidos madre e hijo no coinciden: {madre.apellido_1} → {apellido_2}")
        print_row(row)
        log()

    return cls(
      nombre=nombre,
      apellido_1=apellido_1,
      apellido_2=apellido_2,
      padre=padre,
      madre=madre,
      fecha=row.get('Fecha'),
      observaciones=row.get('Observaciones'),
      year=year,
      n_excel=row.get('N') # For some reason it gets converted to N from N°
    )

  def __str__(self):
    apellido_1 = replace_none(self.apellido_1,"_")
    apellido_2 = replace_none(self.apellido_2,"_")
    padre = replace_none(self.padre,"_")
    madre = replace_none(self.madre,"_")
    year = self.year
    if self.observaciones:
      obs = f" [{self.observaciones}]"
    else:
      obs = ""
    n_excel = f" #{self.n_excel}" if self.n_excel else ""
    return f"{self.nombre} {apellido_1} {apellido_2} ({padre} & {madre}) ({year}){obs}{n_excel}"


@dataclass
class Bautizo(Defuncion):
  paterno: FullName | None = None # Abuelo paterno
  paterna: FullName | None = None # Abuela paterna
  materno: FullName | None = None # Abuelo materno
  materna: FullName | None = None # Abuela materna

  @classmethod
  def baut_from_series(cls, row: pd.Series) -> Optional['Bautizo']:
    # Reuse defu_from_series to handle the fields in Defuncion
    obj = Defuncion.defu_from_series(row)
    if obj is None:
      return None

    # Extract and process additional fields for Bautizo
    if paternos := get_abuelos(row.get('Abuelos_Paternos')):
      paterno, paterna = paternos
    else:
      paterno, paterna = None, None
    if maternos := get_abuelos(row.get('Abuelos_Maternos')):
      materno, materna = maternos
    else:
      materno, materna = None, None

    if _VERIFY_SAME_SURNAMES_PER_ROW:
      if paterno and paterno.apellido_1:
        if obj.apellido_1 and paterno.apellido_1 != obj.apellido_1:
          log(f"Apellido abuelo paterno e hijo no coinciden: {paterno.apellido_1} → {obj.apellido_1}")
          print_row(row)
          log()
        if obj.padre and obj.padre.apellido_1 and paterno.apellido_1 != obj.padre.apellido_1:
          log(f"Apellido abuelo paterno y padre no coinciden: {paterno.apellido_1} → {obj.padre.apellido_1}")
          print_row(row)
          log()
        if obj.padre and obj.padre.apellido_2 and paterna.apellido_1 != obj.padre.apellido_2:
          log(f"Apellido abuela paterna y padre no coinciden: {paterna.apellido_1} → {obj.padre.apellido_2}")
          print_row(row)
          log()
      if materno and materno.apellido_1:
        if obj.apellido_2 and materno.apellido_1 != obj.apellido_2:
          log(f"Apellido abuelo materno e hijo no coinciden: {materno.apellido_1} → {obj.apellido_2}")
          print_row(row)
          log()
        if obj.madre and obj.madre.apellido_1 and materno.apellido_1 != obj.madre.apellido_1:
          log(f"Apellido abuela materno y madre no coinciden: {materno.apellido_1} → {obj.madre.apellido_1}")
          print_row(row)
          log()
        if obj.madre and obj.madre.apellido_2 and materna.apellido_1 != obj.madre.apellido_2:
          log(f"Apellido abuela materna y madre no coinciden: {materna.apellido_1} → {obj.madre.apellido_2}")
          print_row(row)
          log()


    return cls(
      **obj.__dict__,  # Unpack the fields from the parent class
      paterno=paterno,
      paterna=paterna,
      materno=materno,
      materna=materna,
    )

  def get_abuelos(self):
    return self.paterno, self.paterna, self.materno, self.materna

  def __str__(self):
    apellido_1 = replace_none(self.apellido_1,"_")
    apellido_2 = replace_none(self.apellido_2,"_")
    padre = replace_none(self.padre,"_")
    madre = replace_none(self.madre,"_")
    paterno = replace_none(self.paterno,"_")
    paterna = replace_none(self.paterna,"_")
    materno = replace_none(self.materno,"_")
    materna = replace_none(self.materna,"_")
    year = self.year
    if self.observaciones:
      obs = f" [{self.observaciones}]"
    else:
      obs = ""
    n_excel = f" #{self.n_excel}" if self.n_excel else ""
    return f"{self.nombre} {apellido_1} {apellido_2} ({padre} & {madre}) AP:({paterno} & {paterna}) AM:({materno} & {materna}) ({year}){obs}{n_excel}"

import uuid
@dataclass
class Tree:
  baut: Bautizo | None
  defu: Defuncion | None = None
  padre: Optional['Tree'] = None
  madre: Optional['Tree'] | None = None
  n_siblings: int = 0
  inferred_from_siblings: bool = False
  id: int = field(default_factory=uuid.uuid4)


@dataclass
class SearchInfo:
  nombre: str
  apellido_1: str
  apellido_2: str | None = None
  nombre_padre: str | None = None
  nombre_madre: str | None = None
  year_child: int | None = None

  def __str__(self):
    padre = self.nombre_padre if self.nombre_padre else "_"
    madre = self.nombre_madre if self.nombre_madre else "_"
    apellido_2 = self.apellido_2 if self.apellido_2 else "_"
    return f"{self.nombre} {self.apellido_1} {apellido_2} ({padre} & {madre})"


@dataclass
class Sheets:
  baut_by_year: dict[int, list[Bautizo]]
  defu_by_year: dict[int, list[Defuncion]]
  matr_by_year: dict[int, dict]




def get_parenting_age_birth_range(year_child):
  # E.g. Child born in 1800 -> Parents borin in [1740 - 1784]
  return year_child - _MAX_AGE_PARENTING, year_child - _MIN_AGE_PARENTING


def full_name_from_record(d: Bautizo | Defuncion):
  return FullName(d.nombre, d.apellido_1, d.apellido_2)


def get_dummy_tree(info: SearchInfo) -> Tree:
  t = Tree(baut=Bautizo(
      nombre=info.nombre, apellido_1= info.apellido_1, apellido_2= info.apellido_2, year=0))
  if info.nombre_padre:
    t.padre = Tree(
        baut=Bautizo(nombre=info.nombre_padre, apellido_1=info.apellido_1, apellido_2=None, year=0),
        defu= None, padre=None, madre=None)
  if info.nombre_madre:
    t.madre = Tree(
        baut=Bautizo(nombre=info.nombre_madre, apellido_1=info.apellido_2, apellido_2=None, year=0),
        defu= None, padre=None, madre=None)
  return t





def get_tree_parent_limited(parent: FullName):
  padre_info = SearchInfo(
      nombre=parent.nombre,
      apellido_1=parent.apellido_1,
      apellido_2=parent.apellido_2)
  return get_dummy_tree(padre_info)

def get_sets_abuelos(siblings):
  sets_of_abuelos = defaultdict(int)
  for sibling in siblings:
    abuelos = sibling.get_abuelos()
    if abuelos.count(None) > 2:
      sets_of_abuelos["Invalido"] += 1
      continue
    abuelos_id = ""
    for x in abuelos:
      if not x:
        abuelos_id += "_|"
      else:
        abuelos_id += x.nombre+"|"
    abuelos_id = abuelos_id[:-1]
    sets_of_abuelos[abuelos_id] += 1
  return sets_of_abuelos



@dataclass
class Findings:
  full_matches: list
  partial_matches: list
  broad_matches: list

def find_person_abstract_v2(sheet: dict, info: SearchInfo, year_range:Tuple[int,int]|None):
  full_matches = []
  partial_matches = []
  broad_matches = []
  for year,baut in sheet.items():
    if year_range:
      min_year, max_year = year_range
      if not (min_year <= year <= max_year):
        continue
    for r in baut:
      name_match = match_cell(r.nombre, info.nombre)
      surnames_match = [
          match_cell(r.apellido_1, info.apellido_1),
           match_cell(r.apellido_2, info.apellido_2)]
      father_match = match_cell(r.padre.nombre, info.nombre_padre) if r.padre else Match.MISSING_INFO
      mother_match = match_cell(r.madre.nombre, info.nombre_madre) if r.madre else Match.MISSING_INFO
      this_matches = [name_match, father_match, mother_match]+surnames_match
      if Match.NO in this_matches:
        continue
      if Match.TOTAL in this_matches and Match.MISSING_INFO not in this_matches:
        full_matches.append(r)
      elif Match.MISSING_INFO in this_matches and Match.TOTAL in this_matches:
        # If 4 out of 5 fields match
        if this_matches.count(Match.TOTAL) == 4:
          partial_matches.append(r)
        # 3/5
        elif this_matches.count(Match.TOTAL) == 3:
          broad_matches.append(r)
  return Findings(full_matches, partial_matches, broad_matches)


def get_person_from_findings(fin: Findings, logger: Logger, name_record: str):
  broad_match= ""
  if fin.full_matches:
    records = fin.full_matches
  elif fin.partial_matches:
    records = fin.partial_matches
  else:
    records = fin.broad_matches
    broad_match = " (concindencia parcial) "

  if len(records) == 0:
    return None
  elif len(records) == 1:
    logger.log_accum(f"{name_record.title()} encontrado{broad_match}:")
    logger.log_accum(records[0])
    logger.log_flush()
    return records[0]
  else:
    logger.log_accum(f"Varios {name_record}/s encontrados{broad_match}, no se ha elegido ninguno.")
    for r in records:
      logger.log_accum(f" → {r}")
    logger.log_flush()
    return None

class Gen:
  sheets: Sheets
  def __init__(self, sheets):
    self.sheets = sheets

  def find_person(self,info: SearchInfo):
    year_range = None
    if info.year_child:
      year_range = get_parenting_age_birth_range(info.year_child)
    return find_person_abstract_v2(self.sheets.baut_by_year, info, year_range)

  def find_person_defu(self, info: SearchInfo):
    year_range = None
    if info.year_child:
      year_range = (info.year_child-1, info.year_child+_MAX_LIFESPAN_AFTER_PARENTING)
    return find_person_abstract_v2(self.sheets.defu_by_year, info, year_range)

  def find_matr(self,padre:FullName, madre: FullName, year_child):
    year_range = None
    if year_child:
      # e.g. child born in 1800
      # parents married [1756 (1800-60+16),1800]
      year_range = (
          year_child-_MAX_AGE_PARENTING+_MIN_AGE_PARENTING
          ,year_child)

    full_matches = []
    partial_matches = []
    broad_matches = []

    for year,baut in self.sheets.matr_by_year.items():
      if year_range:
        min_year, max_year = year_range
        if not (min_year <= year <= max_year):
          continue

      for r in baut:
        man_name_match = match_cell(r["Nombre_El"], padre.nombre)
        man_surnames_match = [
            match_cell(r["Apellido_1_El"], padre.apellido_1),
             (match_cell(r["Apellido_2_El"], padre.apellido_2))]
        woman_name_match = match_cell(r["Nombre_Ella"], madre.nombre)
        woman_surnames_match = [
            match_cell(r["Apellido_1_Ella"], madre.apellido_1),
             (match_cell(r["Apellido_2_Ella"], madre.apellido_2))]
        this_matches = [man_name_match, woman_name_match]+man_surnames_match+woman_surnames_match

        if Match.NO in this_matches:
          continue
        if Match.TOTAL in this_matches and Match.MISSING_INFO not in this_matches:
          full_matches.append(r)
        elif Match.MISSING_INFO in this_matches and Match.TOTAL in this_matches:
          # 4/6 campos
          # Apellido 2 casi siempre esta vacio en madre y padre asi que no tiene
          # sentido pedir mas de 4
          if this_matches.count(Match.TOTAL) >= 4:
            partial_matches.append(r)
          elif this_matches.count(Match.TOTAL) >= 3:
            broad_matches.append(r)
    return Findings(full_matches, partial_matches, broad_matches)


  def get_tree_parent_from_baut_v2(self, abuelo: FullName, abuela: FullName, apellido_parent: str, parent: FullName, year:int):
    padre_info = SearchInfo(
        nombre=parent.nombre,
        apellido_1=parent.apellido_1 or abuelo.apellido_1 or apellido_parent,
        apellido_2=parent.apellido_2 or abuela.apellido_1,
        nombre_padre=abuelo.nombre,
        nombre_madre=abuela.nombre,
        year_child=year)
    return self.get_ancestors(padre_info)


  def get_ancestors(self, info: SearchInfo) -> Tree:
    if not info.nombre:
      print(f"{info} - Info falta nombre")
    elif not info.apellido_1:
      print(f"{info} - Info falta apellido 1")
    elif not info.apellido_2:
      print(f"{info} - Info falta apellido 2")
    elif not info.nombre_padre:
      print(f"{info} - Info falta nombre padre")
    elif not info.nombre_madre:
      print(f"{info} - Info falta nombre madre")

    id = str(uuid.uuid4())[:8]
    logger = Logger(id, str(info))

    baut = get_person_from_findings(self.find_person(info), logger, "bautizo")
    # TODO: If baut then limit defu search based on birth date
    defuncion = get_person_from_findings(self.find_person_defu(info), logger, "defuncion")


    siblings_fin = self.find_person(replace(info, nombre=None))
    # Since nombre=None, that's already partial match, so consider broad_match
    siblings = siblings_fin.full_matches or siblings_fin.partial_matches or siblings_fin.broad_matches
    n_siblings = 0
    if siblings:
      n_siblings = len(siblings)-(1 if baut else 0)


    # If no birth was found try to infer parents from siblings, currently it
    # uses the first sibling TODO:Make it smarter, e.g. choose one with grandparents cells
    baut_ref = baut
    inferred_from_siblings = False

    if siblings:
      logger.log_accum(f"Hermanos potenciales:")
      for s in siblings:
        logger.log_accum(f" → {s}")

    if not baut_ref and siblings and _INFER_PARENTS_FROM_SIBLINGS:
      sets_of_abuelos = get_sets_abuelos(siblings)
      if len(sets_of_abuelos.keys()) == 1:
        baut_ref = siblings[0]
        inferred_from_siblings = True
        logger.log_accum(f"Deducido datos de potencial hermano: {baut_ref.nombre}.")
      else:
        list_abuelos = sorted(sets_of_abuelos.items(),key=lambda x:x[0])
        primeros_abuelos = list_abuelos[0][0]
        abuelos_names = set(str(i) + x for i,x in enumerate(primeros_abuelos.split("|")))
        same_abuelos = True
        for s,_ in list_abuelos[1:]:
          new_names = [str(i) + x for i,x in enumerate(s.split("|"))]
          n_match = len(abuelos_names.intersection(new_names))
          if n_match < 3:
            same_abuelos = False
            break

        if not same_abuelos:
          logger.log_accum(f"No se pueden deducir datos de los hermanos pues no todos los hermanos tienen los mismos abuelos.")
        else:
          baut_ref = siblings[0]
          inferred_from_siblings = True
          logger.log_accum(f"Deducido datos de potentical hermano: {baut_ref}.")
          logger.log_accum("Los abuelos de los hermanos difieren solo en un nombre.")
        for s,n in list_abuelos:
          logger.log_accum(str(n)+"  "+str(s))
    logger.log_flush()


    r = baut_ref or defuncion
    apellido_1 = r.apellido_1 if r and r.apellido_1 else info.apellido_1
    apellido_2 = r.apellido_2 if r and r.apellido_2 else info.apellido_2
    year_birth = baut_ref.year if baut_ref else None
    if r and r.padre:
      zpadre = replace(r.padre, apellido_1=r.padre.apellido_1 or info.apellido_1)
    else:
      zpadre = FullName(info.nombre_padre, info.apellido_1)
    if r and r.madre:
      zmadre = replace(r.madre, apellido_1=r.madre.apellido_1 or info.apellido_2)
    else:
      zmadre = FullName(info.nombre_madre, info.apellido_2)

    # If we don't find anyhting better we just keep this
    padre = get_tree_parent_limited(zpadre)
    madre = get_tree_parent_limited(zmadre)


    has_maternos = baut_ref and baut_ref.materno and baut_ref.materna
    has_paternos = baut_ref and baut_ref.paterno and baut_ref.paterna
    # TODO: Clarify the whole float.nan, "nan", "Missing" situation to make it clear
    if has_paternos:
      padre = self.get_tree_parent_from_baut_v2(baut_ref.paterno, baut_ref.paterna, baut_ref.apellido_1, baut_ref.padre, year_birth)

    if has_maternos:
      madre = self.get_tree_parent_from_baut_v2(baut_ref.materno, baut_ref.materna, baut_ref.apellido_2, baut_ref.madre, year_birth)

    #if not baut_ref or not baut_ref.padre or not baut_ref.madre or not has_maternos or not has_paternos:
    # Try to find abuelos from marrage of parents
    # Sometimes the parent cell contains the surname(s)
    matrs_fin = self.find_matr(zpadre, zmadre, year_child=year_birth)
    matrs = matrs_fin.full_matches or matrs_fin.partial_matches
    if len(matrs) == 1:
      matr = matrs[0]
      if has_paternos or has_maternos: #No necesitamos inferir nada, solo informacion
        logger.log_accum(f"Encontrado matrimonio de los padres:")
        logger.log_accum(matr)
      elif not (matr["Padres_Ella"] or type(matr["Padres_Ella"]) is not float):
        logger.log_accum(f"Encontrado matrimonio de los padres pero NO aparecen los abuelos:")
        logger.log_accum(matr)
      else:
        logger.log_accum(f"Encontrado matrimonio de los padres. Deducido los abuelos:")
        logger.log_accum(matr)
        abuelos_paternos = matr["Padres_El"]
        abuelos_maternos = matr["Padres_Ella"]
        if paternos := get_abuelos(abuelos_paternos):
          paterno,paterna = paternos
          padre = self.get_tree_parent_from_baut_v2(paterno,paterna,apellido_1, zpadre, year_birth)
        if maternos := get_abuelos(abuelos_maternos):
          materno,materna = maternos
          madre = self.get_tree_parent_from_baut_v2(materno,materna, apellido_2, zmadre, year_birth)
    elif len(matrs) > 1:
      logger.log_accum(f"Varios potenciales matrimonios de los padres encontrados. No se ha elegido ninguno:")
      for m in matrs:
        logger.log_accum(f" → {m}")
    elif not has_maternos or not has_maternos:
      logger.log_accum(f"Matrimonio de los padres no encontrado. No se pueden deducir los abuelos.")
      if matrs_fin.broad_matches:
        logger.log_accum("Las siguientes opciones han sido descartadas:")
        for x in matrs_fin.broad_matches:
          logger.log_accum(f" → {x}")

    logger.log_flush()

    # To log the name of the person in the tree
    if not baut:
      baut = get_dummy_tree(info).baut

    return Tree(id=id,baut=baut, defu=defuncion, padre= padre, madre= madre, n_siblings=n_siblings, inferred_from_siblings=inferred_from_siblings)

def get_tree_size(t: Tree|None):
  if not t:
    return 0
  padre = get_tree_size(t.padre)
  madre = get_tree_size(t.madre)
  return 1 + padre + madre

def print_tree(d: Tree, level: int = 0, is_last: bool = False, padding=""):
  if d is None:
    return
  year_baut = ""
  year_defu = ""
  full_name = ""
  record = ""
  if d.baut:
    full_name = full_name_from_record(d.baut)
    record = d.baut
    year_baut = d.baut.year
  if d.defu:
    year_defu = d.defu.year
    # If year_baut is 0 it means it is a dummy bautizo
    if not record or not year_baut:
      record = d.defu
    if not d.baut:
      full_name = full_name_from_record(d.defu)

  years = ""
  if year_baut or year_defu:
    y1 = str(year_baut) if year_baut else ""
    y2 = str(year_defu) if year_defu else ""
    years = f" ({y1}-{y2})"

  arrow = ""
  if level:
    arrow = "└── " if is_last else "├── "

  n_siblings = ""
  if d.n_siblings and not d.inferred_from_siblings:
    n_siblings = f" [*{d.n_siblings}] "
  elif d.n_siblings and d.inferred_from_siblings:
    n_siblings = f" [!{d.n_siblings}] "

  if years:
    print(f"{padding}{arrow}{full_name}{years}{n_siblings} [{record}] ")
  else: # We don't have any record:
    print(f"{padding}{arrow}{full_name}{years}{n_siblings} ")

  if level:
    if is_last:
      padding += "    "
    else:
      padding += "│   "
  print_tree(d.padre, level+1, False, padding)
  print_tree(d.madre, level+1, True, padding)


def get_tree_html(d: Tree, level: int = 0, is_last: bool = False, padding=""):
  if d is None:
    return ""
  year_baut = ""
  year_defu = ""
  full_name = ""
  if d.baut:
    full_name = full_name_from_record(d.baut)
    year_baut = d.baut.year
  if d.defu:
    year_defu = d.defu.year
    if not d.baut:
      full_name = full_name_from_record(d.defu)

  years = ""
  if year_baut or year_defu:
    y1 = str(year_baut) if year_baut else ""
    y2 = str(year_defu) if year_defu else ""
    years = f" ({y1}-{y2})"

  arrow = ""
  if level:
    arrow = "└──&nbsp;" if is_last else "├──&nbsp;"

  n_siblings = ""
  if d.n_siblings and not d.inferred_from_siblings:
    n_siblings = f" [*{d.n_siblings}] "
  elif d.n_siblings and d.inferred_from_siblings:
    n_siblings = f" [!{d.n_siblings}] "

  if context_map[d.id]:
    s = f"<span id='person_{d.id}' class='person' onclick='show_context(\"{d.id}\")' style='cursor:pointer'>{padding}{arrow}<b>{full_name}</b>{years}{n_siblings}</span><br>"
  else:
    s = f"<span id='person_{d.id}' class='person' onclick='show_context(\"{d.id}\")'>{padding}{arrow}{full_name}{years}{n_siblings}</span><br>"
  #output += s

  if level:
    if is_last:
      padding += "&nbsp;&nbsp;&nbsp;&nbsp;"
    else:
      padding += "│&nbsp;&nbsp;&nbsp;"
  p1 = get_tree_html(d.padre, level+1, False, padding)
  p2 = get_tree_html(d.madre, level+1, True, padding)
  return s + p1 + p2

def get_webpage(tree):
    output = get_tree_html(tree)
    context_html = ""
    for id, l in context_map.items():
        context_person = f"<div id='context_{id}' style='display:none'>"
        for s in l:
            context_person += f"{s}<br>"
        context_person += f"</div>"
        context_html += f"{context_person}"
    
    c = """
    <html>
    <meta charset="UTF-8">
    <style>
    .highlighted {
        background-color: #afddf9;
        padding: 2px;
        padding-left: 0px;
        border-radius: 3px;
        transition: background-color 0.3s ease;
    }
    </style>
    <script>
    let currentHighlightedId = null;
    
    function show_context(id) {
        // Update context
        var z = document.getElementById("context_"+id).innerHTML;
        document.getElementById("context").innerHTML = z;
        
        // Remove previous highlight
        if (currentHighlightedId) {
            const prevElement = document.getElementById("person_"+currentHighlightedId);
            if (prevElement) {
                prevElement.classList.remove('highlighted');
            }
        }
        
        // Add new highlight
        const newElement = document.getElementById("person_"+id);
        if (newElement) {
            newElement.classList.add('highlighted');
        }
        
        // Update current highlighted ID
        currentHighlightedId = id;
    }
    </script>
    <div id="context" style="border: solid 1px; font-family:'Open Sans', sans-serif; height:25vh;position: fixed; top: 0; left: 0; right: 0; width: 100%; max-height: 25vh; overflow-y: auto; background-color: #f9f9f9; padding: 10px; border-bottom: 1px solid #ccc; box-sizing: border-box; z-index: 1000;">
    ...
    </div>
    <div id="tree" style="font-family: Consolas, 'Courier New', monospace;padding-top: 25vh">
    """
    c += f"""
    {output}
    </div>
    <hr>
    {context_html}
    """
    c += """
    <script>
    function redirectToTree() {
        const tree = document.getElementById("tree");
        // Scroll into view smoothly
        tree.scrollIntoView({ behavior: "smooth", block: "start" });
        // Update the URL hash
        window.location.hash = "tree";
    }
    redirectToTree();
    </script>
    </html>
    """
    return c

def get_year_ranges(nums) -> []:
  if not nums:
      return []

  ranges = []
  start = nums[0]

  for i in range(1, len(nums)):
      if nums[i] != nums[i - 1] + 1:  # Check if the current number is not consecutive
          end = nums[i - 1]
          if start == end:
              ranges.append(str(start))  # Single number range
          else:
              ranges.append(f"{start}-{end}")  # Range from start to end
          start = nums[i]

  # Add the last range
  if start == nums[-1]:
      ranges.append(str(start))
  else:
      ranges.append(f"{start}-{nums[-1]}")

  return ranges