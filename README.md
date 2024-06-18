# YouTubePredictor (working title) Recipe

TODO: You should include a **summary** of your recipe as well as some **examples** of pipeline changes.

# Your Recipe Name Here

TODO: Describe your recipe here. We recommend including a gif or screenshot of the final output if applicable.

1. Create a Use Case

There is no need to modify the directions in the next section.

## Getting started
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

3. Create a new Code Space titled "Pull Data"
   - Click the blue "Add" button

4. Create a notebook in the storage directory of your new Codespace with the following cells
   ```bash
   !pip install uv
   ```
   ```bash
   !uv pip install kedro
   ```
   ```bash
   !kedro new -n $YOUR_PROJECT_NAME$ --starter=https://github.com/mpkrass7/YoutubeForecastMaker.git --checkout master
   ```
   ```bash
   !uv pip install -r $YOUR_PROJECT_NAME$/requirements.txt
   ```

5. Run the notebook! A new folder should appear with the project name you gave after the "-n" flag

6. Go into this folder, then conf/local/credentials.yml
   - Fill in your datarobot credentials, your use case id (which is in your search bar after https://app.datarobot.com/usecases/), 
      and your youtube-api-key
   - For this first folder, you don't have to put in your OpenAI credentials

7. Navigate to conf/base/parameters.yml
   - Add in the youtube playlist IDs that you would like to pull data from.
   - There are 3 '-' there, you can add more, or take out 2, if you use 1 playlist ID, make sure it has a '-' before it.

8. Lastly, to schedule the data to pull, you'll want to navigate to the notebooks directory in your project.
   - Click on the data_pull
   - Schedule the notebook to run every hour.

9. Once you've scheduled the notebook to run, give it some time to collect data. A few days at least, but the more data,
   the better the forecast will be.

10. Create a new 

### Example changes
We recommend including some examples of changes users can make to this recipe in order to modify or extend its functionality. These changes could be in the parameters.yaml, the catalog.yaml file or in the pipeline itself.
