# YouTubePredictor Recipe

This recipe allows DataRobot users to create a scheduled pull of data from a live source, in our case,
Youtube, and create a front end to display forecasts of the data. The template has 3 steps.
1. Users will schedule a notebook to pull playlist data (likes, comments, views from each video) and store them in their use case. 
2. Users will schedule preprocessing of this data.
3. Users will create a deployment and an application to display the data and forecasts

## Getting started -- Pulling Data
1. Create a Youtube API key
   1. Log into the [Google Developers Console](https://console.cloud.google.com/apis/dashboard)
   2. Click "Create new project"
         - Add a project name, select your organization (optional)
   3. On the new project dashboard, click "Explore & Enable APIs"
   4. In the library, navigate YouTube Data API v3 under YouTube APIs.
   5. Enable the API
   6. Create a credential
      - In the window, select YouTube Data API v3 for the first blank space, Web server (e.g. node js. Tomcat) for the second, and check the Public data box on the third prompt.
      - Click on the blue button titled "What credentials do I need?" After that, your API key will automatically load.
      - Click "Done."
   7. A screen will appear with the API key. Save this to your clipboard.

2. Create a Use Case on [DataRobot](app.datarobot.com)
   - Click on "DataRobot NextGen"
   - Select Workbench
   - In the top right, click "Create New Use Case"

3. Create a new Code Space titled "Pull Data" and navigate into this Codespace
   - Click the blue "Add" button

4. Open up a terminal (in the bottom-left corner you'll see a ">_" icon) and type the following commands.
   - The project name does not matter.
   ```bash
   !pip install uv
   ```
   ```bash
   !uv pip install kedro
   ```
   ```bash
   !kedro new -n $PROJECT_NAME$ --starter=https://github.com/mpkrass7/YoutubeForecastMaker.git --checkout master
   ```
   ```bash
   !uv pip install -r $PROJECT_NAME$/requirements.txt
   ```

5. Go into this folder, then conf/local/credentials.yml
   - Fill in your datarobot credentials and your Youtube API key
   - For this first pipeline, you don't have to put in your OpenAI credentials

6. Navigate to conf/base/parameters.yml
   - Add in the youtube playlist IDs that you would like to pull data from.
   - There are 3 '-' there, you can add more, or take out 2, if you use 1 playlist ID, make sure it has a '-' before it.

7. To schedule pulling your data, you'll want to navigate to the notebooks directory in your project.
   - Click on data_pull.ipynb
   - Schedule the notebook to run every hour.
      - There is an icon on the left side of the screen that looks like a calendar

8. Once you've scheduled the notebook to run, give it some time to collect data. A few days at least, but the more data, the better the forecast will be.

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