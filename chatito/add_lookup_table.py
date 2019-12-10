import sys

"""
Add a lookup table entry to rasa_dataset_training.json
"""


def parse_command_line():
    argv = sys.argv

    # defaults
    lookup_name = "quartier"
    lookup_data_file = "data/lookup_table_quartier.csv"
    training_dataset_json_file = "output/rasa_dataset_training.json"

    out_files = [lookup_name, lookup_data_file, training_dataset_json_file]

    # read in command line args
    if len(argv) > 1:
        for i, filename in enumerate(argv):
            # ignore the script name
            if i == 0:
                continue
            out_files[i - 1] = filename

    return tuple(out_files)


if __name__ == "__main__":

    lookup_name, lookup_data_file, training_dataset_json_file = parse_command_line()

    # load dataset json
    with open(training_dataset_json_file, encoding='utf-8') as f:
        text = f.readlines()

    # add "lookup_tables": [ { "name": "metro", "elements": "data/metro.txt" } ]
    first = False
    if 'lookup_tables' not in text[0]:
        # add empty list
        text[0] = text[0].replace('"rasa_nlu_data":{', '"rasa_nlu_data":{"lookup_tables": [],', 1)
        first = True

    # add the lookup table element at the end of the list
    if "lookup_tables" in text[0]:
        text[0] = text[0].replace('],', f'{"{" if first else ", {"}' + f' "name": "{lookup_name}", "elements": "{lookup_data_file}"' + '}],', 1)

    # check for success replace
    if lookup_data_file in text[0]:
        # save dataset json
        with open(training_dataset_json_file, 'w', encoding='utf-8') as text_file:
            for t in text:
                text_file.write(t)
    else:
        sys.exit(-1)
