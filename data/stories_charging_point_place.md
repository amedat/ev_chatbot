## CITY - charging point
* ask_charging_point_place{"city":"montréal"}
  - slot{"city": "Montréal"}
  - action_charging_point_place
  - slot{"found_many_charging_points": 900}
  - slot{"found_some_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"metro": null}
  - slot{"street": null}
  - slot{"quartier": null}

## CITY RECTIFY TO METRO - charging point
* ask_charging_point_place{"city":"sherbrooke"}
  - slot{"city": "sherbrooke"}
  - action_charging_point_place
  - slot{"found_many_charging_points": 50}
  - slot{"found_some_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"metro": null}
  - slot{"street": null}
  - slot{"quartier": null}
* inform_rectify_city_metro
  - action_rectify_city_metro
  - slot{"metro": "sherbrooke"}
  - slot{"city": null}
  - action_charging_point_place 
  - slot{"found_some_charging_points": 5}
  - slot{"found_many_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"city": "Montréal"}
  - slot{"street": null}
  - slot{"quartier": null}

## METRO - charging point
* ask_charging_point_place{"metro":"angrignon"}
  - slot{"metro": "Angrignon"}
  - action_charging_point_place
  - slot{"found_some_charging_points": 5}
  - slot{"found_many_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"city": "Montréal"}
  - slot{"street": null}
  - slot{"quartier": null}

## METRO RECTIFY TO CITY - charging point
* ask_charging_point_place{"metro":"longueuil"}
  - slot{"metro": "Longueuil-Universite-De-Sherbrooke"}
  - action_charging_point_place
  - slot{"found_some_charging_points": 5}
  - slot{"found_many_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"city": "Montréal"}
  - slot{"street": null}
  - slot{"quartier": null}
* inform_rectify_city_metro
  - action_rectify_city_metro
  - slot{"city": "longueuil"}
  - slot{"metro": null}
  - action_charging_point_place 
  - slot{"found_many_charging_points": 50}
  - slot{"found_some_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"metro": null}
  - slot{"street": null}
  - slot{"quartier": null}

## METRO RECTIFY TO QUARTIER - charging point ##
* ask_charging_point_place{"metro":"côte-des-neiges"}
  - slot{"metro": "Côte-des-neiges"}
  - action_charging_point_place
  - slot{"found_some_charging_points": 5}
  - slot{"found_many_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"city": "Montréal"}
  - slot{"street": null}
  - slot{"quartier": null}
* inform_rectify_quartier_metro
  - action_rectify_quartier_metro
  - slot{"quartier": "Côte-des-neiges"}
  - slot{"metro": null}
  - action_charging_point_place 
  - slot{"found_many_charging_points": 25}
  - slot{"found_some_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"city": null}
  - slot{"street": null}
  - slot{"metro": null}

## QUARTIER - charging point
* ask_charging_point_place{"quartier":"le plateau"}
  - slot{"quartier": "Le Plateau"}
  - action_charging_point_place
  - slot{"found_many_charging_points": 25}
  - slot{"found_some_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"city": null}
  - slot{"street": null}
  - slot{"metro": null}

## QUARTIER RECTIFY TO METRO - charging point
* ask_charging_point_place{"quartier":"rosemont"}
  - slot{"quartier":"Rosemont"}
  - action_charging_point_place
  - slot{"found_many_charging_points": 25}
  - slot{"found_some_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"city": null}
  - slot{"street": null}
  - slot{"metro": null}
* inform_rectify_quartier_metro
  - action_rectify_quartier_metro
  - slot{"metro": "rosemont"}
  - slot{"quartier": null}
  - action_charging_point_place 
  - slot{"found_some_charging_points": 5}
  - slot{"found_many_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"city": null}
  - slot{"street": null}
  - slot{"metro": null}

## STREET - charging point, one street
* ask_charging_point_place{"street":"saint-laurent"}
  - slot{"street":"Saint-Laurent"}
  - action_charging_point_place
  - slot{"found_many_charging_points": 25}
  - slot{"found_some_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"city": "Montréal"}
  - slot{"quartier": ["Le Plateau", "Centre-Ville", "Vieux-Montréal", "Villeray", "Ahuntsic", "Petite-Patrie"]}
  - slot{"metro": null}

## STREET - charging point, two streets
* ask_charging_point_place{"street":"saint-laurent", "street":"sainte-catherine"}
  - slot{"street":"Saint-Laurent"}
  - action_charging_point_place
  - slot{"found_some_charging_points": 5}
  - slot{"found_many_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"city": "Montréal"}
  - slot{"quartier": "Centre-Ville"}
  - slot{"street":["Saint-Laurent", "Sainte-Catherine"]}
  - slot{"metro": null}

## STREET - charging point, one street + quartier
* ask_charging_point_place{"street":"saint-laurent", "quartier":"centre-ville"}
  - slot{"street":"Saint-Laurent"}
  - slot{"quartier":"Centre-Ville"}
  - action_charging_point_place
  - slot{"found_some_charging_points": 5}
  - slot{"found_many_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"city": "Montréal"}
  - slot{"metro": null}


## CITY - charging point + greet
* greet
  - utter_greet
* ask_charging_point_place{"city":"roberval"}
  - slot{"city":"roberval"}
  - action_charging_point_place
  - slot{"found_some_charging_points": 5}
  - slot{"found_many_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"metro": null}
  - slot{"quartier": null}
  - slot{"street": null}

## METRO - charging point + greet
* greet
  - utter_greet
* ask_charging_point_place{"metro":"verdun"}
  - slot{"metro": "Verdun"}
  - action_charging_point_place
  - slot{"found_some_charging_points": 5}
  - slot{"found_many_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"city": "Montréal"}
  - slot{"street": null}
  - slot{"quartier": null}

## QUARTIER - charging point + greet
* greet
  - utter_greet
* ask_charging_point_place{"quartier":"ile-des-soeurs"}
  - slot{"quartier": "Ile-des-soeurs"}
  - action_charging_point_place
  - slot{"found_many_charging_points": 25}
  - slot{"found_some_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"city": null}
  - slot{"street": null}
  - slot{"metro": null}
