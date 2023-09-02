import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Create a connection object.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
    ],
)
service = build('sheets', 'v4', credentials=credentials)
sheet = service.spreadsheets()
result_input = sheet.values().get(spreadsheetId=st.secrets['SAMPLE_SPREADSHEET_ID_input'],
                            range=st.secrets['SAMPLE_RANGE_NAME']).execute()
values_input = result_input.get('values', [])


df=pd.DataFrame(values_input[1:], columns=values_input[0])
st.dataframe(df)