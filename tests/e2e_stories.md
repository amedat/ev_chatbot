## ----- CORRECT ENTITIES SPELLING -----

## city
* ask_charging_point_place: combien de bornes de recharge à [Saguenay](city)
  - action_charging_point_place

## metro
* ask_charging_point_place: bornes près du métro [Laurier](metro)
  - action_charging_point_place

## quartier
* ask_charging_point_place: bornes dans le quartier [Rosemont](quartier)
  - action_charging_point_place

## ----- SMALL ENTITIES MISPELLING -----

## city
* ask_charging_point_place: Combien de place pour recharger à [Saint Felcien](city:Saint-Félicien)
  - action_charging_point_place

## metro
* ask_charging_point_place: Est-ce qu'il y a des bornes proche du métro [st henry](metro:Place-Saint-Henri)
  - action_charging_point_place

## quartier
* ask_charging_point_place: bornes dans le quartier [Iles des soeur](quartier:Ile-des-soeurs)
  - action_charging_point_place

## ----- METRO WITHOUT ACCENT (NORMALIZATION.PY MODULE) -----

## metro
* ask_charging_point_place: Est-ce qu'il y a des bornes pres du metro [st henry](metro:Place-Saint-Henri)
  - action_charging_point_place
