import sys
import re

import parse_lib as pl


def add_attribute_slugs(all_modules):
    for module in all_modules:
        for attribute in module['data']:
            attribute['slug'] = pl.create_slug(attribute['tag'])


def add_parent_ids_to_table(all_modules):
    for module in all_modules:
        previous_attribute = {}
        attributes = module['data']
        for attribute in attributes:
            sequence_indicator = pl.sequence_indicator_from_cell(attribute['name'])
            if previous_attribute == {}:
                attribute['parent_slug'] = None
            else:
                attribute['parent_slug'] = record_parent_id_to_attribute(sequence_indicator,
                                                                         previous_attribute,
                                                                         attributes)
                if attribute['parent_slug'] is not None:
                    attribute['slug'] = attribute['parent_slug'] + ":" + attribute['slug']
            previous_attribute = set_new_previous_attribute(attribute)
        module['data'] = attributes


def set_new_previous_attribute(attribute):
    sequence_indicator = pl.sequence_indicator_from_cell(attribute['name'])
    previous_attribute = {
        'slug': attribute['slug'],
        'sequence_indicator': sequence_indicator,
        'parent_slug': attribute['parent_slug']
    }
    return previous_attribute


def record_parent_id_to_attribute(sequence_indicator, previous_attribute, attributes):
    if is_sub_attribute_of_previous(sequence_indicator, previous_attribute):
        return previous_attribute['slug']
    elif is_same_level_as_previous(sequence_indicator, previous_attribute):
        return previous_attribute['parent_slug']
    else:
        return find_non_adjacent_parent(sequence_indicator, previous_attribute, attributes)


def find_non_adjacent_parent(sequence_indicator, previous_attribute, attributes):
    difference = reference_level_difference(sequence_indicator, previous_attribute)
    parent_slug = previous_attribute['parent_slug']
    for i in range(difference):
        if parent_slug is None:
            break
        for other_attr in attributes:
            if other_attr['slug'] == parent_slug:
                try:
                    parent_slug = other_attr['parent_slug']
                except KeyError:
                    parent_slug = None
                break
    return parent_slug


def is_sub_attribute_of_previous(sequence_indicator, previous_attribute):
    return len(sequence_indicator) > len(previous_attribute['sequence_indicator'])


def is_same_level_as_previous(sequence_indicator, previous_attribute):
    return len(sequence_indicator) == len(previous_attribute['sequence_indicator'])


def reference_level_difference(sequence_indicator, previous_attribute):
    return len(previous_attribute['sequence_indicator']) - len(sequence_indicator)


def is_part_of_sequence(attribute_name):
    return re.match('^(>+)', attribute_name) is not None


def clean_all_attribute_names(all_modules):
    for module in all_modules:
        for attribute in module['data']:
            stripped_name = attribute['name'].strip()
            attribute['name'] = clean_attribute_name(stripped_name)


def clean_attribute_name(name):
    preceding_space, *split = re.split('^(>+)', name)
    if split != []:
        return split[1].strip()
    else:
        return name


if __name__ == '__main__':
    modules_with_attributes = pl.read_json_to_dict(sys.argv[1])

    add_attribute_slugs(modules_with_attributes)
    add_parent_ids_to_table(modules_with_attributes)
    clean_all_attribute_names(modules_with_attributes)

    pl.write_pretty_json(sys.argv[2], modules_with_attributes)