## ----- CORRECT ENTITIES SPELLING -----

## city
* ask_charging_point_place: combien de bornes de recharge à [Saguenay](city)?
  - action_charging_point_place

## metro
* ask_charging_point_place: bornes près du métro [Laurier](metro)
  - action_charging_point_place

## quartier
* ask_charging_point_place: bornes dans le quartier [Rosemont](quartier)?
  - action_charging_point_place

## ----- SMALL ENTITIES MISPELLING -----

## city
* ask_charging_point_place: Combien de place pour recharger à [Saint Felcien](city:Saint-Félicien)
  - action_charging_point_place

## metro
* ask_charging_point_place: Est-ce qu'il y a des bornes proche du métro [st henry](metro:Place-Saint-Henri) ?
  - action_charging_point_place

## quartier
* ask_charging_point_place: bornes dans le quartier [Iles des soeur](quartier:Ile-des-soeurs)
  - action_charging_point_place

## ----- METRO WITHOUT ACCENT (NORMALIZATION.PY MODULE) -----

## metro
* ask_charging_point_place: Est-ce qu'il y a des bornes pres du metro [st henry](metro:Place-Saint-Henri)
  - action_charging_point_place

## ----- CITY DISAMBIGUATION -----

## city ofter identified as metro by the CRFEntityExtractor
* ask_charging_point_place: bornes à [jean richelieu](city:Saint-Jean-sur-Richelieu)?
  - action_charging_point_place

## ----- STATION DISAMBIGUATION -----

## metro
* ask_charging_point_place: dans le bout de la station [du castelno](metro:De Castelnau) combien de endroit pour recharger 
  - action_charging_point_place

## metro
* ask_charging_point_place: où ce qu'y sont les station de recharge à proximité de [Saint Robert Bellarmin](city:Saint-Robert-Bellarmin) 
  - action_charging_point_place

## metro
* ask_charging_point_place: bornes à la station [rosemont](metro:Rosemont)? 
  - action_charging_point_place
  
## ----- QUARTIER DISAMBIGUATION -----

## quartier
##* ask_charging_point_place: bornes à [rosemont](quartier:Rosemont) 
##  - action_charging_point_place

## quartier
* ask_charging_point_place: bornes dans [rosemont](quartier:Rosemont) 
  - action_charging_point_place

## ----- USER RECTIFY ENTITY -----

## city rectify to metro
* ask_charging_point_place: combien de bornes de recharge à [Sherbrooke](city)?
  - action_charging_point_place
* inform_rectify_city_metro: non, pas la ville de [Sherbrooke](city), la station de métro
  - action_rectify_city_metro
  - action_charging_point_place

## metro rectify to city
* ask_charging_point_place: bornes au metro [Sherbrooke](metro)
  - action_charging_point_place
* inform_rectify_city_metro: je parle de la ville pas de la station 
  - action_rectify_city_metro
  - action_charging_point_place 
  - slot{"found_some_charging_points": 5}
  - slot{"found_many_charging_points": null}
  - slot{"found_charging_points": null}

## quartier rectify to metro
* ask_charging_point_place: combien de place pour recharger dans l'arrondissement [Rosemont](quartier) 
  - slot{"quartier": "Rosemont"}
  - action_charging_point_place
* inform_rectify_quartier_metro: non, le metro [Rosemont](metro) pas le quartier
  - action_rectify_quartier_metro
  - slot{"metro": "Rosemont"}
  - slot{"quartier": null}
  - action_charging_point_place 
  - slot{"found_some_charging_points": null}
  - slot{"found_many_charging_points": null}
  - slot{"found_charging_points": ["1780 | BHR | VER | 201 Berlioz : La Station"]}
  - slot{"city": "Montréal"}
  - slot{"quartier": "Rosemont"}
  - slot{"metro": null}
  - action_present_charging_parks
  - utter_prompt_send_charging_parks
* affirm
  - action_send_charging_parks

## metro rectify to quartier
* ask_charging_point_place: combien de bornes proche du metro [cote des neiges](metro:Côte-des-Neiges)
  - slot{"metro": "Côte-des-Neiges"}
  - action_charging_point_place
* inform_rectify_quartier_metro: pas le metro, le quartier
  - action_rectify_quartier_metro
  - slot{"quartier": "Côte-des-Neiges"}
  - action_charging_point_place 
  - slot{"found_many_charging_points": 25}
  - slot{"found_some_charging_points": null}
  - slot{"found_charging_points": null}
  - slot{"city": null}
  - slot{"street": null}
  - slot{"metro": null}
  - action_request_place_precision
* ask_charging_point_place{"street":"van horne"}
  - slot{"street":"Van horne"}
  - action_charging_point_place
  - slot{"found_some_charging_points": null}
  - slot{"found_many_charging_points": null}
  - slot{"found_charging_points": ["1780 | BHR | VER | 201 Berlioz : La Station"]}
  - slot{"city": "Montréal"}
  - slot{"quartier": "Côte-des-neiges"}
  - slot{"metro": null}
  - action_present_charging_parks
  - utter_prompt_send_charging_parks
* affirm
  - action_send_charging_parks

## ----- STREETS -----

## two streets intersection: bornes au coin du boulevard Saint-Laurent et Sainte-Catherine
* ask_charging_point_place: bornes au coin du boulevard [Saint-Laurent](street) et [Sainte-Catherine](street)
  - slot{"street": "Saint-Laurent"}
  - action_charging_point_place
  - slot{"found_many_charging_points": null}
  - slot{"found_some_charging_points": null}
  - slot{"found_charging_points": ["1780 | BHR | VER | 201 Berlioz : La Station"]}
  - slot{"city": "Montréal"}
  - slot{"quartier": "Centre-Ville"}
  - slot{"metro": null}
  - action_present_charging_parks
  - utter_prompt_send_charging_parks
 * affirm: oui
  - action_send_charging_parks

## one street + quartier: bornes sur le boulevard saint-laurent dans le quartier centre-ville
* ask_charging_point_place: bornes sur le boulevard [Saint-Laurent](street) dans le quartier [Centre-Ville](quartier)
  - slot{"quartier": "Centre-Ville"}
  - slot{"street": "Saint-Laurent"}
  - action_charging_point_place

## one street only - only a charging station nearby: bornes sur la rue Berlioz
* ask_charging_point_place: bornes sur la rue [Berlioz](street)
  - slot{"street":"Berlioz"}
  - action_charging_point_place
  - slot{"found_many_charging_points": null}
  - slot{"found_some_charging_points": null}
  - slot{"found_charging_points": ["1780 | BHR | VER | 201 Berlioz : La Station"]}
  - slot{"city": "Montréal"}
  - slot{"quartier": "Ile-des-soeurs"}
  - slot{"metro": null}
  - action_present_charging_parks
  - utter_prompt_send_charging_parks
 * affirm: oui
  - action_send_charging_parks

## one street + quartier - only a charging station nearby: bornes sur la rue Berlioz dans le quartier Ile-des-soeurs
* ask_charging_point_place: bornes sur la rue [Berlioz](street) dans le quartier [Ile-des-soeurs](quartier)
  - slot{"street":"Berlioz"}
  - slot{"quartier":"Ile-des-soeurs"}
  - action_charging_point_place
  - slot{"found_many_charging_points": null}
  - slot{"found_some_charging_points": null}
  - slot{"found_charging_points": ["1780 | BHR | VER | 201 Berlioz : La Station"]}
  - slot{"city": "Montréal"}
  - slot{"quartier": "Ile-des-soeurs"}
  - slot{"metro": null}
  - action_present_charging_parks
  - utter_prompt_send_charging_parks
 * deny: non
  - utter_ok_no_problem

## two streets intersection - only a charging station nearby
* ask_charging_point_place: bornes au coin du rue [Berlioz](street) et boulevard [Ile des Soeurs](street)
  - slot{"quartier": ["Berlioz", "Ile des Soeurs"]}
  - action_charging_point_place
  - slot{"found_many_charging_points": null}
  - slot{"found_some_charging_points": null}
  - slot{"found_charging_points": ["1780 | BHR | VER | 201 Berlioz : La Station"]}
  - slot{"city": "Montréal"}
  - slot{"quartier": "Ile-des-soeurs"}
  - slot{"metro": null}
  - action_present_charging_parks
  - utter_prompt_send_charging_parks
 * deny: non
  - utter_ok_no_problem

