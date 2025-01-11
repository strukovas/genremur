import streamlit.components.v1 as components
import streamlit as st
import pandas as pd
import lib
import pip
pip.main(["install", "python-calamine"])

st.set_page_config(layout="wide")
# Show title and description.
st.title("(GenReMur) Buscador Recursivo de antepasados Murcia")
st.markdown("""
            Descarga el archivo Excel del pueblo que te interese [aquí](https://onedrive.live.com/?authkey=%21AI%2DjU1MqxB9G8oM&id=BF237BB486352469%21510525&cid=BF237BB486352469). 
            Confirma que está en el Excel la persona cuyos ancestros quieres buscar. A continuación sube el Excel a esta web e introduce los datos de dicha persona (mínimo 3 campos). 
            El programa buscará los datos de sus padres, abuelos, bisabuelos, etc.  \n
            La documentación del programa está disponible [aquí](https://github.com/strukovas/genremur#GenReMur). Consúltala ante cualquier duda. \n
            ¿Te interesa simplemente ver un ejemplo? Busca en Abarán a Aurelio Castaño Molina (padres Antonio y Trinidad).
            """
)


@st.fragment
def upload_widget():
    # Let the user upload a file via `st.file_uploader`.
    uploaded_file = st.file_uploader("", type=("xlsx"),
        help="Sube aquí el archivo Excel. El concimiento del programa está limitado a este archivo."
    )

    if uploaded_file:
        with st.spinner('(1) Cargando Excel, limpiando datos, marcando celdas ausentes, estandarizando nombres...'):
            baut_all, matr_all, defu_all = lib.load_all_sheets_in_colab(
                uploaded_file.read())

        with st.spinner('(2) Separando nombre y apellidos, agrupando datos por año...'):
            from collections import defaultdict
            defu_by_year: dict[int, list] = defaultdict(list)
            for year, group in defu_all.groupby('Año'):
                for _, row in group.iterrows():
                    if x := lib.Defuncion.defu_from_series(row):
                        defu_by_year[year].append(x)
            baut_by_year: dict[int, list] = defaultdict(list)
            for year, group in baut_all.groupby('Año'):
                for _, row in group.iterrows():
                    if x := lib.Bautizo.baut_from_series(row):
                        baut_by_year[year].append(x)

            matr_by_year = {year: group.to_dict(
                'records') for year, group in matr_all.groupby('Año')}
            sheets = lib.Sheets(
                baut_by_year=baut_by_year, matr_by_year=matr_by_year, defu_by_year=defu_by_year)
            st.session_state["sheets"] = sheets

            year_baut = ", ".join(
                lib.get_year_ranges(list(baut_by_year.keys())))
            year_matr = ", ".join(
                lib.get_year_ranges(list(matr_by_year.keys())))
            year_defu = ", ".join(
                lib.get_year_ranges(list(defu_by_year.keys())))
            st.markdown(
                f"Excel procesado con éxito. Contiene los siguientes registros:  \n{len(baut_all)} Bautizos (Años: {year_baut})  \n{len(matr_all)} Matrimonios (Años: {year_matr})  \n{len(defu_all)} Defunciones (Años: {year_defu})")


@st.fragment
def person_form():
    with st.form(key='columns_in_form', enter_to_submit=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            nombre_val = st.text_input("Nombre")
            nombre_padre_val = st.text_input("Nombre Padre (sin apellidos)")
        with col2:
            apellido_1_val = st.text_input("Apellido 1")
            nombre_madre_val = st.text_input("Nombre Madre (sin apellidos)")
        with col3:
            apellido_2_val = st.text_input("Apellido 2")
            st.write('<div style="height: 28px;"></div>',
                     unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "Buscar", use_container_width=True)

    if submitted:
        if "sheets" in st.session_state:
            error = ""
            n_missing = 0
            if not nombre_val:
                error += "Campo 'Nombre' vacío.  \n"
                n_missing += 1
            if not apellido_1_val:
                error += "Campo 'Apellido 1' vacío.  \n"
                n_missing += 1
            if not apellido_2_val:
                error += "Campo 'Apellido 2' vacío.  \n"
                n_missing += 1
            if not nombre_padre_val:
                error += "Campo 'Nombre Padre' vacío.  \n"
                n_missing += 1
            if not nombre_madre_val:
                error += "Campo 'Nombre Madre' vacío.  \n"
                n_missing += 1
            if n_missing > 2:
                error += "**No puede haber más de 2 campos vacíos**. Intenta rellenarlos todos.  \n"
                st.markdown(error)
            else:
                nombre = (nombre_val if nombre_val else "_")
                apellido1 = (apellido_1_val if apellido_1_val else "_")
                apellido2 = (apellido_2_val if apellido_2_val else "_")
                with st.spinner(f'(3) Buscando antepasados de {nombre} {apellido1} {apellido2}...'):
                    g = lib.Gen(sheets=st.session_state['sheets'])
                    z = g.get_ancestors(lib.SearchInfo(
                        nombre_val,
                        apellido_1_val,
                        apellido_2_val,
                        nombre_padre_val,
                        nombre_madre_val,
                    ))
                    webpage = lib.get_webpage(z)
                    size = lib.get_tree_size(z)
                    if size <= 3:
                        st.markdown(
                            "**No se ha encontrado a esta persona en el Excel**")
                    else:
                        st.markdown(f"Deducido árbol con {size} miembros")
                components.html(webpage, height=700, scrolling=True)
        else:
            st.markdown(
                "**Antes de continuar debes subir un Excel en el que buscar**.")


upload_widget()
person_form()


with open('./files/styles.css') as f:
    css = f.read()

st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
