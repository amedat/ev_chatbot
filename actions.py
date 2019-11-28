from py2neo import Graph
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher


class ActionChargingPointPlace(Action):

    def name(self):
        return "action_charging_point_place"

    def count_charging_point_in_city(self, graph, city_name):
        r = graph.run("MATCH (:City {name:{cityName}})<-[:IN]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
                       RETURN count(distinct park) as chargingParkCount, count(distinct point) as chargingPointCount",
                       cityName=city_name).data()
        return r[0]['chargingPointCount'], r[0]['chargingParkCount']

    def count_charging_point_near_metro(self, graph, metro_name):
        # Charging parks at less than 500m of Pie-IX metro station
        return graph.run(
            "MATCH (:MetroStation {name:{metroName}})-[n:NEARBY]-(p:ChargingPark) WHERE n.distance_km < 0.5 RETURN count(p)",
            metroName=metro_name).evaluate()

    def count_charging_point_in_quartier(self, graph, quartier_name):
        r = graph.run("MATCH (:QuartierMontreal {name:{quartierName}})<-[:IN]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
                       RETURN count(distinct park) as chargingParkCount, count(distinct point) as chargingPointCount",
                       quartierName=quartier_name).data()
        return r[0]['chargingPointCount'], r[0]['chargingParkCount']

    def count_charging_point_street(self, graph, street_name):
        r = graph.run("MATCH (:Street {name:{streetName}})-[:CROSS]->(:Intersection) \
                       <-[:NEARBY]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
                       RETURN count(distinct park) as chargingParkCount, count(distinct point) as chargingPointCount",
                       streetName=street_name).data()
        return r[0]['chargingPointCount'], r[0]['chargingParkCount']

    def is_entity_in_list(self, type, value, place_entities):
        """ Returns True if the type and value specified exists in the entity list. """
        found = next((e for e in place_entities if (e["entity"] == type and e['value'] == value)), None)
        return found is not None

    def is_type_equal(self, type_list, sorted_place_entities):
        return [e['entity'] for e in sorted_place_entities] == sorted(type_list)

    def get_sorted_place_entities(self, tracker):
        """ Return a sorted list by type of place entities from latest message and/or slots. """

        # extract places entities from latest message
        place_entities = [e for e in tracker.latest_message.get('entities')
                          if e['entity'] in ['city', 'metro', 'quartier', 'street']]

        if not place_entities:
            # add other places from slots
            for type in ['city', 'metro', 'quartier', 'street']:
                value = tracker.get_slot(type)
                if value and not self.is_entity_in_list(type, value, place_entities):
                    place_entities.append({'value': value, 'entity': type})

        return sorted(place_entities, key=lambda k: k['entity'])

    def dispatch_message(self, dispatcher, point_count, park_count, msg_none, msg_many_one, msg_many_many):
        if point_count == 0:
            msg = msg_none
        else:
            if park_count > 1:
                msg = msg_many_many
            else:
                msg = msg_many_one
        dispatcher.utter_message(msg)

    def single_entity(self, dispatcher, type, value):
        point_count = 0
        graph = Graph(password='abcd')

        if type == 'city':
            point_count, park_count = self.count_charging_point_in_city(graph, value)

            self.dispatch_message(dispatcher, point_count, park_count,
                                  f"Malheureusement, il n'y a aucune borne à {value}.",
                                  f"Il y a {point_count} bornes à {value}.",
                                  f"Il y a {point_count} bornes dans {park_count} emplacements à {value}.")

        elif type == 'metro':
            count = self.count_charging_point_near_metro(graph, value)
            dispatcher.utter_message(f"Il y a {count} emplacements à moins de 500m du métro {value}.")

        elif type == 'quartier':
            point_count, park_count = self.count_charging_point_in_quartier(graph, value)

            self.dispatch_message(dispatcher, point_count, park_count,
                                  f"Malheureusement, il n'y a aucune borne dans le quartier {value}.",
                                  f"Il y a {point_count} bornes dans le quartier {value}.",
                                  f"Il y a {point_count} bornes dans {park_count} emplacements dans le quartier {value}.")

        elif type == 'street':
            point_count, park_count = self.count_charging_point_street(graph, value)

            self.dispatch_message(dispatcher, point_count, park_count,
                                  f"Malheureusement, il n'y a aucune borne près de la rue {value}.",
                                  f"Il y a {point_count} bornes près de la rue {value}.",
                                  f"Il y a {point_count} bornes dans {park_count} emplacements près de la rue {value}.")

        return [SlotSet("found_charging_points", point_count if point_count > 0 else None)]

    def two_streets_charging_point(self, dispatcher, place_entities):
        graph = Graph(password='abcd')

        street_1 = place_entities[0]['value']
        street_2 = place_entities[1]['value']

        r = graph.run("MATCH (:Street {name:{streetName1}})-[:CROSS]->(i:Intersection)<-[:CROSS]-(:Street {name:{streetName2}}) \
                       MATCH (i)<-[:NEARBY]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
                       RETURN count(distinct park) as chargingParkCount, count(distinct point) as chargingPointCount",
                      streetName1=street_1, streetName2=street_2).data()

        if r[0]['chargingPointCount'] == 0:
            msg = f"Malheureusement, il n'y a aucune borne près de l'intersection {street_1} et {street_2}."
        else:
            if r[0]['chargingParkCount'] > 1:
                msg = f"Il y a {r[0]['chargingPointCount']} bornes dans {r[0]['chargingParkCount']} emplacements près de l'intersection {street_1} et {street_2}."
            else:
                msg = f"Il y a {r[0]['chargingPointCount']} bornes près de l'intersection {street_1} et {street_2}."
        dispatcher.utter_message(msg)

        return [SlotSet("found_charging_points", r[0]['chargingPointCount'] if r[0]['chargingPointCount'] > 0 else None)]

    def one_street_quartier_charging_point(self, dispatcher, place_entities):
        graph = Graph(password='abcd')

        quartier_name = [e for e in place_entities if e['entity'] == 'quartier'][0]['value']
        street_name = [e for e in place_entities if e['entity'] == 'street'][0]['value']

        r = graph.run("MATCH (:Street {name:{streetName}})-[:CROSS]->(i:Intersection)-[:IN]->(:QuartierMontreal {name:{quartierName}}) \
                       MATCH (i)<-[:NEARBY]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
                       RETURN count(distinct park) as chargingParkCount, count(distinct point) as chargingPointCount",
                      streetName=street_name, quartierName=quartier_name).data()

        if r[0]['chargingPointCount'] == 0:
            msg = f"Malheureusement, il n'y a aucune borne près {street_name} dans le quartier {quartier_name}."
        else:
            if r[0]['chargingParkCount'] > 1:
                msg = f"Il y a {r[0]['chargingPointCount']} bornes dans {r[0]['chargingParkCount']} emplacements près de {street_name} dans le quartier {quartier_name}."
            else:
                msg = f"Il y a {r[0]['chargingPointCount']} bornes près de {street_name} dans le quartier {quartier_name}."
        dispatcher.utter_message(msg)

        return [SlotSet("found_charging_points", r[0]['chargingPointCount'] if r[0]['chargingPointCount'] > 0 else None)]

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        place_entities = self.get_sorted_place_entities(tracker)
        entity_count = len(place_entities)

        if entity_count == 1:
            # Bornes à Montréal
            # Bornes près du métro Berri
            # Bornes dans le quartier Rosemont
            # Bornes sur la rue Saint-Laurent
            return self.single_entity(dispatcher, place_entities[0]['entity'], place_entities[0]['value'])
        
        elif entity_count == 2:
            if self.is_type_equal(['street', 'street'], place_entities):
                # Bornes au coin du boulevard Saint-Laurent et Sainte-Catherine
                return self.two_streets_charging_point(dispatcher, place_entities)

            elif self.is_type_equal(['quartier', 'street'], place_entities):
                # Bornes sur le boulevard Saint-Laurent dans le quartier Rosemont
                return self.one_street_quartier_charging_point(dispatcher, place_entities)

        else:
            dispatcher.utter_message(f"Pour quel endroit voulez-vous connaitre les bornes de recharge?")


class ActionRectifyCityMetro(Action):

    def name(self):
        return "action_rectify_city_metro"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message("Oups, désolé...")

        city_name = tracker.get_slot('city')
        metro_name = tracker.get_slot('metro')
        return [SlotSet("city", metro_name), SlotSet("metro", city_name)]


class ActionRectifyQuartierMetro(Action):

    def name(self):
        return "action_rectify_quartier_metro"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message("Oups, désolé...")

        metro_name = tracker.get_slot('metro')
        quartier_name = tracker.get_slot('quartier')
        return [SlotSet("quartier", metro_name), SlotSet("metro", quartier_name)]
