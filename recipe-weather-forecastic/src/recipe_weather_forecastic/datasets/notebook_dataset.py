from kedro.io import AbstractDataset
import nbformat

class JupyterNotebookDataSet(AbstractDataset):
    def __init__(self, filepath: str):
        self._filepath = filepath

    def _load(self):
        with open(self._filepath, 'r') as f:
            notebook = nbformat.read(f, as_version=4)
        return notebook

    def _save(self, data) -> None:
        with open(self._filepath, 'w') as f:
            nbformat.write(data, f)

    def _describe(self):
        return dict(filepath=self._filepath)