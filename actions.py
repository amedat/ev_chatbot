import logging

from py2neo import Graph
from typing import Any, Text, Dict, List, Union

from rasa_sdk import Action, Tracker
from rasa_sdk.forms import FormAction
from rasa_sdk.events import SlotSet, Form
from rasa_sdk.executor import CollectingDispatcher

logger = logging.getLogger(__name__)


class ChargingPlaceForm(FormAction):

    CITIES_WITH_QUARTIER = []

    def __init__(self):
        super(ChargingPlaceForm, self).__init__()

        self.graph = Graph(password='abcd')
        logger.info(f"({self.name()}) Connected to Neo4J Graph")

        ChargingPlaceForm.CITIES_WITH_QUARTIER = self.get_cities_with_quartier()
        logger.info(f"cities with quartiers: {ChargingPlaceForm.CITIES_WITH_QUARTIER}")

    def name(self):
        return "charging_place_form"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        *** OVERRIDES ***

        Execute the side effects of this form.

        Steps:
        - activate if needed
        - validate user input if needed
        - set validated slots
        - utter_ask_{slot} template with the next required slot
        - submit the form if all required slots are set
        - deactivate the form
        """

        # ---------------------------------------------------------------
        # The part between these two lines is a custom part

        # correct entity extracted if a slots has been requested,
        # the extractor guess it wrong (frequent situation with one word message)
        self.correct_entity_based_on_requested_slot(tracker)

        # ---------------------------------------------------------------

        # activate the form
        events = self._activate_if_required(dispatcher, tracker, domain)
        # validate user input
        events.extend(self._validate_if_required(dispatcher, tracker, domain))
        # check that the form wasn't deactivated in validation
        if Form(None) not in events:

            # ---------------------------------------------------------------
            # The part between these two lines is a custom part

            events = self.search_charging_place(dispatcher, tracker, events)

            # ---------------------------------------------------------------

            # create temp tracker with populated slots from `validate` method
            temp_tracker = tracker.copy()
            for e in events:
                if e["event"] == "slot":
                    temp_tracker.slots[e["name"]] = e["value"]

            next_slot_events = self.request_next_slot(dispatcher, temp_tracker, domain)

            if next_slot_events is not None:
                # request next slot
                events.extend(next_slot_events)
            else:
                # there is nothing more to request, so we can submit
                self._log_form_slots(temp_tracker)
                logger.debug("Submitting the form '{}'".format(self.name()))
                events.extend(self.submit(dispatcher, temp_tracker, domain))
                # deactivate the form after submission
                events.extend(self.deactivate())

        return events

    def correct_entity_based_on_requested_slot(self, tracker):
        """
        Check for an incorrectly set entity when the bot requested a specific entity.

        Example:
            - message text: Verdun
            - requested_slot is 'quartier'
            - message entity extracted: 'street' (Verdun street with 1.0 confidence)
            - entity_linking module predict: 'quartier' (Verdun quartier with 1.0 confidence)

            At this stage, the form knows it's looking for a 'quartier' (the NLU did not had this information).
            We can safely assume that the entity extractor made a bad guess and reverting the decision.
        """
        requested_slot = tracker.get_slot('requested_slot')
        if requested_slot:
            # do we have a value for the requested slot?
            requested_slot_value = next(tracker.get_latest_entity_values(requested_slot), None)
            if not requested_slot_value:
                # the latest message do not contain the requested slot,
                # check for an extractor mistake and make the correction (if any)
                for e in tracker.latest_message['entities']:
                    e_type = e['entity']
                    e_confidence = e['confidence']

                    requested_entity = e['entity_linking'][requested_slot]
                    requested_entity_confidence = requested_entity['confidence']

                    if requested_entity_confidence >= e_confidence:
                        # there is high probability that the extractor made an error,
                        # make the correction by assigning the predicted entity to the requested slot
                        e['entity'] = requested_slot
                        e['value'] = requested_entity['value']
                        e['confidence'] = requested_entity_confidence
                        logger.debug(f"The form <{self.name()}> is reverting the decision of NLU "
                                     f"based on requested_slot: {e_type} -> {requested_slot}\n")

    def search_charging_place(self, dispatcher, tracker, events):
        """
        Search knowledge base using current slots (city, metro, quartier, street) to fill these slots:
            - found_charging_points
            - found_some_charging_points
            - found_many_charging_points
        """
        place_entities = self.get_sorted_place_entities(tracker, events)

        new_slot_events = []
        entity_count = len(place_entities)

        if entity_count == 1:
            # Bornes à Montréal
            # Bornes près du métro Berri
            # Bornes dans le quartier Rosemont
            # Bornes sur la rue Saint-Laurent
            # Bornes au coin Saint-Laurent et Sainte-Catherine (street: ['Saint-Laurent', 'Sainte-Catherine'])
            new_slot_events = self.single_entity(dispatcher, place_entities[0]['entity'], place_entities[0]['value'])

        elif entity_count >= 2:
            if self.is_type_equal(['quartier', 'street'], place_entities) or \
               self.is_type_equal(['city', 'street'], place_entities) or \
               self.is_type_equal(['city', 'quartier', 'street'], place_entities):

                street = [e['value'] for e in place_entities if e['entity'] == 'street'][0]
                if isinstance(street, list):
                    # Bornes au coin du boulevard Saint-Laurent et Sainte-Catherine
                    new_slot_events = self.two_streets_charging_point(dispatcher, street)
                else:
                    # Bornes sur le boulevard Saint-Laurent dans le quartier Rosemont
                    new_slot_events = self.one_street_quartier_charging_point(dispatcher, place_entities)

            elif self.is_type_equal(['city', 'quartier'], place_entities) or \
                 self.is_type_equal(['city', 'metro'], place_entities):
                # Bornes dans le quartier Rosemont/metro Berri (with city slot already filled)
                new_slot_events = self.single_entity(dispatcher, place_entities[1]['entity'], place_entities[1]['value'])

        # remove all slot events and add the new ones.
        # events = [e for e in events if e['event'] != 'slot']
        events.extend(new_slot_events)

        return events

    @staticmethod
    def required_slots(tracker: Tracker) -> List[Text]:
        """
        A list of required slots that the form has to fill.

        Returning [] to state that form is complete,
        otherwise, returns slots in order you want them to be requested.

        Note: always returns all slots, otherwise the value of slots other than the requested one won't be extracted
        """
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

        # first check if we found an acceptable amount of places to be presented to the user for the current request
        found_charging_points = tracker.get_slot('found_charging_points')
        if found_charging_points:
            found_list = found_charging_points if isinstance(found_charging_points, list) else found_charging_points.split(',')
            # found a small list, we got it!
            if len(found_list) <= 5:
                return []

            if metro:
                return []

            # found a somewhat large list, let's see if we can get more precise location
            if city:
                # the city has no quartier, so we can't get any more precise
                if city not in ChargingPlaceForm.CITIES_WITH_QUARTIER:
                    return []

                # the city has some quartiers but user already specified one
                if quartiers and len(quartiers) == 1:
                    return []

        required_slots = ["city", "quartier", "street", "metro"]

        if city and not quartiers and not streets:
            if city == "Montréal":
                # city of Montreal --> ask for a quartier
                # (knowledge base do not have quartier nor streets for other cities)
                required_slots = ["quartier", "street", "city", "metro"]

        if streets and quartiers:
            if len(streets) == 1 and len(quartiers) > 1:
                # one street and quartier list --> ask to choose a quartier from the list
                required_slots = ["quartier", "street", "city", "metro"]
                # reset quartier slot, otherwise it will ask for the metro...
                tracker.slots['quartier'] = None

            elif len(streets) == 1 and len(quartiers) == 1:
                # one street and a quartier --> ask a crossing street
                required_slots = ["street", "city", "metro"]

        if streets and not quartiers:
            if len(streets) == 1:
                # one street but no quartier --> ask for a quartier
                required_slots = ["quartier", "street", "city", "metro"]

        return required_slots

    def slot_mappings(self) -> Dict[Text, Union[Dict, List[Dict]]]:
        """A dictionary to map required slots to
            - an extracted entity
            - intent: value pairs
            - a whole message
              or a list of them, where a first match will be picked"""

        return {
            "city": self.from_entity(entity="city", intent=["request_charging_place", "inform"]),
            "metro": self.from_entity(entity="metro", intent=["request_charging_place", "inform"]),
            "street": self.from_entity(entity="street", intent=["request_charging_place", "inform"]),
            "quartier": self.from_entity(entity="quartier", intent=["request_charging_place", "inform"]),
        }

    def validate_city(self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker,
                         domain: Dict[Text, Any],) -> Dict[Text, Any]:
        """Validate city value."""

        if isinstance(value, str):
            # validation succeeded, set the value of the "city" slot to value
            return {"city": value}
        else:
            # dispatcher.utter_template("utter_wrong_city", tracker)
            # validation failed, set this slot to None, meaning the user will be asked for the slot again
            return {"city": None}

    def validate_metro(self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker,
                         domain: Dict[Text, Any],) -> Dict[Text, Any]:
        """Validate metro value."""

        if isinstance(value, str):
            # validation succeeded, set the value of the "metro" slot to value
            return {"metro": value}
        else:
            # validation failed, set this slot to None, meaning the user will be asked for the slot again
            return {"metro": None}

    def validate_quartier(self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker,
                         domain: Dict[Text, Any],) -> Dict[Text, Any]:
        """Validate quartier value."""

        if isinstance(value, str):
            # validation succeeded, set the value of the "quartier" slot to value
            return {"quartier": value}
        else:
            # validation failed, set this slot to None, meaning the user will be asked for the slot again
            return {"quartier": None}

    def validate_street(self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker,
                         domain: Dict[Text, Any],) -> Dict[Text, Any]:
        """Validate street value."""

        # TODO - receive a str or a list

        return {"street": value}

        # if isinstance(value, str):
        #     # validation succeeded, set the value of the "street" slot to value
        #     return {"street": value}
        # else:
        #     # validation failed, set this slot to None, meaning the user will be asked for the slot again
        #     return {"street": None}

    def submit(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any],) -> List[Dict]:
        """Define what the form has to do
            after all required slots are filled"""

        # utter submit template
        # dispatcher.utter_template("utter_submit", tracker)
        dispatcher.utter_message(f"*** form submitted ***")
        return []

    def count_charging_point_in_city(self, city_name):
        d = self.graph.run("MATCH (:City {name:{cityName}})<-[:IN]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
                       RETURN count(distinct park) as chargingParkCount, count(distinct point) as chargingPointCount",
                       cityName=city_name).data()
        return d[0]['chargingPointCount'], d[0]['chargingParkCount']

    def count_charging_park_near_metro(self, metro_name):
        """ Charging parks at less than 500m of Pie-IX metro station """
        d = self.graph.run(
            "MATCH (c:City)<-[:IN]-(m:MetroStation {name:{metroName}})-[n:NEARBY]-(park:ChargingPark) \
             MATCH (q:QuartierMontreal)<-[:IN]-(m) \
             WHERE n.distance_km < 0.5 \
             RETURN count(park) AS chargingParkCount, c.name AS cityName, q.name AS quartierNames, \
                    collect(distinct park.name) AS parkNames",
            metroName=metro_name).data()

        return d[0]['chargingParkCount'], d[0]['cityName'], d[0]['quartierNames'], d[0]['parkNames']

    def count_charging_point_in_quartier(self, quartier_name):
        d = self.graph.run(
            "MATCH (q:QuartierMontreal {name:{quartierName}})<-[:IN]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
             MATCH (q)-[:QUARTIER_OF]->(c:City) \
             RETURN count(distinct park) as chargingParkCount, count(distinct point) as chargingPointCount, c.name AS cityName",
            quartierName=quartier_name).data()
        return d[0]['chargingPointCount'], d[0]['chargingParkCount'], d[0]['cityName']

    def count_charging_point_street(self, street_name):
        # number of charging parks and charging points near an intersection crossed by a specific street
        # quartier list of those intersections
        d = self.graph.run("MATCH (c:City {name:'Montréal'})<-[:IN]-(:Street {name:{streetName}})-[:CROSS]-> \
                       (i:Intersection)<-[:NEARBY]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
                       MATCH (q:QuartierMontreal)<-[:IN]-(i) \
                       RETURN count(distinct park) AS chargingParkCount, count(distinct point) AS chargingPointCount, \
                              c.name AS cityName, collect(distinct q.name) AS quartierNames, \
                              collect(distinct park.name) AS parkNames",
                       streetName=street_name).data()

        return d[0]['chargingPointCount'], d[0]['chargingParkCount'], d[0]['cityName'], d[0]['quartierNames'], d[0]['parkNames']

    def get_city_park_names(self, city_name):
        d = self.graph.run("MATCH (:City {name:{cityName}})<-[:IN]-(park:ChargingPark) \
                       RETURN collect(distinct park.name) AS parkNames",
                       cityName=city_name).data()
        return d[0]['parkNames']

    def is_street_in_city(self, street_name, city_name):
        d = self.graph.run("MATCH (s:Street {name:{streetName}})-[:IN]->(c:City {name:{cityName}}) \
                            RETURN count(s)",
                           streetName=street_name, cityName=city_name).evaluate()
        return d > 0

    def is_street_in_quartier(self, street_name, quartier_name):
        d = self.graph.run("MATCH (s:Street {name:{streetName}})-[:CROSS]->(:Intersection)-[:IN]-> \
                            (q:QuartierMontreal {name:{quartierName}}) RETURN count(s)",
                           streetName=street_name, quartierName=quartier_name).evaluate()
        return d > 0

    def is_quartier_of_city(self, quartier_name, city_name):
        d = self.graph.run("MATCH (q:QuartierMontreal {name:{quartierName}})-[:QUARTIER_OF]->(c:City {name:{cityName}}) \
                            RETURN count(q)",
                           quartierName=quartier_name, cityName=city_name).evaluate()
        return d > 0

    def get_cities_with_quartier(self):
        d = self.graph.run("MATCH (q:QuartierMontreal)-[:QUARTIER_OF]->(c:City) \
                            RETURN collect(distinct c.name) AS cityList").data()
        return d[0]['cityList']

    def is_entity_in_list(self, type, value, place_entities):
        """ Returns True if the type and value specified exists in the entity list. """
        found = next((e for e in place_entities if (e["entity"] == type and e['value'] == value)), None)
        return found is not None

    def is_type_equal(self, type_list, sorted_place_entities):
        return [e['entity'] for e in sorted_place_entities] == sorted(type_list)

    def get_sorted_place_entities(self, tracker, events):
        """
        Return a sorted list by type of place entities from latest message and/or slots.

        events: [
         {'event': 'slot', 'timestamp': None, 'name': 'quartier', 'value': 'Centre-Ville'},
         {'event': 'slot', 'timestamp': None, 'name': 'street', 'value': 'Saint-Laurent'},
         {'event': 'slot', 'timestamp': None, 'name': 'requested_slot', 'value': 'street'}
        ]
        """
        place_entities = []

        # extract places entities from latest message processed by the form
        # ex: msg_entities = [{'value': 'Centre-Ville', 'entity': 'quartier'}, {'value': 'Saint-Laurent', 'entity': 'street'}]
        msg_entities = [{'value': e['value'], 'entity': e['name']} for e in events
                        if e['event'] == 'slot' and e['name'] in ['city', 'metro', 'quartier', 'street']]
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

        if ['street'] == msg_entities_type:
            street_name = msg_entities[0]['value']
            if isinstance(street_name, list):
                # if the value is a list of street, take the first one
                street_name = street_name[0]

            for slot in slots_entities:
                if 'city' == slot['entity']:
                    if self.is_street_in_city(street_name, slot['value']):
                        place_entities.append(slot)
                elif 'quartier' == slot['entity']:
                    if self.is_street_in_quartier(street_name, slot['value']):
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
            return [SlotSet("found_charging_points", park_names),
                    SlotSet("found_some_charging_points", park_count),
                    SlotSet("found_many_charging_points", None)]

        return [SlotSet("found_charging_points", park_names),
                SlotSet("found_some_charging_points", None),
                SlotSet("found_many_charging_points", park_count)]

    def single_entity(self, dispatcher, type, value):
        """
        Bornes à Montréal
        Bornes près du métro Berri
        Bornes dans le quartier Rosemont
        Bornes sur la rue Saint-Laurent
        Bornes au coin de la rue Saint-Laurent et Sainte-Catherine (street: ['Saint-Laurent', 'Sainte-Catherine'])
        """
        slots = []

        if type == 'city':
            point_count, park_count = self.count_charging_point_in_city(value)

            park_names = None
            if value not in ChargingPlaceForm.CITIES_WITH_QUARTIER:
                park_names = self.get_city_park_names(value)

            slots = self.dispatch_message(
                            dispatcher, point_count, park_count, park_names,
                            f"Malheureusement, il n'y a aucune borne à {value}.",
                            f"Il y a {point_count} bornes à {value}.",
                            f"Il y a {point_count} bornes dans {park_count} emplacements à {value}.")

            slots.append(SlotSet("metro", None))
            slots.append(SlotSet("street", None))
            slots.append(SlotSet("quartier", None))

        elif type == 'metro':
            park_count, city_name, quartier_names, park_names = self.count_charging_park_near_metro(value)

            slots = self.dispatch_message(
                            dispatcher, park_count, park_count, park_names,
                            f"Malheureusement, il n'y a aucune borne près du métro {value}.",
                            f"Il y a {park_count} emplacements à moins de 500m du métro {value}.",
                            f"Il y a {park_count} emplacements à moins de 500m du métro {value}.")

            slots.append(SlotSet("city", city_name))
            slots.append(SlotSet("quartier", quartier_names))
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
            if isinstance(value, list):
                slots = self.two_streets_charging_point(dispatcher, value)
            else:
                point_count, park_count, city_name, quartier_names, park_names = self.count_charging_point_street(value)

                quartiers = quartier_names if isinstance(quartier_names, list) else quartier_names.split(',')

                if quartiers and len(quartiers) > 1:
                    # utter the quartier list
                    quartiers_str = ", ".join(quartiers[:-1]) + " et " + quartiers[-1]
                    if len(quartiers) > 3:
                        quartiers_str = f"dans les {len(quartiers)} quartiers suivant: {quartiers_str}"
                    else:
                        quartiers_str = f"dans les quartiers {quartiers_str}"

                    slots = self.dispatch_message(
                                    dispatcher, point_count, park_count, park_names,
                                    f"Malheureusement, il n'y a aucune borne près de la rue {value}.",
                                    f"Près de la rue {value}, il y a {park_count} emplacements {quartiers_str}.",
                                    f"Près de la rue {value}, il y a {park_count} emplacements {quartiers_str}.")
                else:
                    slots = self.dispatch_message(
                                    dispatcher, point_count, park_count, park_names,
                                    f"Malheureusement, il n'y a aucune borne près de la rue {value}.",
                                    f"Il y a {park_count} emplacements près de la rue {value}.",
                                    f"Il y a {park_count} emplacements près de la rue {value}.")

                slots.append(SlotSet("city", city_name))
                slots.append(SlotSet("quartier", quartier_names))
                slots.append(SlotSet("metro", None))

        return slots

    def two_streets_charging_point(self, dispatcher, street_list):
        """ Bornes au coin du boulevard Saint-Laurent et Sainte-Catherine """

        street_1 = street_list[0]
        street_2 = street_list[1]

        d = self.graph.run(
                "MATCH (:Street {name:{streetName1}})-[:CROSS]->(i:Intersection)<-[:CROSS]-(:Street {name:{streetName2}}) \
                 MATCH (i)<-[:NEARBY]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
                 MATCH (q:QuartierMontreal)<-[:IN]-(i) \
                 MATCH (q)-[:QUARTIER_OF]->(c:City) \
                 RETURN count(distinct park) as chargingParkCount, count(distinct point) as chargingPointCount, \
                        q.name AS quartierName, c.name AS cityName, collect(distinct park.name) AS parkNames",
                 streetName1=street_1, streetName2=street_2).data()

        if d:
            park_count = d[0]['chargingParkCount']
            point_count = d[0]['chargingPointCount']
            slots = self.dispatch_message(
                            dispatcher, point_count, park_count, d[0]['parkNames'],
                            f"Malheureusement, il n'y a aucune borne près de l'intersection {street_1} et {street_2}",
                            f"Il y a {point_count} bornes près de l'intersection {street_1} et {street_2}",
                            f"Il y a {point_count} bornes dans {park_count} emplacements près de l'intersection {street_1} et {street_2}")

            slots.append(SlotSet("street", [street_1, street_2]))

            slots.append(SlotSet("city", d[0]['cityName']))
            slots.append(SlotSet("quartier", d[0]['quartierName']))
            slots.append(SlotSet("metro", None))
        else:
            # intersection not found... may be the two street are parallele
            dispatcher.utter_message(f"Désolé, je ne connais pas l'intersection {street_1} et {street_2}")
            slots = [SlotSet("street", None)]

        return slots

    def one_street_quartier_charging_point(self, dispatcher, place_entities):
        """ Bornes sur le boulevard Saint-Laurent dans le quartier Rosemont """

        try:
            quartier_name = [e for e in place_entities if e['entity'] == 'quartier'][0]['value']
            street_name = [e for e in place_entities if e['entity'] == 'street'][0]['value']
        except IndexError as e:
            # in case one of the entity is missing
            return []

        d = self.graph.run("MATCH (:Street {name:{streetName}})-[:CROSS]->(i:Intersection)-[:IN]->(q:QuartierMontreal {name:{quartierName}}) \
                       MATCH (i)<-[:NEARBY]-(park:ChargingPark)<-[:IN]-(point:ChargingPoint) \
                       MATCH (q)-[:QUARTIER_OF]->(c:City) \
                       RETURN count(distinct park) as chargingParkCount, count(distinct point) as chargingPointCount, \
                              c.name AS cityName, collect(distinct park.name) AS parkNames",
                      streetName=street_name, quartierName=quartier_name).data()

        park_count = d[0]['chargingParkCount']
        point_count = d[0]['chargingPointCount']
        slots = self.dispatch_message(
                        dispatcher, point_count, park_count, d[0]['parkNames'],
                        f"Malheureusement, il n'y a aucune borne près {street_name} dans le quartier {quartier_name}.",
                        f"Il y a {point_count} bornes près de {street_name} dans le quartier {quartier_name}.",
                        f"Il y a {point_count} bornes dans {park_count} emplacements près de {street_name} dans le quartier {quartier_name}.")

        slots.append(SlotSet("city", d[0]['cityName']))
        slots.append(SlotSet("metro", None))

        return slots


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

        if found_charging_points and len(found_charging_points) > 0:
            address, intersection_name, distance_m, metro_nearby = self.get_charging_park_info(found_charging_points[0])

            if intersection_name and distance_m:
                la_plus_proche_str = " la plus proche" if len(found_charging_points) > 1 else ""
                metro_nearby_str = f", près du métro {metro_nearby}" if metro_nearby else ""

                multiple_of_50 = int(distance_m / 50)
                dist_str = "tout juste à l'intersection" if multiple_of_50 <= 1 else f"à environ de {multiple_of_50 * 50} mètres de l'intersection"

                dispatcher.utter_message(
                    f"La borne{la_plus_proche_str} est située au {address}, {dist_str} {intersection_name.replace('/',' et ')}{metro_nearby_str}")
            else:
                dispatcher.utter_message(f"La borne est située au {address}")

        else:
            logger.error("found_charging_points slot is empty")

        return []

    def get_charging_park_info(self, charging_park_name):
        """return nearest intersection (sorted by distance) to the specified charging park location"""
        # TODO: distance from metro (and other POI) if nearby
        d = self.graph.run(
            "MATCH (i:Intersection)<-[:NEARBY]-(park:ChargingPark {name:{parkName}})<-[:IN]-(point:ChargingPoint) \
             OPTIONAL MATCH (park)-[near_metro:NEARBY]->(m:MetroStation) \
             WHERE near_metro.distance_km < 0.150 \
             WITH i, park, distance(i.location, park.location) AS dist, m.name AS metroName \
             RETURN count(i), collect(distinct metroName) as metroNearby, \
                    park.streetAddress AS address, i.name AS intersectionName, dist ORDER BY dist ASC LIMIT 10",
             parkName=charging_park_name).data()

        if d:
            metro_nearby = d[0]['metroNearby'][0] if d[0]['metroNearby'] else None
            return d[0]['address'], d[0]['intersectionName'], d[0]['dist'], metro_nearby
        else:
            d = self.graph.run(
                "MATCH (park:ChargingPark {name:{parkName}})<-[:IN]-(point:ChargingPoint) \
                 RETURN park.streetAddress AS address",
                parkName=charging_park_name).data()

            return d[0]['address'], None, None, None


class ActionSendChargingParks(Action):

    def name(self):
        return "action_send_charging_parks"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message("Les informations sur la borne de recharge ont été envoyées!")
        return []
