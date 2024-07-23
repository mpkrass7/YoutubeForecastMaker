# YouTubePredictor Recipe

This recipe allows DataRobot users to create a scheduled pull of data from a live source, in our case,
Youtube, and create a front end to display forecasts of the data. The template has 3 steps.
1. Users will schedule a notebook to pull playlist data (likes, comments, views from each video) and store them in their use case. 
2. Users will schedule preprocessing of this data.
3. Users will create a deployment and an application to display the data and forecasts

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
   !pip install uv
   ```
   ```bash
   !uv pip install kedro
   ```
   ```bash
   !kedro new -n $PROJECT_NAME$ --starter=https://github.com/j-beastman/WeatherForecastic.git --checkout master
   ```
   ```bash
   !uv pip install -r $PROJECT_NAME$/requirements.txt
   ```

4. Go into this folder, then conf/local/credentials.yml
   - Fill in your datarobot and OpenAI credentials

5. Navigate to conf/base/parameters.yml
   - Add in the cities along with the weather features you want to collect

6. Navigate to the notebooks directory. Run the setup.ipynb notebook?

7. Create a copy of some notebook and schedule it to run to keep your data up to date
   using the weather API


### Preprocessing the Data

1. Create a new codespace and navigate into it.
   - This codespace will be dedicated to the preprocessing of your data.

2. Repeat step 4 from the previous section

3. Repeat step 5 from the previous section

4. To schedule preprocessing of your data, navigate to the notebooks directory inside your kedro project and click on the data_prep.ipynb notebook.

5. Schedule this notebook to run, but you may disable it at any time to edit how you'd like to preprocess your data.
   - This notebook should be put back on a schedule after your done editing so that your scoring and modeling data stays up to date. Schedule it to run at least 15 minutes after your data_pull notebook so that the notebook can access the raw data when it's not being updated.

### Deploying the forecast and the application

1. Create another codespace in your use case and navigate into it.
- This codespace will be dedicated to deploying your application and creating a model deployment.
- It only needs to be run if you make updates to your front end or if you'd like to change the hyperparameters of your model creation (in which case it will redeploy a model)

2. Repeat step 4 from the first section. 

3. Repeat step 5 from the first section. This time you'll want to put in your OpenAI credentials.

4. Open up a terminal, type 'cd $your_project name' and kedro run'

5. Sit back and watch DataRobot...
   1. Perform AutoML and find the best model for your data.
   2. Deploy this champion model
   3. Create a custom application to display your data and forecasts.

6. Once the pipeline has finished, a link will pop up to the application (open it!)
   - You can also navigate to the applications directory in DataRobot Classic

7. Perform predictions on any of the videos in your playlist

### Future maintenance

1. This pipeline automatically retrains the model attached to your deployment if it starts to drift, so no need to run the last pipeline unless you'd like to make changes to the project.

2. That's it! This application will stay up to date on the data being automatically pulled.