import logging
import yaml


from rasa.nlu.components import Component


logger = logging.getLogger(__name__)


class Keywords(Component):
    """
    Search and replace some words as defined in the "normalization.yml" file.

    The yaml file structure is one keyword per line, '_' to mark space.
    ex:
    _metro_: _métro_
    """

    name = "normalization"

    provides = []

    requires = []

    defaults = {}

    language_list = None

    def __init__(self, component_config=None):
        super(Keywords, self).__init__(component_config)

        self.keywords_list = []
        # Read keywords to look for. Note that '_' are replaced by empty space.
        with open('normalization.yml') as file:
            yaml_dict = yaml.load(file, Loader=yaml.BaseLoader)
            self.keywords_list = [{'keyword': key.replace('_', ' '), 'replace_by': yaml_dict[key].replace('_', ' ')} for key in yaml_dict]

        logger.info(f"*** keywords normalization: {len(self.keywords_list)} ***")

    def train(self, training_data, cfg, **kwargs):
        pass

    def process(self, message, **kwargs):
        """ Search for some important keywords and normalize them. """
        original_text = message.text

        # look and replace keywords
        for item in self.keywords_list:
            message.text = message.text.replace(item['keyword'], item['replace_by'])

        if message.text != original_text:
            logger.info(f"*** text message keywords normalized: <{message.text}> ***")

    def persist(self, file_name, model_dir):
        """ Persist this component to disk for future loading. """
        pass
