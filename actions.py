import logging

from py2neo import Graph
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

logger = logging.getLogger(__name__)


class ActionChargingPointPlace(Action):

    def __init__(self):
        super(ActionChargingPointPlace, self).__init__()

        self.graph = Graph(password='abcd')
        logger.info(f"({self.name()}) Connected to Neo4J Graph")

    def name(self):
        return "action_charging_point_place"

    def count_charging_point_in_city(self, city_name):
        r = self.graph.run("MATCH (:City {name:{cityName}})<-[:IN]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
                       RETURN count(distinct park) as chargingParkCount, count(distinct point) as chargingPointCount",
                       cityName=city_name).data()
        return r[0]['chargingPointCount'], r[0]['chargingParkCount']

    def count_charging_park_near_metro(self, metro_name):
        """ Charging parks at less than 500m of Pie-IX metro station """
        r = self.graph.run(
            "MATCH (c:City {name:'Montréal'})<-[:IN]-(:MetroStation {name:{metroName}})-[n:NEARBY]-(p:ChargingPark) \
             WHERE n.distance_km < 0.5 RETURN count(p) AS chargingParkCount, c.name AS cityName",
            metroName=metro_name).data()

        return r[0]['chargingParkCount'], r[0]['cityName']

    def count_charging_point_in_quartier(self, quartier_name):
        r = self.graph.run(
            "MATCH (q:QuartierMontreal {name:{quartierName}})<-[:IN]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
             MATCH (q)-[:QUARTIER_OF]->(c:City) \
             RETURN count(distinct park) as chargingParkCount, count(distinct point) as chargingPointCount, c.name AS cityName",
            quartierName=quartier_name).data()
        return r[0]['chargingPointCount'], r[0]['chargingParkCount'], r[0]['cityName']

    def count_charging_point_street(self, street_name):
        # number of charging parks and charging points near an intersection crossed by a specific street
        # quartier list of those intersections
        q = self.graph.run("MATCH (c:City {name:'Montréal'})<-[:IN]-(:Street {name:{streetName}})-[:CROSS]-> \
                       (i:Intersection)<-[:NEARBY]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
                       MATCH (q:QuartierMontreal)<-[:IN]-(i) \
                       RETURN count(distinct park) AS chargingParkCount, count(distinct point) AS chargingPointCount, \
                              c.name AS cityName, collect(distinct q.name) AS quartierNames, \
                              collect(distinct park.name) AS parkNames",
                       streetName=street_name).data()

        return q[0]['chargingPointCount'], q[0]['chargingParkCount'], q[0]['cityName'], q[0]['quartierNames'], q[0]['parkNames']

    def is_street_in_city(self, street_name, city_name):
        q = self.graph.run("MATCH (s:Street {name:{streetName}})-[:IN]->(c:City {name:{cityName}}) \
                            RETURN count(s)",
                           streetName=street_name, cityName=city_name).evaluate()
        return q > 0

    def is_street_in_quartier(self, street_name, quartier_name):
        q = self.graph.run("MATCH (s:Street {name:{streetName}})-[:CROSS]->(:Intersection)-[:IN]-> \
                            (q:QuartierMontreal {name:{quartierName}}) RETURN count(s)",
                           streetName=street_name, quartierName=quartier_name).evaluate()
        return q > 0

    def is_quartier_of_city(self, quartier_name, city_name):
        q = self.graph.run("MATCH (q:QuartierMontreal {name:{quartierName}})-[:QUARTIER_OF]->(c:City {name:{cityName}}) \
                            RETURN count(q)",
                           quartierName=quartier_name, cityName=city_name).evaluate()
        return q > 0

    def is_entity_in_list(self, type, value, place_entities):
        """ Returns True if the type and value specified exists in the entity list. """
        found = next((e for e in place_entities if (e["entity"] == type and e['value'] == value)), None)
        return found is not None

    def is_type_equal(self, type_list, sorted_place_entities):
        return [e['entity'] for e in sorted_place_entities] == sorted(type_list)

    def get_sorted_place_entities(self, tracker):
        """ Return a sorted list by type of place entities from latest message and/or slots. """
        place_entities = []

        # extract places entities from latest message
        # ex: msg_entities = [{'value': 'Centre-Ville', 'entity': 'quartier'}, {'value': 'Saint-Laurent', 'entity': 'street'}]
        msg_entities = [e for e in tracker.latest_message.get('entities')
                        if e['entity'] in ['city', 'metro', 'quartier', 'street']]
        msg_entities = sorted(msg_entities, key=lambda k: k['entity'])

        # ['quartier', 'street']
        msg_entities_type = [e['entity'] for e in msg_entities]

        # extract places from slots
        # ex: slots_entities = [{'value': 'Montréal', 'entity': 'city'}]
        slots_entities = []
        for type in ['city', 'metro', 'quartier', 'street']:
            value = tracker.get_slot(type)
            if value and not self.is_entity_in_list(type, value, place_entities):
                slots_entities.append({'value': value, 'entity': type})

        # parse current slots and keep only those that are still valid
        if ['quartier'] == msg_entities_type:
            quartier_name = msg_entities[0]['value']
            for slot in slots_entities:
                if 'city' == slot['entity']:
                    if self.is_quartier_of_city(quartier_name, slot['value']):
                        place_entities.append(slot)
                elif 'street' == slot['entity']:
                    if self.is_street_in_quartier(slot['value'], quartier_name):
                        place_entities.append(slot)

        if ['city'] == msg_entities_type:
            city_name = msg_entities[0]['value']
            for slot in slots_entities:
                if 'quartier' == slot['entity']:
                    if self.is_quartier_of_city(city_name, slot['value']):
                        place_entities.append(slot)
                elif 'street' == slot['entity']:
                    if self.is_street_in_city(city_name, slot['value']):
                        place_entities.append(slot)

        place_entities += msg_entities

        return sorted(place_entities, key=lambda k: k['entity'])

    def dispatch_message(self, dispatcher, point_count, park_count, park_names,
                         msg_none, msg_many_one, msg_many_many):
        """
        dispatch a custom message based on the number of charging park and charging points and
        returns the SlotSet list
        """
        if point_count == 0:
            msg = msg_none
        else:
            if park_count > 1:
                msg = msg_many_many
            else:
                msg = msg_many_one
        dispatcher.utter_message(msg)

        if park_count == 0:
            return [SlotSet("found_charging_points", None),
                    SlotSet("found_some_charging_points", None),
                    SlotSet("found_many_charging_points", None)]

        if park_count == 1:
            return [SlotSet("found_charging_points", park_names),
                    SlotSet("found_some_charging_points", None),
                    SlotSet("found_many_charging_points", None)]

        if park_count <= 5:
            return [SlotSet("found_charging_points", None),
                    SlotSet("found_some_charging_points", point_count),
                    SlotSet("found_many_charging_points", None)]

        return [SlotSet("found_charging_points", None),
                SlotSet("found_some_charging_points", None),
                SlotSet("found_many_charging_points", point_count)]

    def single_entity(self, dispatcher, type, value):
        """
        Bornes à Montréal
        Bornes près du métro Berri
        Bornes dans le quartier Rosemont
        Bornes sur la rue Saint-Laurent
        """
        slots = []

        if type == 'city':
            point_count, park_count = self.count_charging_point_in_city(value)

            slots = self.dispatch_message(
                            dispatcher, point_count, park_count, None,
                            f"Malheureusement, il n'y a aucune borne à {value}.",
                            f"Il y a {point_count} bornes à {value}.",
                            f"Il y a {point_count} bornes dans {park_count} emplacements à {value}.")

            slots.append(SlotSet("metro", None))
            slots.append(SlotSet("street", None))
            slots.append(SlotSet("quartier", None))

        elif type == 'metro':
            park_count, city_name = self.count_charging_park_near_metro(value)
            dispatcher.utter_message(f"Il y a {park_count} emplacements à moins de 500m du métro {value}.")

            slots.append(SlotSet("city", city_name))
            slots.append(SlotSet("quartier", None))
            slots.append(SlotSet("street", None))

        elif type == 'quartier':
            point_count, park_count, city_name = self.count_charging_point_in_quartier(value)

            slots = self.dispatch_message(
                            dispatcher, point_count, park_count, None,
                            f"Malheureusement, il n'y a aucune borne dans le quartier {value}.",
                            f"Il y a {point_count} bornes dans le quartier {value}.",
                            f"Il y a {point_count} bornes dans {park_count} emplacements dans le quartier {value}.")

            slots.append(SlotSet("city", city_name))
            slots.append(SlotSet("metro", None))
            slots.append(SlotSet("street", None))

        elif type == 'street':
            point_count, park_count, city_name, quartier_names, park_names = self.count_charging_point_street(value)

            slots = self.dispatch_message(
                            dispatcher, point_count, park_count, park_names,
                            f"Malheureusement, il n'y a aucune borne près de la rue {value}.",
                            f"Il y a {point_count} bornes près de la rue {value}.",
                            f"Il y a {point_count} bornes dans {park_count} emplacements près de la rue {value}.")

            slots.append(SlotSet("city", city_name))
            slots.append(SlotSet("quartier", quartier_names))
            slots.append(SlotSet("metro", None))

        return slots

    def two_streets_charging_point(self, dispatcher, place_entities):
        """ Bornes au coin du boulevard Saint-Laurent et Sainte-Catherine """

        street_1 = place_entities[0]['value']
        street_2 = place_entities[1]['value']

        r = self.graph.run(
                "MATCH (:Street {name:{streetName1}})-[:CROSS]->(i:Intersection)<-[:CROSS]-(:Street {name:{streetName2}}) \
                 MATCH (i)<-[:NEARBY]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
                 MATCH (q:QuartierMontreal)<-[:IN]-(i) \
                 MATCH (q)-[:QUARTIER_OF]->(c:City) \
                 RETURN count(distinct park) as chargingParkCount, count(distinct point) as chargingPointCount, \
                        q.name AS quartierName, c.name AS cityName, collect(distinct park.name) AS parkNames",
                 streetName1=street_1, streetName2=street_2).data()

        park_count = r[0]['chargingParkCount']
        point_count = r[0]['chargingPointCount']
        slots = self.dispatch_message(
                        dispatcher, point_count, park_count, r[0]['parkNames'],
                        f"Malheureusement, il n'y a aucune borne près de l'intersection {street_1} et {street_2}.",
                        f"Il y a {point_count} bornes près de l'intersection {street_1} et {street_2}.",
                        f"Il y a {point_count} bornes dans {park_count} emplacements près de l'intersection {street_1} et {street_2}.")

        slots.append(SlotSet("street", [street_1, street_2]))

        slots.append(SlotSet("city", r[0]['cityName']))
        slots.append(SlotSet("quartier", r[0]['quartierName']))
        slots.append(SlotSet("metro", None))

        return slots

    def one_street_quartier_charging_point(self, dispatcher, place_entities):
        """ Bornes sur le boulevard Saint-Laurent dans le quartier Rosemont """

        quartier_name = [e for e in place_entities if e['entity'] == 'quartier'][0]['value']
        street_name = [e for e in place_entities if e['entity'] == 'street'][0]['value']

        r = self.graph.run("MATCH (:Street {name:{streetName}})-[:CROSS]->(i:Intersection)-[:IN]->(q:QuartierMontreal {name:{quartierName}}) \
                       MATCH (i)<-[:NEARBY]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
                       MATCH (q)-[:QUARTIER_OF]->(c:City) \
                       RETURN count(distinct park) as chargingParkCount, count(distinct point) as chargingPointCount, \
                              c.name AS cityName, collect(distinct park.name) AS parkNames",
                      streetName=street_name, quartierName=quartier_name).data()

        park_count = r[0]['chargingParkCount']
        point_count = r[0]['chargingPointCount']
        slots = self.dispatch_message(
                        dispatcher, point_count, park_count, r[0]['parkNames'],
                        f"Malheureusement, il n'y a aucune borne près {street_name} dans le quartier {quartier_name}.",
                        f"Il y a {point_count} bornes près de {street_name} dans le quartier {quartier_name}.",
                        f"Il y a {point_count} bornes dans {park_count} emplacements près de {street_name} dans le quartier {quartier_name}.")

        slots.append(SlotSet("city", r[0]['cityName']))
        slots.append(SlotSet("metro", None))

        return slots

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
        
        elif entity_count >= 2:
            if self.is_type_equal(['street', 'street'], place_entities) or \
               self.is_type_equal(['quartier', 'street', 'street'], place_entities) or \
               self.is_type_equal(['city', 'quartier', 'street', 'street'], place_entities):
                # Bornes au coin du boulevard Saint-Laurent et Sainte-Catherine
                return self.two_streets_charging_point(dispatcher, place_entities)

            elif self.is_type_equal(['quartier', 'street'], place_entities) or \
                 self.is_type_equal(['city', 'quartier', 'street'], place_entities):
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


class ActionPresentChargingParks(Action):

    def __init__(self):
        super(ActionPresentChargingParks, self).__init__()

        self.graph = Graph(password='abcd')
        logger.info(f"({self.name()}) Connected to Neo4J Graph")

    def name(self):
        return "action_present_charging_parks"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        found_charging_points = tracker.get_slot('found_charging_points')

        if len(found_charging_points) > 0:
            address, intersection_name, distance_m = self.get_charging_park_info(found_charging_points[0])

            multiple_of_50 = int(distance_m / 50)
            dist_str = "à moins de 50 mètres de l'intersection" if multiple_of_50 == 1 else f"à environ de {multiple_of_50 * 50} mètres de l'intersection"

            dispatcher.utter_message(
                f"La borne est située au {address}, {dist_str} {intersection_name.replace('/',' et ')}.")
        else:
            logger.error("found_charging_points slot is empty")

        return []

    def get_charging_park_info(self, charging_park_name):
        # return nearest intersection (sorted by distance) to the specified charging park location
        r = self.graph.run(
            "MATCH (i:Intersection)<-[:NEARBY]-(park:ChargingPark {name:{parkName}})<-[:IN]-(point:ChargingPoint) \
             WITH i, park, distance(i.location, park.location) AS dist \
             RETURN park.streetAddress AS address, i.name AS intersectionName, dist ORDER BY dist ASC LIMIT 10",
             parkName=charging_park_name).data()

        return r[0]['address'], r[0]['intersectionName'], r[0]['dist']

class ActionSendChargingParks(Action):

    def name(self):
        return "action_send_charging_parks"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message("Les informations sur la borne de recharge ont été envoyées!")
        return []

class ActionRequestPlacePrecision(Action):

    def name(self):
        return "action_request_place_precision"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # extract relevant slots
        city = tracker.get_slot('city')
        metro = tracker.get_slot('metro')
        streets = tracker.get_slot('street')
        quartiers = tracker.get_slot('quartier')

        # make sure street and quartier are list of string
        if streets:
            streets = streets if isinstance(streets, list) else streets.split(',')
        if quartiers:
            quartiers = quartiers if isinstance(quartiers, list) else quartiers.split(',')

        case = self.select_case(city, metro, streets, quartiers)

        if case == "one street and quartier list":
            self.ask_to_choose_from_quartiers(dispatcher, quartiers)

        elif case == "city only":
            if city == "Montréal":
                dispatcher.utter_message(f"Vous cherchez dans quel quartier ou quelles rues?")

        return []

    def select_case(self, city, metro, streets, quartiers):
        if streets and quartiers:
            if len(streets) == 1 and len(quartiers) > 1:
                return "one street and quartier list"

        if city and not quartiers and not streets:
            return "city only"

        return None

    def ask_to_choose_from_quartiers(self, dispatcher, quartiers):
        quartiers_str = ", ".join(quartiers[:-1]) + " ou " + quartiers[-1]
        dispatcher.utter_message(f"Dans lequel des {len(quartiers)} quartiers suivant: {quartiers_str}?")
