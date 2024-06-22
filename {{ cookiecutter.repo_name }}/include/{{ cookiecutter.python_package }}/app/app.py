# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

import base64
import sys

import datarobot as dr
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from openai import AzureOpenAI
from plotly.subplots import make_subplots
from streamlit import delta_generator
import yaml

import helpers


if "params" not in st.session_state:
    try:
        # in production, parameters are available in the working directory
        with open("app_parameters.yaml", "r") as f:
            st.session_state["params"] = yaml.safe_load(f)
        st.session_state['datarobot_credentials'] = st.secrets["datarobot_credentials"]
        st.session_state['azure_client'] = AzureOpenAI(**st.secrets["azure_credentials"])
        
    except (FileNotFoundError, KeyError):
        # during local dev, parameters can be retrieved from the kedro catalog
        project_root = "../../../"
        catalog = helpers.get_kedro_catalog(project_root)
        st.session_state["params"] = catalog.load("deploy_streamlit_app.app_parameters")
        st.session_state["datarobot_credentials"] = catalog.load("params:credentials.datarobot")
        azure_credentials = catalog.load("params:credentials.azure_openai_llm_credentials")
        st.session_state["azure_client"] = AzureOpenAI(
            azure_endpoint=azure_credentials.get("azure_endpoint"),
            api_key=azure_credentials.get("api_key"),
            api_version=azure_credentials.get("api_version")
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

if st.session_state.get('scoring_data') is None:
    st.session_state['scoring_data'] = dr.Dataset.get(params["scoring_data"]).get_as_dataframe()

LOGO = "./DataRobot.png"

sys.setrecursionlimit(10000)

# Set the maximum number of rows and columns to be displayed
pd.set_option("display.max_rows", None)  # Display all rows
pd.set_option("display.max_columns", None)  # Display all columns

# Configure the page title, favicon, layout, etc
st.set_page_config(page_title=PAGE_TITLE, layout="wide")

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


@st.cache_data(show_spinner=False)
def scoreForecast(df, deployment_id, prediction_interval: str = "80", bound_at_zero: bool = False):
    predictions = helpers.make_datarobot_deployment_predictions(
        ENDPOINT, API_KEY, df, deployment_id
    )
    processed_predictions = helpers.process_predictions(
        predictions, prediction_interval=prediction_interval
    )
    return predictions, processed_predictions


@st.cache_data(show_spinner=False)
def createChart(history, forecast, title, date_format="%m/%d/%y"):
    # Create the Chart
    fig = make_subplots(specs=[[{"secondary_y": False}]])
    fig.add_trace(
        go.Scatter(
            x=pd.to_datetime(history[DATETIME_PARTITION_COLUMN], format=date_format),
            y=history[TARGET],
            mode="lines",
            name=f"{TARGET} History",
            line_shape="spline",
            line=dict(color="#ff9e00", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=forecast["timestamp"],
            y=forecast["low"],
            mode="lines",
            name="Low forecast",
            line_shape="spline",
            line=dict(color="#335599", width=0.5, dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=forecast["timestamp"],
            y=forecast["high"],
            mode="lines",
            name="High forecast",
            line_shape="spline",
            line=dict(color="#335599", width=0.5, dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=forecast["timestamp"],
            y=forecast["prediction"],
            mode="lines",
            name=f"Total {TARGET} Forecast",
            line_shape="spline",
            line=dict(color="#162955", width=2),
        )
    )

    fig.add_vline(
        x=history[DATETIME_PARTITION_COLUMN].max(),
        line_width=2,
        line_dash="dash",
        line_color="gray",
    )

    fig.update_xaxes(
        color="#404040",
        title_font_family="Gravitas One",
        title_text=DATETIME_PARTITION_COLUMN,
        linecolor="#adadad",
    )

    fig.update_yaxes(
        color="#404040",
        title_font_size=16,
        title_text=Y_AXIS_NAME,
        linecolor="#adadad",
        gridcolor="#f2f2f2",
    )

    fig.update_layout(
        height=600,
        title=title,
        title_font_size=20,
        hovermode="x unified",
        plot_bgcolor="#ffffff",
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.5),
        margin=dict(l=50, r=50, b=20, t=50, pad=4),
        xaxis=dict(rangeslider=dict(visible=True), type="date"),
        uniformtext_mode="hide",
    )

    fig.update_layout(xaxis=dict(fixedrange=False), yaxis=dict(fixedrange=False))
    fig.update_traces(connectgaps=False)
    config = {"displayModeBar": False, "responsive": True}

    st.plotly_chart(fig, config=config, use_container_width=True)


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


def fpa():
    # Layout
    titleContainer = st.container()
    headlineContainer = st.container()
    chartContainer = st.container()
    videoContainer = st.container()
    explanationContainer = st.container()
    # Header
    with titleContainer:
        col1, _, = titleContainer.columns([1, 2])
        col1.image(LOGO, width=200)
        st.markdown(f"<h1 style='text-align: center;'>{PAGE_TITLE}</h1>", unsafe_allow_html=True)


    df = st.session_state["scoring_data"]
    date_format = get_dateformat(ENDPOINT, API_KEY, DEPLOYMENT_ID)
    # Setup dropdown menues in the sidebar
    with st.sidebar:
        series_selection = df[MULTISERIES_ID_COLUMN].unique().tolist()

        with st.form(key="sidebar_form"):
            series = st.selectbox(MULTISERIES_ID_COLUMN, options=series_selection)
            n_records_to_display = st.number_input(
                "Number of records to display",
                min_value=10,
                max_value=200,
                value=90,
                step=10,
            )
            sidebarSubmit = st.form_submit_button(label="Run Forecast")
            if sidebarSubmit:
                if series is not None:
                    # Execute the forecast
                    with st.spinner("Processing forecast..."):
                        scoring_data = (
                            df.loc[df[MULTISERIES_ID_COLUMN] == series]
                            .reset_index(drop=True)
                            .copy()
                        )
                        forecast_raw, forecast = scoreForecast(
                            scoring_data,
                            DEPLOYMENT_ID,
                            prediction_interval=PREDICTION_INTERVAL,
                            bound_at_zero=LOWER_BOUND_AT_0,
                        )

                    with chartContainer:
                        createChart(
                            scoring_data.tail(n_records_to_display),
                            forecast,
                            "Forecast for " + str(series),
                            date_format=date_format,
                        )

                    with headlineContainer:
                        with st.spinner("Generating Headline..."):
                            st.subheader(interpretChartHeadline(forecast))

                    with videoContainer:
                        with st.spinner("Retrieving Youtube Media..."):
                            video_id = df.loc[df[MULTISERIES_ID_COLUMN] == series]["video_id"].reset_index(drop=True)[0]
                            url = f"https://www.youtube.com/watch?v={video_id}&list=PLSdoVPM5WnndSQEXRz704yQkKwx76GvPV&index=11"
                            st.video(data=url, autoplay=True)

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

    fpa()


if __name__ == "__main__":
    _main()
