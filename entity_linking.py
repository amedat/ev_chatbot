import logging
import pickle

import fofe_entity_linking.predict as predict

from rasa_nlu.components import Component


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

        self.cities_model, self.cities_embedding = predict.load_models(
                                                "./fofe_entity_linking/models/cities_fofe_model.pth",
                                                "./fofe_entity_linking/data/cities_embedding.pth",
                                                "./fofe_entity_linking/data/cities_vocab.pickle")
        with open("./fofe_entity_linking/data/cities_training_labels.pickle", "rb") as cities_label_file:
            self.cities_labels, _, _ = pickle.load(cities_label_file)
        logger.info(f"*** {len(self.cities_labels)} cities ***")

        self.metro_model, self.metro_embedding = predict.load_models(
                                                "./fofe_entity_linking/models/metro_fofe_model.pth",
                                                "./fofe_entity_linking/data/metro_embedding.pth",
                                                "./fofe_entity_linking/data/metro_vocab.pickle")
        with open("./fofe_entity_linking/data/metro_training_labels.pickle", "rb") as metro_label_file:
            self.metro_labels, _, _ = pickle.load(metro_label_file)
        logger.info(f"*** {len(self.metro_labels)} metro stations ***")

    def train(self, training_data, cfg, **kwargs):
        pass

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
    def link(entities, model, embedding, labels):
        for i, entity in enumerate(entities):
            text = CityMetro.expand_saint_abreviation(entity.get('value'))
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
        entities += self.link(city_entities, self.cities_model, self.cities_embedding, self.cities_labels)
        entities += self.link(metro_entities, self.metro_model, self.metro_embedding, self.metro_labels)

        if entities:
            message.set("entities", entities, add_to_output=True)

    def persist(self, file_name, model_dir):
        """ Persist this component to disk for future loading. """
        pass
