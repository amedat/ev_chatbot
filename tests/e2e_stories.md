## ----- CORRECT ENTITIES SPELLING -----

## city
* ask_charging_point_place: combien de bornes de recharge à [Saguenay](city)?
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## metro
* ask_charging_point_place: bornes près du métro [Laurier](metro)
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## quartier
* ask_charging_point_place: bornes dans le quartier [Rosemont](quartier)?
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## ----- SMALL ENTITIES MISPELLING -----

## city
* ask_charging_point_place: Combien de place pour recharger à [Saint Felcien](city:Saint-Félicien)
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## metro
* ask_charging_point_place: Est-ce qu'il y a des bornes proche du métro [st henry](metro:Place-Saint-Henri) ?
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## quartier
* ask_charging_point_place: bornes dans le quartier [Iles des soeur](quartier:Ile-des-soeurs)
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## ----- METRO WITHOUT ACCENT (NORMALIZATION.PY MODULE) -----

## metro
* ask_charging_point_place: Est-ce qu'il y a des bornes pres du metro [st henry](metro:Place-Saint-Henri)
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## ----- STATION DISAMBIGUATION -----

## metro
* ask_charging_point_place: dans le bout de la station [du castelno](metro:De Castelnau) combien de endroit pour recharger 
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## metro
* ask_charging_point_place: où ce qu'y sont les station de recharge à proximité de [Saint Robert Bellarmin](city:Saint-Robert-Bellarmin) 
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## metro
* ask_charging_point_place: bornes à la station [rosemont](metro:Rosemont)? 
  - action_charging_point_place
  - slot{"found_charging_point": 5}
  
## ----- QUARTIER DISAMBIGUATION -----

## quartier
* ask_charging_point_place: bornes à [rosemont](quartier:Rosemont) 
  - action_charging_point_place
  - slot{"found_charging_point": 5}

## quartier
* ask_charging_point_place: bornes dans [rosemont](quartier:Rosemont) 
  - action_charging_point_place
  - slot{"found_charging_point": 5}

