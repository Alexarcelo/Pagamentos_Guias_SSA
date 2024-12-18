import streamlit as st
import pandas as pd
import mysql.connector
import decimal
from babel.numbers import format_currency
import gspread 
import requests
from datetime import time
from google.cloud import secretmanager 
import json
from google.oauth2.service_account import Credentials

def gerar_df_phoenix(vw_name, base_luck):

    # Parametros de Login AWS
    config = {
    'user': 'user_automation_jpa',
    'password': 'luck_jpa_2024',
    'host': 'comeia.cixat7j68g0n.us-east-1.rds.amazonaws.com',
    'database': base_luck
    }
    # Conexão as Views
    conexao = mysql.connector.connect(**config)
    cursor = conexao.cursor()

    request_name = f'SELECT * FROM {vw_name}'

    # Script MySql para requests
    cursor.execute(
        request_name
    )
    # Coloca o request em uma variavel
    resultado = cursor.fetchall()
    # Busca apenas o cabecalhos do Banco
    cabecalho = [desc[0] for desc in cursor.description]

    # Fecha a conexão
    cursor.close()
    conexao.close()

    # Coloca em um dataframe e muda o tipo de decimal para float
    df = pd.DataFrame(resultado, columns=cabecalho)
    df = df.applymap(lambda x: float(x) if isinstance(x, decimal.Decimal) else x)
    return df

def puxar_dados_phoenix():

    st.session_state.df_escalas_bruto = gerar_df_phoenix('vw_pagamento_guias', 'test_phoenix_salvador')

    st.session_state.df_escalas = st.session_state.df_escalas_bruto[~(st.session_state.df_escalas_bruto['Status da Reserva'].isin(['CANCELADO', 'PENDENCIA DE IMPORTAÇÃO'])) & 
                                                                    ~(pd.isna(st.session_state.df_escalas_bruto['Status da Reserva'])) & ~(pd.isna(st.session_state.df_escalas_bruto['Escala'])) & 
                                                                    ~(pd.isna(st.session_state.df_escalas_bruto['Guia']))].reset_index(drop=True)
    
    st.session_state.df_cnpj_fornecedores = st.session_state.df_escalas_bruto[~pd.isna(st.session_state.df_escalas_bruto['Guia'])]\
        [['Guia', 'CNPJ/CPF Fornecedor Guia', 'Razao Social/Nome Completo Fornecedor Guia']].drop_duplicates().reset_index(drop=True)
    
def inserir_infos_dataframe(id_gsheet, aba_excel, df_insercao):
    
    # GCP projeto onde está a chave credencial
    project_id = "grupoluck"

    # ID da chave credencial do google.
    secret_id = "cred-luck-aracaju"

    # Cria o cliente.
    secret_client = secretmanager.SecretManagerServiceClient()

    secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = secret_client.access_secret_version(request={"name": secret_name})

    secret_payload = response.payload.data.decode("UTF-8")

    credentials_info = json.loads(secret_payload)

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    # Use the credentials to authorize the gspread client
    credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
    client = gspread.authorize(credentials)
    
    # Abertura da planilha e aba
    spreadsheet = client.open_by_key(id_gsheet)
    sheet = spreadsheet.worksheet(aba_excel)
    
    # Limpeza do intervalo A2:Z10000
    sheet.batch_clear(["A2:AR10000"])
    data = df_insercao.values.tolist()
    start_cell = "A2"  # Sempre insere a partir da segunda linha
    sheet.update(start_cell, data)

def puxar_aba_simples(id_gsheet, nome_aba, nome_df):

    # GCP projeto onde está a chave credencial
    project_id = "grupoluck"

    # ID da chave credencial do google.
    secret_id = "cred-luck-aracaju"

    # Cria o cliente.
    secret_client = secretmanager.SecretManagerServiceClient()

    secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = secret_client.access_secret_version(request={"name": secret_name})

    secret_payload = response.payload.data.decode("UTF-8")

    credentials_info = json.loads(secret_payload)

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    # Use the credentials to authorize the gspread client
    credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(id_gsheet)
    
    sheet = spreadsheet.worksheet(nome_aba)

    sheet_data = sheet.get_all_values()

    st.session_state[nome_df] = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])

def inserir_config(df_itens_faltantes, id_gsheet, nome_aba):

    # GCP projeto onde está a chave credencial
    project_id = "grupoluck"

    # ID da chave credencial do google.
    secret_id = "cred-luck-aracaju"

    # Cria o cliente.
    secret_client = secretmanager.SecretManagerServiceClient()

    secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = secret_client.access_secret_version(request={"name": secret_name})

    secret_payload = response.payload.data.decode("UTF-8")

    credentials_info = json.loads(secret_payload)

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    # Use the credentials to authorize the gspread client
    credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
    client = gspread.authorize(credentials)
    
    spreadsheet = client.open_by_key(id_gsheet)

    sheet = spreadsheet.worksheet(nome_aba)

    sheet.batch_clear(["A2:Z100"])

    data = df_itens_faltantes.values.tolist()
    sheet.update('A2', data)

def transformar_em_listas(idiomas):

    return list(set(idiomas))

def transformar_em_string(apoio):

    return ', '.join(list(set(apoio.dropna())))

def tratar_colunas_idioma(df_escalas_group):
    
    df_idiomas = df_escalas_group[df_escalas_group['Idioma'].apply(lambda idiomas: idiomas != ['pt-br'])].reset_index()

    df_idiomas['Idioma'] = df_idiomas['Idioma'].apply(lambda idiomas: ', '.join([idioma for idioma in idiomas if idioma != 'pt-br']))

    df_escalas_group['Idioma'] = ''

    for index, index_principal in df_idiomas['index'].items():

        df_escalas_group.at[index_principal, 'Idioma'] = df_idiomas.at[index, 'Idioma']

    df_escalas_group['Idioma'] = df_escalas_group['Idioma'].replace({'all': 'en-us', 'it-ele': 'en-us'})

    return df_escalas_group

def verificar_tarifarios(df_escalas_group, id_gsheet):

    lista_passeios = df_escalas_group['Servico'].unique().tolist()

    lista_passeios_tarifario = st.session_state.df_tarifario['Servico'].unique().tolist()

    lista_passeios_sem_tarifario = [item for item in lista_passeios if not item in lista_passeios_tarifario]

    if len(lista_passeios_sem_tarifario)>0:

        df_itens_faltantes = pd.DataFrame(lista_passeios_sem_tarifario, columns=['Serviços'])

        st.dataframe(df_itens_faltantes, hide_index=True)

        # GCP projeto onde está a chave credencial
        project_id = "grupoluck"
    
        # ID da chave credencial do google.
        secret_id = "cred-luck-aracaju"
    
        # Cria o cliente.
        secret_client = secretmanager.SecretManagerServiceClient()
    
        secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = secret_client.access_secret_version(request={"name": secret_name})
    
        secret_payload = response.payload.data.decode("UTF-8")
    
        credentials_info = json.loads(secret_payload)
    
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    
        # Use the credentials to authorize the gspread client
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        client = gspread.authorize(credentials)
        
        spreadsheet = client.open_by_key(id_gsheet)

        sheet = spreadsheet.worksheet('Tarifário Robô')
        sheet_data = sheet.get_all_values()
        last_filled_row = len(sheet_data)
        data = df_itens_faltantes.values.tolist()
        start_row = last_filled_row + 1
        start_cell = f"A{start_row}"
        
        sheet.update(start_cell, data)

        st.error('Os serviços acima não estão tarifados. Eles foram inseridos no final da planilha de tarifários. Por favor, tarife os serviços e tente novamente')

        st.stop()

    else:

        st.success('Todos os serviços estão tarifados!')

def indentificar_motoguias(df_escalas_pag):

    df_escalas_pag['Motoguia'] = ''

    df_escalas_pag.loc[(df_escalas_pag['Motorista']==df_escalas_pag['Guia']), 'Motoguia'] = 'X'

    return df_escalas_pag

def identificar_trf_ln_diurno_noturno(df_escalas_group):

    mask_ln_noturnos = (df_escalas_group['Servico'].isin([' OUT -  LITORAL NORTE ', 'IN  - LITORAL NORTE '])) & \
        (((pd.to_datetime(df_escalas_group['Horario Voo']).dt.time >= time(18,0)) | (pd.to_datetime(df_escalas_group['Horario Voo']).dt.time <= time(5,0))) | 
         ((pd.to_datetime(df_escalas_group['Data | Horario Apresentacao']).dt.time >= time(18,0)) | (pd.to_datetime(df_escalas_group['Data | Horario Apresentacao']).dt.time <= time(5,0))))
    
    mask_ln_diurnos = (df_escalas_group['Servico'].isin([' OUT -  LITORAL NORTE ', 'IN  - LITORAL NORTE '])) & \
        ~(((pd.to_datetime(df_escalas_group['Horario Voo']).dt.time >= time(18,0)) | (pd.to_datetime(df_escalas_group['Horario Voo']).dt.time <= time(5,0))) | 
         ((pd.to_datetime(df_escalas_group['Data | Horario Apresentacao']).dt.time >= time(18,0)) | (pd.to_datetime(df_escalas_group['Data | Horario Apresentacao']).dt.time <= time(5,0))))

    df_escalas_group.loc[mask_ln_noturnos, 'Servico'] = df_escalas_group['Servico'] + ' - NOTURNO'

    df_escalas_group.loc[mask_ln_diurnos, 'Servico'] = df_escalas_group['Servico'] + ' - DIURNO'

    return df_escalas_group

def criar_colunas_escala_veiculo_mot_guia(df_apoios):

    df_apoios[['Escala Apoio', 'Veiculo Apoio', 'Motorista Apoio', 'Guia Apoio']] = ''

    df_apoios['Apoio'] = df_apoios['Apoio'].str.replace('Escala Auxiliar: ', '', regex=False)

    df_apoios['Apoio'] = df_apoios['Apoio'].str.replace(' Veículo: ', '', regex=False)

    df_apoios['Apoio'] = df_apoios['Apoio'].str.replace(' Motorista: ', '', regex=False)

    df_apoios['Apoio'] = df_apoios['Apoio'].str.replace(' Guia: ', '', regex=False)

    df_apoios[['Escala Apoio', 'Veiculo Apoio', 'Motorista Apoio', 'Guia Apoio']] = \
        df_apoios['Apoio'].str.split(',', expand=True)
    
    return df_apoios

def adicionar_apoios_em_dataframe(df_escalas_pag):

    df_escalas_com_apoio = df_escalas_pag[(df_escalas_pag['Apoio']!='') & (~df_escalas_pag['Apoio'].str.contains(r' \| ', regex=True))].reset_index(drop=True)

    if len(df_escalas_com_apoio)>0:

        df_escalas_com_apoio = criar_colunas_escala_veiculo_mot_guia(df_escalas_com_apoio)

        df_apoios_group = df_escalas_com_apoio.groupby(['Escala Apoio', 'Veiculo Apoio', 'Motorista Apoio', 'Guia Apoio']).agg({'Data da Escala': 'first', 'Data | Horario Apresentacao': 'first'}).reset_index()

        df_apoios_group = df_apoios_group.rename(columns={'Veiculo Apoio': 'Veiculo', 'Motorista Apoio': 'Motorista', 'Guia Apoio': 'Guia', 'Escala Apoio': 'Escala'})

        df_apoios_group = df_apoios_group[['Data da Escala', 'Escala', 'Veiculo', 'Motorista', 'Guia', 'Data | Horario Apresentacao']]

        df_apoios_group[['Servico', 'Tipo de Servico', 'Modo', 'Apoio', 'Idioma', 'Total ADT | CHD', 'Horario Voo']] = ['APOIO', 'TRANSFER', 'REGULAR', None, '', 0, time(0,0)]
        
        df_apoios_group = df_apoios_group[df_apoios_group['Guia']!='null'].reset_index(drop=True)

        df_escalas_pag = pd.concat([df_escalas_pag, df_apoios_group], ignore_index=True)

    df_escalas_com_2_apoios = df_escalas_pag[(df_escalas_pag['Apoio']!='') & (df_escalas_pag['Apoio'].str.contains(r' \| ', regex=True))].reset_index(drop=True)

    if len(df_escalas_com_2_apoios)>0:

        df_novo = pd.DataFrame(columns=['Escala', 'Veiculo', 'Motorista', 'Guia', 'Data | Horario Apresentacao', 'Data da Escala'])

        for index in range(len(df_escalas_com_2_apoios)):

            data_escala = df_escalas_com_2_apoios.at[index, 'Data da Escala']

            apoio_nome = df_escalas_com_2_apoios.at[index, 'Apoio']

            data_h_apr = df_escalas_com_2_apoios.at[index, 'Data | Horario Apresentacao']

            lista_apoios = apoio_nome.split(' | ')

            for item in lista_apoios:

                dict_replace = {'Escala Auxiliar: ': '', ' Veículo: ': '', ' Motorista: ': '', ' Guia: ': ''}

                for old, new in dict_replace.items():

                    item = item.replace(old, new)
                    
                lista_insercao = item.split(',')

                contador = len(df_novo)

                df_novo.at[contador, 'Escala'] = lista_insercao[0]

                df_novo.at[contador, 'Veiculo'] = lista_insercao[1]

                df_novo.at[contador, 'Motorista'] = lista_insercao[2]

                df_novo.at[contador, 'Guia'] = lista_insercao[3]

                df_novo.at[contador, 'Data | Horario Apresentacao'] = data_h_apr

                df_novo.at[contador, 'Data da Escala'] = data_escala

        df_novo = df_novo[df_novo['Guia']!='null'].reset_index(drop=True)

        df_novo[['Servico', 'Tipo de Servico', 'Modo', 'Apoio', 'Idioma', 'Total ADT | CHD', 'Horario Voo']] = ['APOIO', 'TRANSFER', 'REGULAR', None, '', 0, time(0,0)]

        df_escalas_pag = pd.concat([df_escalas_pag, df_novo], ignore_index=True)

    return df_escalas_pag

def definir_html(df_ref):

    html=df_ref.to_html(index=False, escape=False)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                text-align: center;  /* Centraliza o texto */
            }}
            table {{
                margin: 0 auto;  /* Centraliza a tabela */
                border-collapse: collapse;  /* Remove espaço entre as bordas da tabela */
            }}
            th, td {{
                padding: 8px;  /* Adiciona espaço ao redor do texto nas células */
                border: 1px solid black;  /* Adiciona bordas às células */
                text-align: center;
            }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """

    return html

def criar_output_html(nome_html, html, guia, soma_servicos):

    with open(nome_html, "w", encoding="utf-8") as file:

        file.write(f'<p style="font-size:40px;">{guia}</p>')

        file.write(f'<p style="font-size:30px;">Serviços prestados entre {st.session_state.data_inicial.strftime("%d/%m/%Y")} e {st.session_state.data_final.strftime("%d/%m/%Y")}</p>')

        file.write(f'<p style="font-size:30px;">CPF / CNPJ: {st.session_state.cnpj}</p>')

        file.write(f'<p style="font-size:30px;">Razão Social / Nome Completo: {st.session_state.razao_social}</p><br><br>')

        file.write(html)

        file.write(f'<br><br><p style="font-size:30px;">O valor total dos serviços é {soma_servicos}</p>')

        file.write(f'<p style="font-size:30px;">Data de Pagamento: {st.session_state.data_pagamento.strftime("%d/%m/%Y")}</p>')

def verificar_guia_sem_telefone(id_gsheet, guia, lista_guias_com_telefone):

    if not guia in lista_guias_com_telefone:

        lista_guias = []

        lista_guias.append(guia)

        df_itens_faltantes = pd.DataFrame(lista_guias, columns=['Guias'])

        st.dataframe(df_itens_faltantes, hide_index=True)

        # GCP projeto onde está a chave credencial
        project_id = "grupoluck"
    
        # ID da chave credencial do google.
        secret_id = "cred-luck-aracaju"
    
        # Cria o cliente.
        secret_client = secretmanager.SecretManagerServiceClient()
    
        secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = secret_client.access_secret_version(request={"name": secret_name})
    
        secret_payload = response.payload.data.decode("UTF-8")
    
        credentials_info = json.loads(secret_payload)
    
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    
        # Use the credentials to authorize the gspread client
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        client = gspread.authorize(credentials)
        
        spreadsheet = client.open_by_key(id_gsheet)

        sheet = spreadsheet.worksheet('Telefones Guias')
        sheet_data = sheet.get_all_values()
        last_filled_row = len(sheet_data)
        data = df_itens_faltantes.values.tolist()
        start_row = last_filled_row + 1
        start_cell = f"A{start_row}"
        
        sheet.update(start_cell, data)

        st.error(f'O guia {guia} não tem número de telefone cadastrado na planilha. Ele foi inserido no final da lista de guias. Por favor, cadastre o telefone dele e tente novamente')

        st.stop()

    else:

        telefone_guia = st.session_state.df_telefones.loc[st.session_state.df_telefones['Guias']==guia, 'Telefone'].values[0]

    return telefone_guia

st.set_page_config(layout='wide')

if not 'id_gsheet' in st.session_state:

    st.session_state.id_gsheet = '1TsOGz9-O1QcZiTnpT1tYiI0ZEBy1UCZ6qtV6iahLxFA'

if not 'id_webhook' in st.session_state:

    st.session_state.id_webhook = "https://conexao.multiatend.com.br/webhook/pagamentolucksalvador"

if not 'mostrar_config' in st.session_state:

        st.session_state.mostrar_config = False

if not 'df_config' in st.session_state:

    with st.spinner('Puxando configurações...'):

        puxar_aba_simples(st.session_state.id_gsheet, 'Configurações Guias', 'df_config')

with st.spinner('Puxando dados do Phoenix...'):

    if not 'df_escalas' in st.session_state:

        puxar_dados_phoenix()

st.title('Mapa de Pagamento - Guias')

st.divider()

st.header('Configurações')

alterar_configuracoes = st.button('Visualizar Configurações')

if alterar_configuracoes:

    if st.session_state.mostrar_config == True:

        st.session_state.mostrar_config = False

    else:

        st.session_state.mostrar_config = True

row01 = st.columns(1)

if st.session_state.mostrar_config == True:

    with row01[0]:

        st.subheader('Excluir Serviços')
        
        filtrar_servicos = st.multiselect('', sorted(st.session_state.df_escalas_bruto['Servico'].dropna().unique().tolist()), key='filtrar_servicos', 
                                          default=sorted(list(filter(lambda x: x != '', st.session_state.df_config['Excluir Servicos'].tolist()))))

    salvar_config = st.button('Salvar Configurações')

    if salvar_config:

        with st.spinner('Salvando Configurações...'):

            lista_escolhas = [filtrar_servicos]

            st.session_state.df_config = pd.DataFrame({f'Coluna{i+1}': pd.Series(lista) for i, lista in enumerate(lista_escolhas)})

            st.session_state.df_config = st.session_state.df_config.fillna('')

            inserir_config(st.session_state.df_config, st.session_state.id_gsheet, 'Configurações Guias')

            puxar_aba_simples(st.session_state.id_gsheet, 'Configurações Guias', 'df_config')

        st.session_state.mostrar_config = False

        st.rerun()

st.divider()

row1 = st.columns(2)

with row1[0]:

    container_datas = st.container(border=True)

    container_datas.subheader('Período')

    data_inicial = container_datas.date_input('Data Inicial', value=None ,format='DD/MM/YYYY', key='data_inicial')

    data_final = container_datas.date_input('Data Inicial', value=None ,format='DD/MM/YYYY', key='data_final')

    gerar_mapa = container_datas.button('Gerar Mapa de Pagamentos')

with row1[1]:

    atualizar_phoenix = st.button('Atualizar Dados Phoenix')

    container_data_pgto = st.container(border=True)

    container_data_pgto.subheader('Data de Pagamento')

    data_pagamento = container_data_pgto.date_input('Data de Pagamento', value=None ,format='DD/MM/YYYY', key='data_pagamento')

if atualizar_phoenix:

    with st.spinner('Puxando dados do Phoenix...'):

        puxar_dados_phoenix()

if gerar_mapa:

    # Puxando tarifários e tratando colunas de números

    with st.spinner('Puxando tarifários, ubers...'):

        puxar_aba_simples(st.session_state.id_gsheet, 'Tarifário Robô', 'df_tarifario')

        st.session_state.df_tarifario[['Valor', 'Valor Motoguia']] = st.session_state.df_tarifario[['Valor', 'Valor Motoguia']].apply(pd.to_numeric, errors='coerce')

        puxar_aba_simples(st.session_state.id_gsheet, 'Uber Guias', 'df_uber')

        st.session_state.df_uber[['Valor Uber']] = st.session_state.df_uber[['Valor Uber']].apply(pd.to_numeric, errors='coerce')

    # Filtrando período solicitado pelo usuário

    df_escalas = st.session_state.df_escalas[(st.session_state.df_escalas['Data da Escala'] >= data_inicial) & (st.session_state.df_escalas['Data da Escala'] <= data_final) & 
                                             (~st.session_state.df_escalas['Servico'].isin(list(filter(lambda x: x != '', st.session_state.df_config['Excluir Servicos'].tolist()))))]\
                                                .reset_index(drop=True)

    # Adicionando somatório de ADT e CHD

    df_escalas['Total ADT | CHD'] = df_escalas['Total ADT'] + df_escalas['Total CHD']

    # Agrupando escalas

    df_escalas_group = df_escalas.groupby(['Data da Escala', 'Escala', 'Veiculo', 'Motorista', 'Guia', 'Servico', 'Tipo de Servico', 'Modo'])\
        .agg({'Apoio': transformar_em_string,  'Idioma': transformar_em_listas, 'Total ADT | CHD': 'sum', 'Horario Voo': transformar_em_listas, 'Data | Horario Apresentacao': 'min'}).reset_index()
    
    # Tratando coluna Idioma

    df_escalas_group = tratar_colunas_idioma(df_escalas_group)

    # Pegando horário de último voo de cada escala

    df_escalas_group['Horario Voo'] = df_escalas_group['Horario Voo'].apply(lambda lista: max(lista) if isinstance(lista, list) and lista else None)

    # Alterando TRF LITORAL NORTE p/ Diurno e Noturno

    df_escalas_group = identificar_trf_ln_diurno_noturno(df_escalas_group)

    # Adicionando Apoios no dataframe de pagamentos

    df_escalas_group = adicionar_apoios_em_dataframe(df_escalas_group)

    # Verificando se todos os serviços estão tarifados

    verificar_tarifarios(df_escalas_group, st.session_state.id_gsheet)

    # Colocando valores tarifarios
    
    df_escalas_pag = pd.merge(df_escalas_group, st.session_state.df_tarifario, on='Servico', how='left')

    # Calculando adicional p/ tours como motoguia

    df_escalas_pag = indentificar_motoguias(df_escalas_pag)

    # Adicionando valor de uber por escala

    df_escalas_pag = df_escalas_pag.merge(st.session_state.df_uber[['Escala', 'Valor Uber']], on='Escala', how='left')

    df_escalas_pag['Valor Uber'] = df_escalas_pag['Valor Uber'].fillna(0)

    # Gerando Valor Serviço

    df_escalas_pag['Valor Serviço'] = df_escalas_pag.apply(lambda row: row['Valor Motoguia'] if row['Motoguia'] == 'X' else row['Valor'], axis=1)

    # Ajustando valores idioma

    df_escalas_pag.loc[df_escalas_pag['Idioma']!='', 'Valor Serviço'] = df_escalas_pag['Valor Serviço']*1.2

    # Gerando Valor Total

    df_escalas_pag['Valor Total'] = df_escalas_pag[(['Valor Serviço', 'Valor Uber'])].sum(axis=1)

    st.session_state.df_pag_final = df_escalas_pag[['Data da Escala', 'Modo', 'Tipo de Servico', 'Servico', 'Veiculo', 'Motorista', 'Guia', 'Idioma', 'Motoguia', 'Valor Uber', 'Valor Serviço', 
                                                    'Valor Total']]

if 'df_pag_final' in st.session_state:

    st.header('Gerar Mapas')

    row2 = st.columns(2)

    with row2[0]:

        lista_guias = st.session_state.df_pag_final['Guia'].dropna().unique().tolist()

        guia = st.selectbox('Guia', sorted(lista_guias), index=None)

    if guia and data_pagamento and data_inicial and data_final:

        st.session_state.cnpj = st.session_state.df_cnpj_fornecedores[st.session_state.df_cnpj_fornecedores['Guia']==guia]['CNPJ/CPF Fornecedor Guia'].iloc[0]

        st.session_state.razao_social = st.session_state.df_cnpj_fornecedores[st.session_state.df_cnpj_fornecedores['Guia']==guia]['Razao Social/Nome Completo Fornecedor Guia'].iloc[0]

        row2_1 = st.columns(4)

        df_pag_guia = st.session_state.df_pag_final[st.session_state.df_pag_final['Guia']==guia].sort_values(by=['Data da Escala', 'Veiculo', 'Motorista']).reset_index(drop=True)

        df_data_correta = df_pag_guia.reset_index(drop=True)

        df_data_correta['Data da Escala'] = pd.to_datetime(df_data_correta['Data da Escala'])

        df_data_correta['Data da Escala'] = df_data_correta['Data da Escala'].dt.strftime('%d/%m/%Y')

        container_dataframe = st.container()

        container_dataframe.dataframe(df_data_correta, hide_index=True, use_container_width = True)

        with row2_1[0]:

            total_a_pagar = df_pag_guia['Valor Total'].sum()

            st.subheader(f'Valor Total: R${int(total_a_pagar)}')

        df_pag_guia['Data da Escala'] = pd.to_datetime(df_pag_guia['Data da Escala'])

        df_pag_guia['Data da Escala'] = df_pag_guia['Data da Escala'].dt.strftime('%d/%m/%Y')

        soma_servicos = df_pag_guia['Valor Total'].sum()

        soma_servicos = format_currency(soma_servicos, 'BRL', locale='pt_BR')

        for item in ['Valor Uber', 'Valor Serviço', 'Valor Total']:

            df_pag_guia[item] = df_pag_guia[item].apply(lambda x: format_currency(x, 'BRL', locale='pt_BR'))

        html = definir_html(df_pag_guia)

        nome_html = f'{guia}.html'

        criar_output_html(nome_html, html, guia, soma_servicos)

        with open(nome_html, "r", encoding="utf-8") as file:

            html_content = file.read()

        with row2_1[1]:

            st.download_button(
                label="Baixar Arquivo HTML",
                data=html_content,
                file_name=nome_html,
                mime="text/html"
            )

        st.session_state.html_content = html_content

    else:

        row2_1 = st.columns(4)

        with row2_1[0]:

            enviar_informes = st.button(f'Enviar Informes Gerais')

            if enviar_informes and data_pagamento and data_inicial and data_final:

                puxar_aba_simples(st.session_state.id_gsheet, 'Telefones Guias', 'df_telefones')

                lista_htmls = []

                lista_telefones = []

                for guia_ref in lista_guias:

                    st.session_state.cnpj = st.session_state.df_cnpj_fornecedores[st.session_state.df_cnpj_fornecedores['Guia']==guia_ref]['CNPJ/CPF Fornecedor Guia'].iloc[0]

                    st.session_state.razao_social = st.session_state.df_cnpj_fornecedores[st.session_state.df_cnpj_fornecedores['Guia']==guia_ref]['Razao Social/Nome Completo Fornecedor Guia'].iloc[0]

                    telefone_guia = verificar_guia_sem_telefone(st.session_state.id_gsheet, guia_ref, st.session_state.df_telefones['Guias'].unique().tolist())

                    df_pag_guia = st.session_state.df_pag_final[st.session_state.df_pag_final['Guia']==guia_ref].sort_values(by=['Data da Escala', 'Veiculo', 'Motorista']).reset_index(drop=True)

                    df_pag_guia['Data da Escala'] = pd.to_datetime(df_pag_guia['Data da Escala'])

                    df_pag_guia['Data da Escala'] = df_pag_guia['Data da Escala'].dt.strftime('%d/%m/%Y')

                    soma_servicos = df_pag_guia['Valor Total'].sum()

                    soma_servicos = format_currency(soma_servicos, 'BRL', locale='pt_BR')

                    for item in ['Valor Uber', 'Valor Serviço', 'Valor Total']:

                        df_pag_guia[item] = df_pag_guia[item].apply(lambda x: format_currency(x, 'BRL', locale='pt_BR'))

                    html = definir_html(df_pag_guia)

                    nome_html = f'{guia_ref}.html'

                    criar_output_html(nome_html, html, guia_ref, soma_servicos)

                    with open(nome_html, "r", encoding="utf-8") as file:

                        html_content_guia_ref = file.read()

                    lista_htmls.append([html_content_guia_ref, telefone_guia])

                payload = {"informe_html": lista_htmls}
                
                response = requests.post(st.session_state.id_webhook, json=payload)
                    
                if response.status_code == 200:
                    
                    st.success(f"Mapas de Pagamentos enviados com sucesso!")
                    
                else:
                    
                    st.error(f"Erro. Favor contactar o suporte")

                    st.error(f"{response}")

        with row2_1[1]:

            enviar_informes_financeiro = st.button('Enviar Informes p/ Financeiro')

            if enviar_informes_financeiro and data_pagamento and data_inicial and data_final:

                lista_htmls = []

                lista_telefones = []

                for guia_ref in lista_guias:

                    st.session_state.cnpj = st.session_state.df_cnpj_fornecedores[st.session_state.df_cnpj_fornecedores['Guia']==guia_ref]['CNPJ/CPF Fornecedor Guia'].iloc[0]

                    st.session_state.razao_social = st.session_state.df_cnpj_fornecedores[st.session_state.df_cnpj_fornecedores['Guia']==guia_ref]['Razao Social/Nome Completo Fornecedor Guia'].iloc[0]

                    df_pag_guia = st.session_state.df_pag_final[st.session_state.df_pag_final['Guia']==guia_ref].sort_values(by=['Data da Escala', 'Veiculo', 'Motorista']).reset_index(drop=True)

                    df_pag_guia['Data da Escala'] = pd.to_datetime(df_pag_guia['Data da Escala'])

                    df_pag_guia['Data da Escala'] = df_pag_guia['Data da Escala'].dt.strftime('%d/%m/%Y')

                    soma_servicos = df_pag_guia['Valor Total'].sum()

                    soma_servicos = format_currency(soma_servicos, 'BRL', locale='pt_BR')

                    for item in ['Valor Uber', 'Valor Serviço', 'Valor Total']:

                        df_pag_guia[item] = df_pag_guia[item].apply(lambda x: format_currency(x, 'BRL', locale='pt_BR'))

                    html = definir_html(df_pag_guia)

                    nome_html = f'{guia_ref}.html'

                    criar_output_html(nome_html, html, guia_ref, soma_servicos)

                    with open(nome_html, "r", encoding="utf-8") as file:

                        html_content_guia_ref = file.read()

                    lista_htmls.append([html_content_guia_ref, '84994001644'])

                payload = {"informe_html": lista_htmls}
                
                response = requests.post(st.session_state.id_webhook, json=payload)
                    
                if response.status_code == 200:
                    
                    st.success(f"Mapas de Pagamentos enviados com sucesso!")
                    
                else:
                    
                    st.error(f"Erro. Favor contactar o suporte")

                    st.error(f"{response}")

if 'html_content' in st.session_state and guia:

    with row2_1[2]:

        enviar_informes = st.button(f'Enviar Informes | {guia}')

    if enviar_informes and data_pagamento and data_inicial and data_final:

        puxar_aba_simples(st.session_state.id_gsheet, 'Telefones Guias', 'df_telefones')

        telefone_guia = verificar_guia_sem_telefone(st.session_state.id_gsheet, guia, st.session_state.df_telefones['Guias'].unique().tolist())
        
        payload = {"informe_html": st.session_state.html_content, 
                    "telefone": telefone_guia}
        
        response = requests.post(st.session_state.id_webhook, json=payload)
            
        if response.status_code == 200:
            
            st.success(f"Mapas de Pagamento enviados com sucesso!")
            
        else:
            
            st.error(f"Erro. Favor contactar o suporte")

            st.error(f"{response}")
