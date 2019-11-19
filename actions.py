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

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        count = 0

        msg_entities = tracker.latest_message.get('entities')
        if msg_entities and len(msg_entities) > 0:
            msg_entity_type = msg_entities[0].get('entity')
            msg_entity_value = msg_entities[0].get('value')

            if msg_entity_type:
                graph = Graph(password='abcd')

                if msg_entity_type == 'city':
                    count = self.count_charging_point_in_city(graph, msg_entity_value)
                    dispatcher.utter_message(f"Il y a {count} bornes de recharge à {msg_entity_value}.")
                elif msg_entity_type == 'metro':
                    count = self.count_charging_point_near_metro(graph, msg_entity_value)
                    dispatcher.utter_message(f"Il y a {count} endroits à moins de 500m du métro {msg_entity_value}.")
                elif msg_entity_type == 'quartier':
                    count = self.count_charging_point_in_quartier(graph, msg_entity_value)
                    dispatcher.utter_message(f"Il y a {count} bornes dans le quartier {msg_entity_value}.")
        else:
            dispatcher.utter_message(f"Pour quel endroit voulez-vous connaitre les bornes de recharge?")

        return [SlotSet("found_charging_point", count)] if count > 0 else []
