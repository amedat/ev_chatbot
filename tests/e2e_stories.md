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
* ask_charging_point_place: bornes à [rosemont](quartier:Rosemont) 
  - action_charging_point_place

## quartier
* ask_charging_point_place: bornes dans [rosemont](quartier:Rosemont) 
  - action_charging_point_place

## ----- USER RECTIFY ENTITY -----

## city rectify to metro
* ask_charging_point_place: combien de bornes de recharge à [Sherbrooke](city)?
  - action_charging_point_place
* inform_rectify_metro_not_city: non, pas la ville de sherbrooke, la station de métro
  - action_rectify_metro_not_city
  - action_charging_point_place

## metro rectify to city
* ask_charging_point_place: bornes au metro [Sherbrooke](metro)
  - action_charging_point_place
* inform_rectify_city_not_metro: je parle de la ville pas de la station 
  - action_rectify_city_not_metro
  - action_charging_point_place 

## quartier rectify to metro
* ask_charging_point_place: combien de place pour recharger dans l'arrondissement [Rosemont](quartier) 
  - slot{"quartier": "Rosemont"}
  - action_charging_point_place
* inform_rectify_metro_not_quartier: non, le metro rosemont pas le quartier
  - slot{"metro": "Rosemont"}
  - action_rectify_metro_not_quartier
  - action_charging_point_place 

## metro rectify to quartier
* ask_charging_point_place: combien de bornes proche du metro [cote des neiges](metro:Côte-des-Neiges)
  - slot{"metro": "Côte-des-Neiges"}
  - action_charging_point_place
* inform_rectify_quartier_not_metro: pas le metro, le quartier
  - action_rectify_quartier_not_metro
  - slot{"quartier": "Côte-des-Neiges"}
  - action_charging_point_place 
