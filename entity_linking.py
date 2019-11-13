import hashlib
import logging
import math
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
        self.quartier_data_filename = "./fofe_entity_linking/quartiers.csv"

        # create exact match map from data
        self.exact_map_cities = self.create_exact_map(self.cities_data_filename)
        self.exact_map_metro = self.create_exact_map(self.metro_data_filename)
        self.exact_map_quartier = self.create_exact_map(self.quartier_data_filename)

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

        # load quartier model
        self.quartier_model, self.quartier_embedding = predict.load_models(
                                                "./fofe_entity_linking/models/quartiers.pth",
                                                "./fofe_entity_linking/data/quartiers_embedding.pth",
                                                "./fofe_entity_linking/data/quartiers_vocab.pickle")
        with open("./fofe_entity_linking/data/quartiers_training_labels.pickle", "rb") as quartier_label_file:
            self.quartier_labels, _, _ = pickle.load(quartier_label_file)
        logger.info(f"*** {len(self.quartier_labels)} quartiers ***")

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
        self.train_model("quartiers", "./train_quartiers.sh", self.quartier_data_filename)

    @staticmethod
    def expand_saint_abreviation(s):
        s = s.lower()

        # replace "st-" by "saint-" only when it's start with or is preceeded by a space or a dash.
        # to avoid situation like this:
        #        Saint-Juste-du-Lac  -->  Saint-Jusainte-du-Lac
        i = s.find('st-')
        if i >= 0 and (i == 0 or s[i-1] in [' ','-']):
            s = s.replace('st-', 'saint-', 1)

        i = s.find('st ')
        if i >= 0 and (i == 0 or s[i - 1] in [' ', '-']):
            s = s.replace('st ', 'saint ', 1)

        i = s.find('ste-')
        if i >= 0 and (i == 0 or s[i-1] in [' ','-']):
            s = s.replace('ste-', 'sainte-', 1)

        i = s.find('ste ')
        if i >= 0 and (i == 0 or s[i - 1] in [' ', '-']):
            s = s.replace('ste ', 'sainte ', 1)

        return s

    @staticmethod
    def link_entity_model_inference(text, model, embedding, labels, max_length=50):
        prediction = predict.predict(model, embedding, text, max_length)

        # max = prediction.argmax(1)[0]
        # predicted_label = labels[max]

        # top-k
        values, indices = prediction.topk(5)
        predicted_label = labels[indices[0][0]]
        predicted_prob = math.exp(values[0][0].item())
        # for rank, indice in enumerate(indices[0]):
        #     print(f'top {rank+1} ({math.exp(values[0][rank].item()):.10f}): {labels[indice]}')

        return predicted_label, predicted_prob

    @staticmethod
    def link(entities, model, embedding, labels, exact_map, model_name=""):
        for i, entity in enumerate(entities):
            text = CityMetro.expand_saint_abreviation(entity.get('value'))
            normalize_name = CityMetro.normalize_name(text)

            # check for a direct match in dictionary before running the NN Model
            linked_name = exact_map.get(normalize_name)
            if linked_name:
                probability = 1.0
                logger.info(f"*** {model_name} entity linked found in dictionary <{linked_name}> ({probability:.4f}) ***")
            else:
                # ask the entity linking NN Model to predict the entity name
                linked_name, probability = CityMetro.link_entity_model_inference(normalize_name, model, embedding, labels)
                logger.info(f"*** {model_name} entity linked from <{normalize_name}> to <{linked_name}> ({probability:.4f}) ***")

            entities[i]['value'] = linked_name
            entities[i]['entity linking confidence'] = probability
            entities[i]['entity linking'] = "entity_linking.CityMetro"

        return entities

    def process(self, message, **kwargs):
        """ Look for city and metro entity and pass it to the entity linking model.  """

        # check for a city or metro entity detected by the Entity Extractor
        #   entities => [{'start': 9, 'end': 17, 'value': 'roberval', 'entity': 'city',
        #                 'confidence': 0.976792, 'extractor': 'CRFEntityExtractor'}]
        city_entities = [e for e in message.data.get('entities') if e['entity'] == 'city']
        metro_entities = [e for e in message.data.get('entities') if e['entity'] == 'metro']
        quartier_entities = [e for e in message.data.get('entities') if e['entity'] == 'quartier']

        entities = []
        entities += self.link(city_entities, self.cities_model, self.cities_embedding, self.cities_labels, self.exact_map_cities, "cities")
        entities += self.link(metro_entities, self.metro_model, self.metro_embedding, self.metro_labels, self.exact_map_metro, "metro")
        entities += self.link(quartier_entities, self.quartier_model, self.quartier_embedding, self.quartier_labels, self.exact_map_quartier, "quartiers")

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

        # remove spaces around dash
        s = s.replace(" - ", ' ')

        # replace apostrophe and dash by space
        s = s.replace("-", ' ')
        s = s.replace("'", ' ')

        # replace multiple spaces by a single space
        s = s.replace("   ", ' ')
        s = s.replace("  ", ' ')

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
