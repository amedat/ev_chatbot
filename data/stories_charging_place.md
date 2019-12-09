## happy path - starting with city
* request_charging_place{"city": "Montréal"} OR inform{"city": "Montréal"}
    - charging_place_form
    - form{"name": "charging_place_form"}
    - form{"name": null}
    - action_present_charging_parks
    - utter_prompt_send_charging_parks
* affirm
    - action_send_charging_parks

## happy path - starting with quartier
* request_charging_place{"quartier": "Rosemont"} OR inform{"quartier": "Rosemont"}
    - charging_place_form
    - form{"name": "charging_place_form"}
    - form{"name": null}
    - action_present_charging_parks
    - utter_prompt_send_charging_parks
* affirm
    - action_send_charging_parks

## happy path - starting with one street
* request_charging_place{"street": "saint-laurent"} OR inform{"street": "saint-laurent"}
    - charging_place_form
    - form{"name": "charging_place_form"}
    - form{"name": null}
    - action_present_charging_parks
    - utter_prompt_send_charging_parks
* deny
    - utter_ok_no_problem

## happy path - starting with two streets
* request_charging_place{"street": "saint-laurent", "street": "saint-denis"} OR inform{"street": "saint-laurent", "street": "saint-denis"}
    - charging_place_form
    - form{"name": "charging_place_form"}
    - form{"name": null}
    - action_present_charging_parks
    - utter_prompt_send_charging_parks
* deny
    - utter_ok_no_problem

## happy path - starting with a metro station
* request_charging_place{"metro": "McGill"} OR inform{"metro": "McGill"}
    - charging_place_form
    - form{"name": "charging_place_form"}
    - form{"name": null}
    - action_present_charging_parks
    - utter_prompt_send_charging_parks
* deny
    - utter_ok_no_problem

## happy path - starting without any entity
* request_charging_place
    - charging_place_form
    - form{"name": "charging_place_form"}
    - form{"name": null}
    - action_present_charging_parks
    - utter_prompt_send_charging_parks
* deny
    - utter_ok_no_problem

## happy path - starting with a greeting
* greet
    - utter_greet
* request_charging_place OR inform{"city": "Montréal"}
    - charging_place_form
    - form{"name": "charging_place_form"}
    - form{"name": null}
    - action_present_charging_parks
    - utter_prompt_send_charging_parks
* affirm
    - action_send_charging_parks
