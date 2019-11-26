from py2neo import Graph
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher


class ActionChargingPoinPlace(Action):

    def name(self):
        return "action_charging_point_place"

    @staticmethod
    def count_charging_point_in_city(graph, city_name):
        return graph.run("MATCH (City {name:{cityName}})<-[:IN*]-(p:ChargingPoint) RETURN count(p)",
                         cityName=city_name).evaluate()

    @staticmethod
    def count_charging_point_near_metro(graph, metro_name):
        # Charging parks at less than 500m of Pie-IX metro station
        return graph.run(
            "MATCH (MetroStation {name:{metroName}})-[n:NEARBY]-(p:ChargingPark) WHERE n.distance_km < 0.5 RETURN count(p)",
            metroName=metro_name).evaluate()

    @staticmethod
    def count_charging_point_in_quartier(graph, quartier_name):
        return graph.run("MATCH (QuartierMontreal {name:{quartierName}})<-[:IN*]-(p:ChargingPoint) RETURN count(p)",
                         quartierName=quartier_name).evaluate()

    @staticmethod
    def count_charging_point_street(graph, street_name):
        return graph.run("MATCH (Street {name:{streetName}})-[:CROSS]->(Intersection)<-[:NEARBY]-(ChargingPark)<-[:IN]-(p:ChargingPoint) RETURN count(p)",
                         streetName=street_name).evaluate()

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        count = 0
        type = None

        # First, look for paramaters from message
        msg_entities = tracker.latest_message.get('entities')
        if msg_entities and len(msg_entities) > 0:
            # Retrieve params from message
            type = msg_entities[0].get('entity')
            value = msg_entities[0].get('value')
        else:
            # Since there is nothing in message, then retrieve from slots
            if tracker.get_slot('city'):
                type, value = ('city', tracker.get_slot('city'))
            elif tracker.get_slot('metro'):
                type, value = ('metro', tracker.get_slot('metro'))
            elif tracker.get_slot('quartier'):
                type, value = ('quartier', tracker.get_slot('quartier'))
            elif tracker.get_slot('street'):
                type, value = ('street', tracker.get_slot('street'))

        if type:
            graph = Graph(password='abcd')

            if type == 'city':
                count = self.count_charging_point_in_city(graph, value)
                dispatcher.utter_message(f"Il y a {count} bornes de recharge à {value}.")
            elif type == 'metro':
                count = self.count_charging_point_near_metro(graph, value)
                dispatcher.utter_message(f"Il y a {count} endroits à moins de 500m du métro {value}.")
            elif type == 'quartier':
                count = self.count_charging_point_in_quartier(graph, value)
                dispatcher.utter_message(f"Il y a {count} bornes dans le quartier {value}.")
            elif type == 'street':
                count = self.count_charging_point_street(graph, value)
                dispatcher.utter_message(f"Il y a {count} bornes près de la rue {value}.")
        else:
            dispatcher.utter_message(f"Pour quel endroit voulez-vous connaitre les bornes de recharge?")

        return [SlotSet("found_charging_point", count if count > 0 else None)]


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
