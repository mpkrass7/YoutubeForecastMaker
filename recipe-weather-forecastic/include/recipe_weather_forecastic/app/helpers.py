# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

from __future__ import annotations
import os
from typing import Any, Dict, Tuple, TYPE_CHECKING

import requests
import datarobot as dr
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from PIL import Image, ImageDraw, ImageFont
from openai import AzureOpenAI
from plotly.subplots import make_subplots


if TYPE_CHECKING:
    from kedro.io import DataCatalog


def get_kedro_catalog(kedro_project_root: str) -> DataCatalog:
    """Initialize a kedro data catalog (as a singleton)."""
    if "KEDRO_CATALOG" not in st.session_state:
        try:
            import pathlib
            from kedro.framework.startup import bootstrap_project
            from kedro.framework.session import KedroSession
        except ImportError as e:
            raise ImportError(
                "Please ensure you've installed `kedro` and `kedro_datasets` to run this app locally"
            ) from e

        project_path = pathlib.Path(kedro_project_root).resolve()
        bootstrap_project(project_path)
        session = KedroSession.create(project_path)
        context = session.load_context()
        catalog = context.catalog

        # initializing a context & catalog is slow enough to be perceived; persist in session state
        st.session_state["KEDRO_CATALOG"] = catalog
    return st.session_state["KEDRO_CATALOG"]


@st.cache_data(show_spinner=False)
def make_datarobot_deployment_predictions(
    endpoint: str, token: str, data: pd.DataFrame, deployment_id: str
):
    """
    Make predictions on data provided using DataRobot deployment_id provided.
    See docs for details:
         https://docs.datarobot.com/en/docs/api/reference/predapi/dr-predapi.html

    Parameters
    ----------
    data : str
        Feature1,Feature2
        numeric_value,string
    deployment_id : str
        Deployment ID to make predictions with.
    forecast_point : str, optional
        Forecast point as timestamp in ISO format
    predictions_start_date : str, optional
        Start of predictions as timestamp in ISO format
    predictions_end_date : str, optional
        End of predictions as timestamp in ISO format

    Returns
    -------
    Response schema:
        https://docs.datarobot.com/en/docs/api/reference/predapi/dr-predapi.html#response-schema

    Raises
    ------
    DataRobotPredictionError if there are issues getting predictions from DataRobot
    """
    client = dr.Client(endpoint=endpoint, token=token)

    deployment = client.get(f"deployments/{deployment_id}/").json()

    datarobot_key = deployment["defaultPredictionServer"]["datarobot-key"]
    prediction_server_endpoint = deployment["defaultPredictionServer"]["url"]
    # Set HTTP headers. The charset should match the contents of the file.
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": f"Bearer {client.token}",
        "DataRobot-Key": datarobot_key,
    }
    api_url = os.path.join(
        prediction_server_endpoint,
        "predApi/v1.0/deployments/{deployment_id}/predictions",
    )

    url = api_url.format(deployment_id=deployment_id)

    params = {"maxExplanations": 3}

    # Make API request for predictions
    predictions_response = requests.post(
        url,
        data=data.to_json(orient="records"),
        headers=headers,
        params=params,  # "Prediction Explanations aren't available because the validation partition doesn't contain the required number of rows."
    )
    # If we run into an issue, explanations may not be available.
    if predictions_response.status_code == 400:
        print(predictions_response.text)
        predictions_response = requests.post(
            url, data=data.to_json(orient="records"), headers=headers, params=None
        )
    # Return a Python dict following the schema in the documentation
    return predictions_response.json()


def process_predictions(
    predictions: Dict[str, Any],
    prediction_interval: str = "80",
    bound_at_zero: bool = False,
) -> pd.DataFrame:
    data = predictions["data"]
    if data[0].get("predictionExplanations") is None:
        slim_predictions = pd.DataFrame(data)[["seriesId", "timestamp", "prediction"]]
        intervals = pd.DataFrame(
            [i["predictionIntervals"][prediction_interval] for i in data]
        )
        clean_predictions = pd.concat([slim_predictions, intervals], axis=1)

        if bound_at_zero:
            bounds = ["prediction", "low", "high"]
            clean_predictions[bounds] = clean_predictions[bounds].clip(lower=0)
    else:
        slim_predictions = pd.DataFrame(data)[
            ["seriesId", "timestamp", "prediction", "predictionExplanations"]
        ]
        intervals = pd.DataFrame(
            [i["predictionIntervals"][prediction_interval] for i in data]
        )
        clean_predictions = pd.concat([slim_predictions, intervals], axis=1).drop(
            columns="predictionExplanations"
        )

        if bound_at_zero:
            bounds = ["prediction", "low", "high"]
            clean_predictions[bounds] = clean_predictions[bounds].clip(lower=0)

    return clean_predictions


def get_prompt(
    prediction_explanations_df: pd.DataFrame,
    target: str,
    ex_target: bool = False,
    use_ranks: bool = True,
) -> str:
    """Build prompt to summarize pred explanations data."""
    top_feature_threshold = 75
    total_strength = (
        prediction_explanations_df.groupby("feature")["strength"]
        .apply(lambda c: c.abs().sum())
        .sort_values(ascending=False)
    )
    total_strength = ((total_strength / total_strength.sum()) * 100).astype(int)
    total_strength.name = "Relative importance (%)"
    total_strength.index.name = None
    cum_total_strength = total_strength.cumsum()
    if use_ranks:
        total_strength = pd.Series(
            range(1, 1 + len(total_strength)), index=total_strength.index
        )
        total_strength.name = "Rank"
    top_features = pd.DataFrame(
        total_strength[cum_total_strength.shift(1).fillna(0) < top_feature_threshold][
            :4
        ]
    ).to_string()
    if not ex_target:
        prompt = (
            "The following are the most important features in the "
            + "forecasting model's predictions. Provide a 3-4 sentence "
            + "summary of the key cyclical and/or trend drivers for the "
            + "forecast, explain any potential intuitive,qualitative "
            + "interpretations or explanations."
        )
    else:
        prompt = (
            "The following are the most important exogenous features "
            + f"in the forecasting model's predictions of `{target}`. "
            + "Provide a 3-4 sentence summary of the exogenous "
            + "driver(s) for the forecast, explain any potential "
            + "intuitive, qualitative interpretation(s) "
            + "or explanation(s)."
        )
    return prompt + f"\n\n\n{top_features}"


def get_completion(
    client: AzureOpenAI, llm_model_name: str, prompt: str, temperature: float = 0
) -> str:
    """Generate LLM completion"""
    resp = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=llm_model_name,
        temperature=temperature,
    )
    return resp.choices[0].message.content


def get_tldr(
    preds_json: str,
    target: str,
    client: AzureOpenAI,
    llm_model_name: str,
    temperature: float = 0,
) -> Tuple[str, pd.DataFrame]:
    """Get a natural langauge tldr of what the pred expls say about a TS forecast."""
    df = pd.DataFrame(preds_json["data"])

    if "predictionExplanations" not in df.columns:
        raise KeyError

    target_df = pd.DataFrame(
        [
            explanation
            for explanations in df["predictionExplanations"].tolist()
            for explanation in explanations
            if explanation["feature"].startswith(target + " (")
        ]
    )
    target_prompt = get_prompt(target_df, target, ex_target=False)
    target_completion = get_completion(
        client, llm_model_name, target_prompt, temperature=temperature
    )

    ex_target_df = pd.DataFrame(
        [
            explanation
            for explanations in df["predictionExplanations"].tolist()
            for explanation in explanations
            if not explanation["feature"].startswith(target + " (")
        ]
    )
    ex_target_prompt = get_prompt(ex_target_df, target, ex_target=True)
    ex_target_completion = get_completion(
        client, llm_model_name, ex_target_prompt, temperature=temperature
    )
    explain_df = pd.concat((target_df, ex_target_df)).reset_index(drop=True)
    return target_completion + "\n\n\n" + ex_target_completion, explain_df


def create_weather_image(temperature, hour):
    # Load base image (you'll need to create or obtain these)
    base_image_path = f"weather_icons/{hour}.jpg"
    try:
        img = Image.open(base_image_path)
    except FileNotFoundError:
        img = Image.open("weather_icons/1.jpg") #TODO: remove this once have image for each hour
    
    # Resize the image to be smaller
    img = img.resize((1000, 2000))  # Adjust size as needed
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("Helvetica.ttf", 200)  # Increased font size
    temp_text = f"{temperature}°F"
    
    # Get text size
    left, top, right, bottom = font.getbbox(temp_text)
    text_width = right - left
    text_height = bottom - top
    
    # Calculate position (this will center the text)
    position = ((1000 - text_width) // 2, (text_height) // 2)
    draw.text(position, temp_text, font=font, fill=(255, 255, 255))  # White text
    return img

@st.cache_data(show_spinner=False)
def score_forecast(
    df, deployment_id, endpoint, api_key, prediction_interval: str = "80", bound_at_zero: bool = False
):
    predictions = make_datarobot_deployment_predictions(
        endpoint, api_key, df, deployment_id
    )
    processed_predictions = process_predictions(
        predictions, prediction_interval=prediction_interval, bound_at_zero=bound_at_zero
    )
    return predictions, processed_predictions

@st.cache_data(show_spinner=False)
def create_chart(
    history, 
    forecast, 
    title, 
    target,
    y_axis_name,
    datetime_partition_column,
    date_format="%m/%d/%y", 
):
    # Create the Chart
    fig = make_subplots(specs=[[{"secondary_y": False}]])
    fig.add_trace(
        go.Scatter(
            x=pd.to_datetime(history[datetime_partition_column], format=date_format),
            y=history[target],
            mode="lines",
            name=f"{target} History",
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
            name=f"Total {target} Forecast",
            line_shape="spline",
            line=dict(color="#162955", width=2),
        )
    )

    fig.add_vline(
        x=history[datetime_partition_column].max(),
        line_width=2,
        line_dash="dash",
        line_color="gray",
    )

    fig.update_xaxes(
        color="#404040",
        title_font_family="Gravitas One",
        title_text=datetime_partition_column,
        linecolor="#adadad",
    )

    fig.update_yaxes(
        color="#404040",
        title_font_size=16,
        title_text=y_axis_name,
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