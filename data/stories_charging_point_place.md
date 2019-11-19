## CITY - charging point
* ask_charging_point_place{"city":"montréal"}
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## CITY - charging point
* ask_charging_point_place{"city":"saguenay"}
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## CITY - charging point
* ask_charging_point_place{"city":"trois-rivieres"}
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## METRO - charging point
* ask_charging_point_place{"metro":"angrignon"}
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## METRO - charging point
* ask_charging_point_place{"metro":"beaubien"}
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## METRO - charging point
* ask_charging_point_place{"metro":"square-victoria"}
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## QUARTIER - charging point
* ask_charging_point_place{"quartier":"le plateau"}
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## QUARTIER - charging point
* ask_charging_point_place{"quartier":"centre-ville"}
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## QUARTIER - charging point
* ask_charging_point_place{"quartier":"ahuntsic"}
  - action_charging_point_place
  - slot{"found_charging_point": 5}


## CITY - charging point + greet
* greet
  - utter_greet
* ask_charging_point_place{"city":"roberval"}
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## METRO - charging point + greet
* greet
  - utter_greet
* ask_charging_point_place{"metro":"verdun"}
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## QUARTIER - charging point + greet
* greet
  - utter_greet
* ask_charging_point_place{"quartier":"ile-des-soeurs"}
  - action_charging_point_place
  - slot{"found_charging_point": 5}
