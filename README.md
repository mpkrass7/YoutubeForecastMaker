# Weather Forecastic

This template allows users to connect their data to DataRobot's functionality seamlessly with automated data updates and real-time forecasting. We deploy a model trained on your data, then create a streamlit application for clear visualizations of the deployment's capabilities. We can ensure accurate model performance through scheduled batch predictions and automatic retraining if our model's accuracy drops below a set threshold.

## Getting started -- Pulling Data
1. Create a Use Case on [DataRobot](app.datarobot.com)
   - Click on "DataRobot NextGen"
   - Select Workbench
   - In the top right, click "Create New Use Case"

2. Create a new Code Space and navigate into it
   - Click the blue "Add" button

3. Open up a terminal (in the bottom-left corner you'll see a ">_" icon) and type the following commands.
   - The project name does not matter.
   ```bash
   pip install uv
   ```
   ```bash
   uv pip install kedro
   ```
   ```bash
   kedro new -n $PROJECT_NAME$ --starter=https://github.com/j-beastman/WeatherForecastic.git --checkout master
   ```
   ```bash
   uv pip install -r $PROJECT_NAME$/requirements.txt
   ```

4. Go into this folder, then conf/local/credentials.yml
   - Fill in your datarobot and OpenAI credentials

5. Navigate to conf/base/parameters.yml
   - Add in the cities along with the weather features you want to collect

6. Now, in the terminal type 
   ```bash
   kedro run -p "setup"
   ```
   This subpipeline...
   - Collects historical weather data from the cities you inputted so that we have modeling data ready from the get-go.
   - Sets up a scheduled notebook to pull weather data from your cities every 2 hours to ensure your data is up-to-date.
      - This incoming data also allows us to pair actuals with predictions made via our batch prediction job which will be setup in the next step.

7. Once the setup pipeline has run, open up the terminal again to type
   ```bash
   kedro run
   ```

8. Sit back and watch your Datarobot deploy your model, your deployment, and your custom application. 

## For contributors

1. Install datarobotx-idp locally
   ```bash
   git clone https://github.com/datarobot-community/datarobotx-idp
   cd datarobotx-idp
   pip install -e .
   ```

2. Install kedro, install requirements from requirements.txt

3. Fill in your credentials.yml, ensure globals.yml is filled in.

4. Run
   ```bash
   kedro run -p "setup"
   ```

5. Once this is complete, run 
   ```bash
   kedro run
   ```
