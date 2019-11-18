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
    def predict_entity_linking(entities, model, embedding, labels, exact_map, entity_predicted):
        """
        Make a prediction for each given entities using the given model and store the result
        in the entity dict under the key "entity_linking".

        Example for metro model with CRFEntityExtractor that extracted a city entity.
        entities:         [{'start': 9, 'end': 17, 'value': 'longueuil', 'entity': 'city', 'confidence': 0.976792, 'extractor': 'CRFEntityExtractor'}]

        Returns entities: [{'start': 9, 'end': 17, 'value': 'longueuil', 'entity': 'city', 'confidence': 0.976792, 'extractor': 'CRFEntityExtractor',
                            'entity_linking': {
                                'metro': {'value': 'Longueuil-Université-de-Sherbrooke', 'confidence': 0.9953, 'module': 'entity_linking.CityMetro'}
                            }
                          }]
        """
        for i, entity in enumerate(entities):
            text = CityMetro.expand_saint_abreviation(entity.get('value'))
            normalized_name = CityMetro.normalize_name(text)

            # check for a direct match in dictionary before running the NN Model
            linked_name = exact_map.get(normalized_name)
            if linked_name:
                probability = 1.0
                logger.info(f"*** {entity_predicted} entity linked found in dictionary <{linked_name}> ({probability:.4f}) ***")
            else:
                # ask the entity linking NN Model to predict the entity name
                linked_name, probability = CityMetro.link_entity_model_inference(normalized_name, model, embedding, labels)
                logger.info(f"*** {entity_predicted} entity linked from <{normalized_name}> to <{linked_name}> ({probability:.4f}) ***")

            if not entities[i].get('entity_linking'):
                entities[i]['entity_linking'] = {}
            if not entities[i]['entity_linking'].get(entity_predicted):
                entities[i]['entity_linking'][entity_predicted] = {}

            entities[i]['entity_linking'][entity_predicted]['value'] = linked_name
            entities[i]['entity_linking'][entity_predicted]['confidence'] = probability
            entities[i]['entity_linking'][entity_predicted]['input'] = normalized_name
            entities[i]['entity_linking'][entity_predicted]['module'] = "entity_linking.CityMetro"

        return entities

    def process(self, message, **kwargs):
        """ Look for city, metro and quartier entity and pass it to the entity linking model.  """

        # check for a city or metro entity detected by the Entity Extractor
        #   entities => [{'start': 16, 'end': 25, 'value': 'longueuil', 'entity': 'metro', 'confidence': 0.99112538,
        #                 'extractor': 'CRFEntityExtractor'}]
        entities = [e for e in message.get('entities') if e['entity'] in ['city', 'metro', 'quartier']]

        if entities:
            self.predict_entity_linking(entities, self.cities_model, self.cities_embedding, self.cities_labels, self.exact_map_cities, "city")
            self.predict_entity_linking(entities, self.metro_model, self.metro_embedding, self.metro_labels, self.exact_map_metro, "metro")
            self.predict_entity_linking(entities, self.quartier_model, self.quartier_embedding, self.quartier_labels, self.exact_map_quartier, "quartier")

            # logger.info(f"*** {entities} ***")
            # entities example:
            # [
            #   {
            #     'start': 16,
            #     'end': 25,
            #     'value': 'longueuil',
            #     'entity': 'metro',
            #     'confidence': 0.9911253808966003,
            #     'extractor': 'CRFEntityExtractor',
            #
            #     'entity_linking': {
            #       'city': {
            #         'value': 'Longueuil',
            #         'confidence': 1.0,
            #         'input': 'longueuil',
            #         'module': 'entity_linking.CityMetro'
            #       },
            #       'metro': {
            #         'value': 'Longueuil-Université-de-Sherbrooke',
            #         'confidence': 0.999599060347744,
            #         'input': 'longueuil',
            #         'module': 'entity_linking.CityMetro'
            #       },
            #       'quartier': {
            #         'value': 'Vieux-Montréal',
            #         'confidence': 0.3658391254377098,
            #         'input': 'longueuil',
            #         'module': 'entity_linking.CityMetro'
            #       }
            #     }
            #   }
            # ]

            for entity in entities:
                # default is entity selected by CRFEntityExtractor
                selected_entity = entity['entity']

                # print(message.text)

                # DISAMBIGUATION
                if entity['entity'] == 'city':
                    if entity['entity_linking']['metro']['confidence'] > 0.80:
                        if any(keyword in message.text[:entity['start']] for keyword in ['métro', 'station']):
                            # some keywords confirm that we are talking of a metro station.
                            # ex: <Longueuil> the city or the metro station: "bornes à la station Longueuil"
                            selected_entity = 'metro'

                    if entity['entity_linking']['quartier']['confidence'] > 0.80:
                        if any(keyword in message.text[:entity['start']] for keyword in ['quartier', 'arrondissement']):
                            # some keywords confirm that we are talking of a quartier of Montreal.
                            # ex: <Rosemont> guess as <Rougemont> city but is a quartier: "bornes dans le quartier Rosemont"
                            selected_entity = 'quartier'
                        elif (entity['entity_linking']['quartier']['confidence'] > 0.95 and
                              entity['entity_linking']['quartier']['confidence'] > entity['entity_linking']['city']['confidence']):
                            # no keyword found but the confidence is very strong about a quartier instead of a city.
                            # ex: <Rosemont> guess as <Rougemont> city but is a quartier: "bornes dans Rosemont"
                            selected_entity = 'quartier'

                # apply the entity found by entity linking model
                if entity['entity'] != selected_entity:
                    logger.info(f"*** CRFEntityExtractor decision changed ***")
                    entity['old_entity'] = entity['entity']
                    entity['old_confidence'] = entity['confidence']

                entity['value'] = entity['entity_linking'][selected_entity]['value']
                entity['confidence'] = entity['entity_linking'][selected_entity]['confidence']
                entity['entity'] = selected_entity

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


class MatchIntent(Component):
    """
    Make sure the select intent match the entity extracted from the current message.
    If the entity name is not part of the intent name then check for the second ranking
    intent for a match and update if required.

    Ex:
        - message intent name: ask_charging_point_city
        - message entity name: metro
        - intent_ranking = [
              {
                'name': 'ask_charging_point_city',
                'confidence': 0.6711967573629241
              },
              {
                'name': 'ask_charging_point_metro',
                'confidence': 0.3057607654890056
              },
              {
                'name': 'mood_unhappy',
                'confidence': 0.013120531057085248
              } ]

        Assuming the entity linking (done in a previous step of the NLU pipeline) is correct,
        we can affirm that the second intent was the correct one, so we update the intent.
    """

    name = "entity_linking"

    provides = ["intent"]

    requires = ["intent", "entities"]

    defaults = {}

    language_list = None

    def __init__(self, component_config=None):
        super(MatchIntent, self).__init__(component_config)

    def train(self, training_data, cfg, **kwargs):
        pass

    def process(self, message, **kwargs):
        entities = [e for e in message.get('entities') if e['entity'] in ['city', 'metro', 'quartier']]

        if len(entities) >= 1:
            entity_name = entities[0].get('entity')  # String, one of ['city', 'metro', 'quartier']

            # check for the intent name containing the name of the entity found.
            # ex: intent "ask_charging_point_city" contains the entity name "city"
            intent_name = message.get('intent').get('name')
            if not entity_name in intent_name:

                intent_ranking = sorted(message.get('intent_ranking'), key=lambda k: k['confidence'], reverse=True)
                if len(intent_ranking) >= 2:
                    second_intent = intent_ranking[1]

                    # for intent "ask_charging_point_city" and entity name "metro",
                    # we would have expected "ask_charging_point_metro"
                    expected_intent_name = intent_name
                    for n in ['city', 'metro', 'quartier']:
                        expected_intent_name = expected_intent_name.replace(n, entity_name)

                    if second_intent.get('name') == expected_intent_name:
                        # the second guess intent was the correct one, update the intent!
                        message.set("intent", second_intent, add_to_output=True)
                        logger.info(f"*** updated intent <{message.get('intent').get('name')}> <-- entity <{entity_name}> + intent <{intent_name}> | {message.text} ***")

    def persist(self, file_name, model_dir):
        """ Persist this component to disk for future loading. """
        pass
