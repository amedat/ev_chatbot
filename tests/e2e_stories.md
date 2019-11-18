## ----- CORRECT ENTITIES SPELLING -----

## city
* ask_charging_point_in_city: combien de bornes de recharge à [Saguenay](city)
  - action_charging_point_in_city

## metro
* ask_charging_point_near_metro: bornes près du métro [Laurier](metro)
  - action_charging_point_near_metro

## quartier
* ask_charging_point_in_quartier: bornes dans le quartier [Rosemont](quartier)
  - action_charging_point_in_quartier

## ----- SMALL ENTITIES MISPELLING -----

## city
* ask_charging_point_in_city: Combien de place pour recharger à [Saint Felcien](city:Saint-Félicien)
  - action_charging_point_in_city

## metro
* ask_charging_point_near_metro: Est-ce qu'il y a des bornes proche du métro [st henry](metro:Place-Saint-Henri)
  - action_charging_point_near_metro

## quartier
* ask_charging_point_in_quartier: bornes dans le quartier [Iles des soeur](quartier:Ile-des-soeurs)
  - action_charging_point_in_quartier

## ----- METRO WITHOUT ACCENT (NORMALIZATION.PY MODULE) -----

## metro
* ask_charging_point_near_metro: Est-ce qu'il y a des bornes pres du metro [st henry](metro:Place-Saint-Henri)
  - action_charging_point_near_metro
