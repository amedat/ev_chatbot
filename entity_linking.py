import hashlib
import logging
import pickle
import os
import subprocess
import unidecode

import fofe_entity_linking.predict as predict

from rasa.nlu.components import Component


logger = logging.getLogger(__name__)


class CityMetro(Component):
    """
    Look for 'city' and 'metro' entities and link them to graph entities.
    """

    name = "entity_linking"

    provides = ["entities"]

    requires = []

    defaults = {}

    language_list = None

    def __init__(self, component_config=None):
        super(CityMetro, self).__init__(component_config)

        self.cities_data_filename = "./fofe_entity_linking/cities.csv"
        self.metro_data_filename = "./fofe_entity_linking/metro.csv"

        # create exact match map from data
        self.exact_map_cities = self.create_exact_map(self.cities_data_filename)
        self.exact_map_metro = self.create_exact_map(self.metro_data_filename)

        # load cities model
        self.cities_model, self.cities_embedding = predict.load_models(
                                                "./fofe_entity_linking/models/cities.pth",
                                                "./fofe_entity_linking/data/cities_embedding.pth",
                                                "./fofe_entity_linking/data/cities_vocab.pickle")
        with open("./fofe_entity_linking/data/cities_training_labels.pickle", "rb") as cities_label_file:
            self.cities_labels, _, _ = pickle.load(cities_label_file)
        logger.info(f"*** {len(self.cities_labels)} cities ***")

        # load metro model
        self.metro_model, self.metro_embedding = predict.load_models(
                                                "./fofe_entity_linking/models/metro.pth",
                                                "./fofe_entity_linking/data/metro_embedding.pth",
                                                "./fofe_entity_linking/data/metro_vocab.pickle")
        with open("./fofe_entity_linking/data/metro_training_labels.pickle", "rb") as metro_label_file:
            self.metro_labels, _, _ = pickle.load(metro_label_file)
        logger.info(f"*** {len(self.metro_labels)} metro stations ***")

    @staticmethod
    def train_model(model_name, script_path, data_filename):
        if CityMetro.data_changed(data_filename):
            CityMetro.run_training_subprocess(model_name, script_path, data_filename)
        else:
            logger.info(f"*** <{data_filename}> did not change. No need to retrain. ***")

    @staticmethod
    def run_training_subprocess(model_name, script_path, data_filename):
        logger.info(f"*** training {model_name} ***")
        completed_process = subprocess.run([script_path])

        if completed_process.returncode == 0:
            CityMetro.save_md5_file(data_filename)
        else:
            logger.error(f"*** training {model_name} - error returncode={completed_process.returncode} ***")

    def train(self, training_data, cfg, **kwargs):
        self.train_model("cities", "./train_cities.sh", self.cities_data_filename)
        self.train_model("metro", "./train_metro.sh", self.metro_data_filename)

    @staticmethod
    def expand_saint_abreviation(s):
        # todo - use a regular expression to avoid this mistake while replacing:
        #        Saint-Just-de-Bretenières  --> Saint-Jusaint-de-Bretenières
        #        Saint-Juste-du-Lac         --> Saint-Jusainte-du-Lac
        s = s.lower()
        s = s.replace('ste-', 'sainte-', 1)
        s = s.replace('ste ', 'sainte ', 1)
        s = s.replace('st-', 'saint-', 1)
        s = s.replace('st ', 'saint ', 1)
        return s

    @staticmethod
    def link_entity(text, model, embedding, labels, max_length=50):
        prediction = predict.predict(model, embedding, text, max_length)

        max = prediction.argmax(1)[0]
        predicted_label = labels[max]

        return predicted_label

    @staticmethod
    def link(entities, model, embedding, labels, exact_map):
        for i, entity in enumerate(entities):
            text = CityMetro.expand_saint_abreviation(entity.get('value'))

            # check for a direct match in dictionnary before running the NN Model
            linked_name = exact_map.get(CityMetro.normalize_name(text))
            if not linked_name:
                # ask the entity linking NN Model to predict the entity name
                linked_name = CityMetro.link_entity(text, model, embedding, labels)
                logger.info(f"*** entity linked from <{text}> to <{linked_name}> ***")

            entities[i]['value'] = linked_name
            entities[i]['extractor'] = CityMetro.name

        return entities

    def process(self, message, **kwargs):
        """ Look for city and metro entity and pass it to the entity linking model.  """

        # check for a city or metro entity detected by the Entity Extractor
        #   entities => [{'start': 9, 'end': 17, 'value': 'roberval', 'entity': 'city',
        #                 'confidence': 0.976792, 'extractor': 'CRFEntityExtractor'}]
        city_entities = [e for e in message.data.get('entities') if e['entity'] == 'city']
        metro_entities = [e for e in message.data.get('entities') if e['entity'] == 'metro']

        entities = []
        entities += self.link(city_entities, self.cities_model, self.cities_embedding, self.cities_labels, self.exact_map_cities)
        entities += self.link(metro_entities, self.metro_model, self.metro_embedding, self.metro_labels, self.exact_map_metro)

        if entities:
            message.set("entities", entities, add_to_output=True)

    def persist(self, file_name, model_dir):
        """ Persist this component to disk for future loading. """
        pass

    @staticmethod
    def create_exact_map(data_filename):
        """ Create a map of normalized version of the entity with the entity. """
        with open(data_filename) as f:
            content = f.readlines()

        return {CityMetro.normalize_name(entity): entity.strip() for entity in content}

    @staticmethod
    def normalize_name(s):
        # lower case and accents removed
        s = unidecode.unidecode(s).lower().strip()

        # replace apostrophe and dash by space
        s = s.replace("-", ' ')
        s = s.replace("'", ' ')

        return s

    @staticmethod
    def data_changed(filename):
        """
        Compare md5 value of specified file to detect changes.
        Returns True if file has changed or no previous md5 file saved, False otherwise.
        """
        if os.path.exists(filename):
            if os.path.exists(filename + '.md5'):
                # compute the md5 of the input file and compare to saved md5
                current_md5 = CityMetro.md5(filename)

                # read saved md5
                with open(filename + '.md5', 'r') as md5_file:
                    saved_md5 = md5_file.read()

                # compare to saved md5
                return (current_md5 != saved_md5)
            else:
                # md5 do not exists, then need to train
                return True
        else:
            logger.error(f"*** <{filename}> do not exists ***")

        return False

    @staticmethod
    def md5(fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def save_md5_file(filename):
        md5_hash = CityMetro.md5(filename)
        with open(filename + '.md5', 'w') as md5_file:
            md5_file.write(md5_hash)
