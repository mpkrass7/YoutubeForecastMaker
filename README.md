# YouTubePredictor (working title) Recipe

TODO: You should include a **summary** of your recipe as well as some **examples** of pipeline changes.

# Your Recipe Name Here

TODO: Describe your recipe here. We recommend including a gif or screenshot of the final output if applicable.

1. Create a Use Case

There is no need to modify the directions in the next section.

## Getting started
1. Ensure you have the following DataRobot feature flags turned on:
   - **INSERT REQUIRED FLAGS HERE**

2. Create a [new][virtualenv-docs] python virtual environment with python >= 3.9.

3. Install `kedro`, create a new kedro project from this template and `cd` to the newly created directory.
   Choose a project name that is likely to be unique - DataRobot requires registered model names to be unique
   for an organization. You can change it later if necessary by editing `parameters.yml`.
   ```bash
   pip install kedro
   ```
   ```bash
   kedro new --starter=https://github.com/datarobot/recipe-template.git --checkout main
   ```
   ```bash
   cd your_project_name
   ```
      
4. Install requirements for this template: `pip install -r requirements.txt`

5. Populate the following credentials in `conf/local/credentials.yml`:
   ```yaml
   datarobot:
     endpoint: <your endpoint>  # e.g. https://your_subdomain.datarobot.com/api/v2
     api_token: <your api token>
   ```

6. Run the pipeline: `kedro run`. Start exploring the pipeline using the kedro GUI: `kedro viz --include-hooks`

![Kedro Viz](https://s3.amazonaws.com/datarobot_public/drx/drx_gifs/kedro-viz.gif)

[virtualenv-docs]: https://docs.python.org/3/library/venv.html#creating-virtual-environments

## Making changes to the pipeline
The following files govern pipeline execution. In general, you will not need to modify
any other boilerplate files as you customize the pipeline.:

- `conf/base/parameters.yml`: pipeline configuration options and hyperparameters
- `conf/local/credentials.yml`: API tokens and other secrets
- `conf/base/catalog.yml`: file storage locations that can be used as node inputs or outputs,
  including locations of supporting assets to build DR custom models, execution environments
- `src/your_project_name/pipelines/*/nodes.py`: function definitions for the pipeline nodes
- `src/your_project_name/pipelines/*/pipeline.py`: node names, inputs and outputs
- `src/datarobotx/idp`: directory contains function definitions for for reusable idempotent DR nodes
- `include/your_project_name`: directory contains raw assets and templates used by the pipeline

For a deeper orientation to kedro principles and project structure visit the [Kedro][kedro-docs]
documentation.

[kedro-docs]: https://docs.kedro.org/en/stable/

### Example changes
We recommend including some examples of changes users can make to this recipe in order to modify or extend its functionality. These changes could be in the parameters.yaml, the catalog.yaml file or in the pipeline itself.
