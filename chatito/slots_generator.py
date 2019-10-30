import random

import os.path
import pandas as pd


slots = [
    {
        "name": 'metro',
        "max": None,
        "function_list": [
            "dash_space",
            "space_dash",
        ],
    },
    {
        "name": 'city',
        "max" : 250,
        "function_list": [
            "dash_space",
        ],
    },
]


def dash_space(str):
    """ replace dash by space """
    return str.replace('-', ' ')


def space_dash(str):
    """ replace space by dash """
    return str.replace(' ', '-')


def get_slot_filename(slot_name):
    return f"./slots/{slot_name}.csv"


def get_list_for_slot(slot_name):
    filename = get_slot_filename(slot_name)

    name_list = None
    if os.path.isfile(filename):
        df = pd.read_csv(filename, sep=',', header=None)
        name_list = list(df[0])

    return name_list


def process_slot(slot_name, max_entry, function_list):
    """
    Load the list of names contains in file /slots/{slot_name}.csv and
    return a "chatito file type" string. Here an example for slot_name = 'city':
        @[city]
            ~[Montréal]
            ~[Québec]
            ~[Laval]
    """
    slot_chatito_str_list = []
    slot_chatito_str_list.append(f"@[{slot_name}]")

    name_list = get_list_for_slot(slot_name)
    if name_list:
        random.shuffle(name_list)

        for name in name_list:
            if max_entry and len(slot_chatito_str_list) > max_entry:
                break

            slot_chatito_str_list.append(f"    ~[{name}]")

            if function_list:
                for fnc in function_list:
                    new_name = eval(f'{fnc}("{name}")')
                    if new_name != name:
                        slot_chatito_str_list.append(f"    ~[{new_name}]")
    else:
        slot_chatito_str_list = None

    return '\n'.join(slot_chatito_str_list) if slot_chatito_str_list else None


if __name__ == "__main__":
    all_slots_chatito_str = ""

    for slot in slots:
        print(f"Processing slot <{slot['name']}>")
        slot_chatito_str = process_slot(slot['name'], slot['max'], slot['function_list'])

        if slot_chatito_str:
            print(slot_chatito_str)

            # append string
            all_slots_chatito_str += slot_chatito_str + '\n\n'
        else:
            print(f"  ** Problem processing slot {slot['name']} from file {get_slot_filename(slot['name'])} **")

    # save all_slots_chatito_str to slots.chatito file
    with open('./input/slots.chatito', 'w', encoding='utf-8') as text_file:
        text_file.write(all_slots_chatito_str)
