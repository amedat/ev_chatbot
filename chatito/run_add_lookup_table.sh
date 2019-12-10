#!/usr/bin/env bash

# set current working directory to the directory of the script
cd "$(dirname "$0")"

# read slot's list, remove some and save filtered list and add the "lookup" element to rasa_dataset_training.json

# QUARTIER
if [ -f slots/lookup_table_quartier.txt ]; then
    cp -v ./slots/lookup_table_quartier.txt ../data/
    if python add_lookup_table.py quartier data/lookup_table_quartier.txt output/rasa_dataset_training.json; then
        echo "<quartier> lookup table added"
    else
        echo "ERROR ADDING <QUARTIER> LOOKUP TABLE -- EXIT"
        exit -1
    fi
else
    echo "<quartier> no lookup table"
fi

# METRO
if [ -f slots/lookup_table_metro.txt ]; then
    cp -v ./slots/lookup_table_metro.txt ../data/
    if python add_lookup_table.py metro data/lookup_table_metro.txt output/rasa_dataset_training.json; then
        echo "<metro> lookup table added"
    else
        echo "ERROR ADDING <METRO> LOOKUP TABLE -- EXIT"
        exit -1
    fi
else
    echo "<metro> no lookup table"
fi

# CITY
if [ -f slots/lookup_table_city.txt ]; then
    cp -v ./slots/lookup_table_city.txt ../data/
    if python add_lookup_table.py city data/lookup_table_city.txt output/rasa_dataset_training.json; then
        echo "<city> lookup table added"
    else
        echo "ERROR ADDING <CITY> LOOKUP TABLE -- EXIT"
        exit -1
    fi
else
    echo "<city> no lookup table"
fi

# STREET
if [ -f slots/lookup_table_street.txt ]; then
    cp -v ./slots/lookup_table_street.txt ../data/
    if python add_lookup_table.py street data/lookup_table_street.txt output/rasa_dataset_training.json; then
        echo "<street> lookup table added"
    else
        echo "ERROR ADDING <STREET> LOOKUP TABLE -- EXIT"
        exit -1
    fi
else
    echo "<street> no lookup table"
fi
