# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

import sys

import datarobot as dr
import pandas as pd
import streamlit as st

from openai import AzureOpenAI
import yaml

import helpers


if "params" not in st.session_state:
    try:
        # in production, parameters are available in the working directory
        with open("app_parameters.yaml", "r") as f:
            st.session_state["params"] = yaml.safe_load(f)
        st.session_state["datarobot_credentials"] = st.secrets["datarobot_credentials"]
        st.session_state["azure_client"] = AzureOpenAI(
            **st.secrets["azure_credentials"]
        )

    except (FileNotFoundError, KeyError):
        # during local dev, parameters can be retrieved from the kedro catalog
        project_root = "../../../"
        catalog = helpers.get_kedro_catalog(project_root)
        st.session_state["params"] = catalog.load("deploy_streamlit_app.app_parameters")
        st.session_state["datarobot_credentials"] = catalog.load(
            "params:credentials.datarobot"
        )
        azure_credentials = catalog.load(
            "params:credentials.azure_openai_llm_credentials"
        )
        st.session_state["azure_client"] = AzureOpenAI(
            azure_endpoint=azure_credentials.get("azure_endpoint"),
            api_key=azure_credentials.get("api_key"),
            api_version=azure_credentials.get("api_version"),
        )

params = st.session_state["params"]

API_KEY = st.session_state["datarobot_credentials"]["api_token"]
ENDPOINT = st.session_state["datarobot_credentials"]["endpoint"]

CLIENT = st.session_state["azure_client"]

PAGE_TITLE = params["page_title"]
DEPLOYMENT_ID = params["deployment_id"]
DATETIME_PARTITION_COLUMN = params["datetime_partition_column"]
TARGET = params["target"]
MULTISERIES_ID_COLUMN = params["multiseries_id_column"][0]
PREDICTION_INTERVAL = str(params["prediction_interval"])
Y_AXIS_NAME = params["graph_y_axis"]
LOWER_BOUND_AT_0 = params["lower_bound_forecast_at_0"]
LLM_MODEL_NAME = params["model_name"]
HEADLINE_PROMPT = params["headline_prompt"]
HEADLINE_TEMPERATURE = params["headline_temperature"]
ANALYSIS_TEMPERATURE = params["analysis_temperature"]

if st.session_state.get("scoring_data") is None:
    st.session_state["scoring_data"] = dr.Dataset.get(
        params["scoring_data"]
    ).get_as_dataframe()

LOGO = "./DataRobot.png"

sys.setrecursionlimit(10000)

# Set the maximum number of rows and columns to be displayed
pd.set_option("display.max_rows", None)  # Display all rows
pd.set_option("display.max_columns", None)  # Display all columns

# Configure the page title, favicon, layout, etc
st.set_page_config(page_title=PAGE_TITLE, page_icon="./datarobot_favicon.png", layout="wide")

with open("./style.css") as f:
    css = f.read()

st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def get_dateformat(endpoint: str, token: str, deployment_id: str) -> str:
    """
    Get the date format of the deployment
    """
    client = dr.Client(endpoint=endpoint, token=token)
    deployment_settings = client.get(f"deployments/{deployment_id}/settings/").json()
    return deployment_settings["predictionsByForecastDate"]["datetimeFormat"]


def interpretChartHeadline(forecast):
    completion = CLIENT.chat.completions.create(
        model=LLM_MODEL_NAME,
        temperature=HEADLINE_TEMPERATURE,
        messages=[
            {"role": "system", "content": HEADLINE_PROMPT},
            {
                "role": "user",
                "content": "Forecast:" + str(forecast[["timestamp", "prediction"]]),
            },
        ],
    )
    return completion.choices[0].message.content

def run_app():
    titleContainer = st.container()
    with titleContainer:
        (
            col1,
            _,
        ) = titleContainer.columns([1, 2])
        col1.image(LOGO, width=200)
        st.markdown(
            f"<h1 style='text-align: center;'>{PAGE_TITLE}</h1>", unsafe_allow_html=True
        )

    df = st.session_state["scoring_data"]
    date_format = get_dateformat(ENDPOINT, API_KEY, DEPLOYMENT_ID)
    # Setup dropdown menues in the sidebar
    with st.sidebar:
        series_selection = df[MULTISERIES_ID_COLUMN].unique().tolist()

        visual = st.radio(
            "Select visual configuration",
            ["Meterologist", "Graph"]
        )

        with st.form(key="sidebar_form"):
            series = st.selectbox(MULTISERIES_ID_COLUMN, options=series_selection)
            if visual == "Graph":
                n_records_to_display = st.number_input(
                    "Number of records to display",
                    min_value=10,
                    max_value=200,
                    value=90,
                    step=10,
                )
            sidebarSubmit = st.form_submit_button(label="Run Forecast")

    if sidebarSubmit:
        st.session_state["series"] = series
    if st.session_state.get("series") is not None:
        # Execute the forecast
        with st.spinner("Processing forecast..."):
            scoring_data = (
                df.loc[df[MULTISERIES_ID_COLUMN] == series]
                .reset_index(drop=True)
                .copy()
            )
            forecast_raw, forecast = helpers.score_forecast(
                scoring_data,
                DEPLOYMENT_ID,
                ENDPOINT,
                API_KEY,
                prediction_interval=PREDICTION_INTERVAL,
                bound_at_zero=LOWER_BOUND_AT_0,
            )
        if visual == "Graph":
            fpa(n_records_to_display, scoring_data, forecast, date_format, forecast_raw, series)
        elif visual == "Meterologist":
            visual_forecast(forecast, forecast_raw)


def visual_forecast(forecast, forecast_raw):    
    # Ordering matters
    headlineContainer = st.container()
    forecastContainer = st.container()
    descriptionContainer = st.container()
    
    with headlineContainer:
        st.subheader(interpretChartHeadline(forecast), divider=True)

    first_hour = pd.to_datetime(forecast["timestamp"].iloc[0]).hour

    with forecastContainer: 
        cols = st.columns(12)
        forecast = forecast.sort_values(by='timestamp', ascending=True)
        for i, col in enumerate(cols):
            forecast_this_hour = forecast.iloc[i]
            temperature = f"{forecast_this_hour['prediction']:.1f}"
            # Create and display the image with overlaid temperature
            weather_image = helpers.create_weather_image(temperature, ((first_hour + i) % 24))
            with col:
                # st.metric("Hour of day", first_hour + i)
                st.image(weather_image, caption=f"Weather at {((first_hour + i) % 24) :02d}00", use_column_width=True)

    with descriptionContainer:
        with st.spinner("Generating description..."):
            try:
                st.write("**AI Generated Meteorologist Insights")
                explanations, explain_df = helpers.get_tldr(
                    forecast_raw,
                    TARGET,
                    CLIENT,
                    LLM_MODEL_NAME,
                    temperature=ANALYSIS_TEMPERATURE,
                )
            except KeyError:
                explanations = "No explanation generated. This may be an issue with the amount of training data provided."
                explain_df = None
            st.write(explanations)
        with st.expander("Raw Explanations", expanded=False):
            st.write(explain_df)
    

def fpa(n_records_to_display, scoring_data, forecast, date_format, forecast_raw, series):
    # Layout
    headlineContainer = st.container()
    chartContainer = st.container()
    explanationContainer = st.container()
    
    with chartContainer:
        helpers.create_chart(
            scoring_data.tail(n_records_to_display),
            forecast,
            "Forecast for " + str(series),
            target=TARGET,
            datetime_partition_column=DATETIME_PARTITION_COLUMN,
            date_format=date_format,
        )

    with headlineContainer:
        with st.spinner("Generating Headline..."):
            st.subheader(interpretChartHeadline(forecast))

    with explanationContainer:
        with st.spinner("Generating explanation..."):
            st.write("**AI Generated Analysis:**")
            try:
                explanations, explain_df = helpers.get_tldr(
                    forecast_raw,
                    TARGET,
                    CLIENT,
                    LLM_MODEL_NAME,
                    temperature=ANALYSIS_TEMPERATURE,
                )
            except KeyError:
                explanations = "No explanation generated. This may be an issue with the amount of training data provided."
                explain_df = None
            st.write(explanations)
        with st.expander("Raw Explanations", expanded=False):
            st.write(explain_df)

# Main app
def _main():
    hide_streamlit_style = """
    <style>
    # MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """
    st.markdown(
        hide_streamlit_style, unsafe_allow_html=True
    )  # This let's you hide the Streamlit branding

    run_app()

if __name__ == "__main__":
    _main()
