from py2neo import Graph
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher


class ActionChargingPointInCity(Action):

    def name(self):
        return "action_charging_point_in_city"

    @staticmethod
    def count_charging_point_in_city(graph, city_name):
        return graph.run("MATCH (City {name:{cityName}})<-[:IN*]-(p:ChargingPoint) RETURN count(p)",
                         cityName=city_name).evaluate()

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        city_name = tracker.get_slot('city')

        if city_name:
            graph = Graph(password='abcd')
            count = self.count_charging_point_in_city(graph, city_name)

            dispatcher.utter_message(f"Il y a {count} bornes de recharge à {city_name}.")
        else:
            dispatcher.utter_message(f"Pour quel ville voulez-vous connaitre les bornes de recharge?")

        return []


class ActionChargingPointNearMetro(Action):

    def name(self):
        return "action_charging_point_near_metro"

    @staticmethod
    def normalize_metro_name(name):
        return name.title()

    @staticmethod
    def count_charging_point_near_metro(graph, city_name):
        return graph.run("MATCH (City {name:{cityName}})<-[:IN*]-(p:ChargingPoint) RETURN count(p)",
                         cityName=city_name).evaluate()

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        metro_name = self.normalize_metro_name(tracker.get_slot('metro')) if tracker.get_slot('metro') else None

        if metro_name:
            # graph = Graph(password='abcd')
            # count = self.count_charging_point_near_metro(graph, metro_name)
            #
            # dispatcher.utter_message(f"Il y a {count} bornes de recharge près du métro {metro_name}.")
            dispatcher.utter_message(f"Les bornes pres du metro ({metro_name}) sont:")
        else:
            dispatcher.utter_message(f"Pour quel métro voulez-vous connaitre les bornes de recharge?")

        return []
