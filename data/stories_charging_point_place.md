## CITY - charging point
* ask_charging_point_place{"city":"montréal"}
  - action_charging_point_place
  - slot{"found_charging_points": 5}

## CITY RECTIFY TO METRO - charging point
* ask_charging_point_place{"city":"sherbrooke"}
  - slot{"city": "sherbrooke"}
  - action_charging_point_place
  - slot{"found_charging_points": 5}
* inform_rectify_city_metro
  - action_rectify_city_metro
  - slot{"metro": "sherbrooke"}
  - slot{"city": null}
  - action_charging_point_place 
  - slot{"found_charging_points": 2}

## METRO - charging point
* ask_charging_point_place{"metro":"angrignon"}
  - action_charging_point_place
  - slot{"found_charging_points": 5}

## METRO RECTIFY TO CITY - charging point
* ask_charging_point_place{"metro":"longueuil"}
  - slot{"metro": "longueuil"}
  - action_charging_point_place
  - slot{"found_charging_points": 5}
* inform_rectify_city_metro
  - action_rectify_city_metro
  - slot{"city": "longueuil"}
  - slot{"metro": null}
  - action_charging_point_place 
  - slot{"found_charging_points": 2}

## METRO RECTIFY TO QUARTIER - charging point ##
* ask_charging_point_place{"metro":"côte-des-neiges"}
  - slot{"metro": "côte-des-neiges"}
  - action_charging_point_place
  - slot{"found_charging_points": 5}
* inform_rectify_quartier_metro
  - action_rectify_quartier_metro
  - slot{"quartier": "côte-des-neiges"}
  - slot{"metro": null}
  - action_charging_point_place 
  - slot{"found_charging_points": 2}

## QUARTIER - charging point
* ask_charging_point_place{"quartier":"le plateau"}
  - action_charging_point_place
  - slot{"found_charging_points": 5}

## QUARTIER RECTIFY TO METRO - charging point
* ask_charging_point_place{"quartier":"rosemont"}
  - slot{"quartier":"rosemont"}
  - action_charging_point_place
  - slot{"found_charging_points": 5}
* inform_rectify_quartier_metro
  - action_rectify_quartier_metro
  - slot{"metro": "rosemont"}
  - slot{"quartier": null}
  - action_charging_point_place 
  - slot{"found_charging_points": 2}

## STREET - charging point, one street
* ask_charging_point_place{"street":"saint-laurent"}
  - action_charging_point_place
  - slot{"found_charging_points": 5}

## STREET - charging point, two streets
* ask_charging_point_place{"street":"saint-laurent", "street":"sainte-catherine"}
  - action_charging_point_place
  - slot{"found_charging_points": 5}

## STREET - charging point, one street + quartier
* ask_charging_point_place{"street":"saint-laurent", "quartier":"centre-ville"}
  - action_charging_point_place
  - slot{"found_charging_points": 5}


## CITY - charging point + greet
* greet
  - utter_greet
* ask_charging_point_place{"city":"roberval"}
  - action_charging_point_place
  - slot{"found_charging_points": 5}

## METRO - charging point + greet
* greet
  - utter_greet
* ask_charging_point_place{"metro":"verdun"}
  - action_charging_point_place
  - slot{"found_charging_points": 5}

## QUARTIER - charging point + greet
* greet
  - utter_greet
* ask_charging_point_place{"quartier":"ile-des-soeurs"}
  - action_charging_point_place
  - slot{"found_charging_points": 5}
