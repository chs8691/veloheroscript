from utility import log, exit_on_rc_error, exit_on_error, exit_on_login_error
from pathlib import Path as pathlib_Path
from os import path
import requests as requests
import re
import json
from lxml import html


# Filled with ID for SSO login
sso_id = None

# Constant with file name in the users directory
rc_file = ".veloherorc"

# User-Agent string
my_user_agent = "veloheroup/1.0"


def velohero_process_upload(args):
    log("execute_vh_upload", "start")

    velohero_check_sso_login()

    workout_id = -1
    if args.file:
        workout_id = velohero_do_upload(args.file)
        velohero_do_update(workout_id, args, None)

    print("Uploaded to Velohero. New workout ID: %s" % workout_id)

    log("execute_vh_upload", "end")


def velohero_process_update(args):
    log("execute_vh_update", "start")

    velohero_check_sso_login()

    velohero_do_update(args.workout_id, args, None)

    print("Done.")

    log("execute_vh_update", "end")


def velohero_process_show(args):
    log("execute_vh_show", "start")

    velohero_check_sso_login()

    tree = load_workout_data(args.workout_id)
    # log("response", str(r.text))

    print_simple_input(tree, 'workout_date')
    print_simple_input(tree, 'workout_start_time')
    print_simple_input(tree, 'workout_dist_km')
    print_simple_input(tree, 'workout_asc_m')
    print_simple_input(tree, 'workout_dur_time')
    print_simple_input(tree, 'workout_dsc_m')
    print_simple_input(tree, 'workout_alt_min_m')
    print_simple_input(tree, 'workout_alt_max_m')
    print_simple_input(tree, 'workout_spd_avg_kph')
    print_simple_input(tree, 'workout_spd_max_kph')
    print_simple_input(tree, 'workout_hr_avg_bpm')
    print_simple_input(tree, 'workout_hr_max_bpm')
    print_textarea(tree, 'workout_comment')

    print("")
    print_select_values(tree, "sport_id")
    print("")
    print_select_values(tree, "type_id")
    print("")
    print_select_values(tree, "route_id")
    print("")
    print_select_values(tree, "equipment_ids")

    log("execute_vh_show", "start")


def load_workout_data(workload_id):
    """
    Requests the workload for the given ID. Precondition: SSO established
    Returns HTML tree
    """
    log("load_workload_data", "start")

    # just for for testing
    # return html.parse(open('workout.html', 'rt')).getroot()

    url = "https://app.velohero.com/workouts/edit/{}".format(workload_id)
    log("url", str(url))
    r = requests.post(url,
                      headers={
                          'user-agent': my_user_agent,
                      },
                      data={
                          'sso': sso_id,
                      })

    if r.status_code != 200:
        exit_on_rc_error("HTTP error {}. Status code".format(url), r.status_code)

    return html.fromstring(r.text)


def get_select_values_value(tree, name):
    """
    Returns only the value of a select field
    :return: Value or empty string
    """
    values = [v for v in get_select_values(tree, name)['values'] if v['selected']]

    if len(values) == 0:
        return ""
    else:
        return values[0]['id']


def get_select_values_values(tree, name):
    """
    Returns only the values of a select field
    :return: List with values, list can be empty
    """
    values = [v for v in get_select_values(tree, name)['values'] if v['selected']]

    ret = []
    for value in values:
        ret.append(value['id'])

    return ret


def get_select_values(tree, name):
    """
    Returns dictionary with id, value, description, for instance
            dict=(id='sport_id',
                  description='Sportart',
                  values=[(id=1, description='Radsport', data-subtext=None, selectecd=True),
                        id=6, description='Mountainbike', data-subtext=None, selected=False),
                        ...
                      ]),

    """
    ret = None

    try:

        element = tree.xpath("//select[@id='%s']" % name)[0]

        label_elements = tree.xpath("//label[@for='%s']" % name)

        # Proper HTML: label has a for attribute
        if len(label_elements) > 0:
            label = label_elements[0].text

        # Just for 'Material' / equipment_ids:
        else:
            label = element.getparent().getparent()[0].text

        ret = dict(id=element.name,
                   description=label,
                   values=[])

        # exclude empty item
        for option in [o for o in element if len(o.get('value')) > 0]:
            if option.get('selected'):
                # log('selected', "True")
                selected = True
            else:
                # log('selected', "False")
                selected = False
            if option.get('data-subtext'):
                data_subtext = option.get('data-subtext')
            else:
                data_subtext = None

            ret['values'].append(dict(id=option.get('value'),
                                      description=option.text,
                                      data_subtext=data_subtext,
                                      selected=selected))

    except IndexError as e:
        exit_on_rc_error("Element '%s' error" % name, e)

    return ret


def get_text_area(tree, name):
    """
    Returns dictionary with id, value, description
    """
    log('get_text_area', str(name))
    try:

        label = tree.xpath("//label[@for='%s']" % name)[0].text
        # label inside formatting element, e.g. <span>
        if label is None:
            label = tree.xpath("//label[@for='%s']" % name)[0][0].text

        # log('label', label)
        # log('textarea', str(tree.xpath("//textarea[@id='%s']" % name)[0].value))

        element = tree.xpath("//textarea[@id='%s']" % name)[0]

        # log('element.name', element.name)
        # log('element.value', element.value)

        ret = dict(id=element.name,
                   value=element.value,
                   description=label,
                   )
        # log("get_simple_input ret=", ret)
        return ret

    except IndexError:
        exit_on_rc_error("Element not found", name)


def get_simple_input(tree, name):
    """
    Returns dictionary with id, value, description
    """
    # log('get_simple_input', str(name))
    try:

        label = tree.xpath("//label[@for='%s']" % name)[0].text
        # label inside formatting element, e.g. <span>
        if label is None:
            label = tree.xpath("//label[@for='%s']" % name)[0][0].text

        # log('label', label)

        element = tree.xpath("//input[@id='%s']" % name)[0]

        # log('element', element)

        ret = dict(id=element.name,
                   value=element.value,
                   description=label,
                   )
        # log("get_simple_input ret=", ret)
        return ret

    except IndexError:
        exit_on_rc_error("Element not found", name)


def get_selected_id(select_dict, value):
    """
    Exits script, if value is invalid. Exits in error case
    :param select_dict: Dictionary which describes the data
    :param value: id or description
    :return: id or, in initial case, empty string
    """
    if value.isdigit():
        key = 'id'
        log('res is digit', value)
    else:
        key = 'description'

    try:
        res_list = [v for v in select_dict['values'] if value.lower() in v[key].lower()]
        if len(res_list) > 1:
            print("ERROR")
            print("%s '%s' is non-unique, found %s canidates:" % (select_dict['description'], value, len(res_list)))
            for res in res_list:
                print("  * %s (%s)" % (res['description'], res['id']))
            exit_on_rc_error("Please set a unique value for ", select_dict['description'])

        res = res_list[0]['id']
        log("Found for %s" % (select_dict['description']), res_list[0])
        return res
    except IndexError:
        exit_on_rc_error("Unknown value", value)


def get_selected_ids(select_dict, values=None, value_list=None):
    """
    Exits script, if value is invalid
    :param select_dict: Dictionary which describes the data
    :param values: String with list with ids or descriptions, e.g. "", "123, 345, 56756"
    :param value_list: Alternative to values, the data directly as list
    :return: List with ids or, in initial case, empty list
    """

    ret = []

    if values is not None:
        # Empty list or empty string
        if len(values) == 0:
            return ret

        value_list = values.split(", ")

    for value in value_list:
        res = get_selected_id(select_dict, value)
        ret.append(res)

    return ret


def velohero_do_upload(file_name):
    """
    File must exist and of a valid route
    Returns workout ID or False
    """
    log("upload file", file_name)

    with open(file_name, "rb") as file:
        # content = file.read()
        # log("content", content)
        r = requests.post("https://app.velohero.com/upload/file",
                          headers={
                              'user-agent': my_user_agent,
                          },
                          files={
                              'file': (file_name, file.read()),
                          },
                          data={
                              'sso': sso_id,
                              'view': "json",
                          })
        # log("request.headers", r.request.headers)
        # log("headers", r.headers)
        log("text", r.text)

        # text = json.loads(r.text)
        # log("id", text["id"])

        # 200 Created
        if r.status_code == 200:
            log("Upload successful", r.status_code)
            log("Response", str(r))

            return json.loads(r.text)["id"]

        # 403 Forbidden
        if r.status_code == 403:
            exit_on_error("Login forbidden - {}: ".format(r.status_code))
            return False

        # Other error
        exit_on_error("HTTP error - {}: ".format(r.status_code))
        return False


def print_select_values(tree, name):
    data = get_select_values(tree, name)
    print("%s '%s':" % (data['id'], data['description']))

    for option in [o for o in data['values'] if o['id'] is not None]:

        # Only route_id can have a subtext with distance-value
        if not option['data_subtext'] is None:
            subtext = " / %s" % option['data_subtext']
        else:
            subtext = ""

        if option['selected'] is True:
            print(">>> %s%s (%s) <<<-------- SELECTED" % (option['description'], subtext, option['id']))
        else:
            print("    %s%s (%s)" % (option['description'], subtext, option['id']))


def print_simple_input(tree, name):
    # log('print_simple_input', str(name))
    data = get_simple_input(tree, name)

    print("%s '%s' = %s" % (data['id'], data['description'], data['value']))


def print_textarea(tree, name):
    log('print_text_area', str(name))
    data = get_text_area(tree, name)

    print("%s '%s' = %s" % (data['id'], data['description'], data['value']))


def map_sport_id(sport_id_dict, activity):
    """
    From a set activity type to a velohero sport
    :return: sport, or, if unknown, None
    """
    result = []

    log("activity", activity)

    if activity == 'run':
        result = [v for v in sport_id_dict['values'] if v['description'] in ('Running', 'Laufsport')]

    elif activity == 'mtb':
        result = [v for v in sport_id_dict['values'] if v['description'] in ('Mountain Bike', 'Mountainbike')]

    elif activity == 'roadbike':
        result = [v for v in sport_id_dict['values'] if v['description'] in ('Cycling', 'Radsport')]

    elif activity == 'fitness':
        result = [v for v in sport_id_dict['values'] if v['description'] in ('Fitness', 'Fitness')]

    elif activity == 'hiking':
        result = [v for v in sport_id_dict['values'] if v['description'] in ('Hiking', 'Wandern')]

    if len(result) == 0 or 'id' not in result[0]:
        print("Warn: Activity type '%s' could not map to Velohero's sport ID !" % activity)
        return None

    return result[0]['id']



def velohero_do_update(workout_id, args, load):
    """
    Update existing workout
    :param workout_id Workout ID to update
    :param args Args from the vh_update command or, if load set, None.
    :param load Load with attributes to update, or if args set, None.
    """
    log("do_set", "start")

    velohero_check_sso_login()

    tree = load_workout_data(workout_id)

    # Init all field with old data
    workout_date = get_simple_input(tree, 'workout_date')['value']
    workout_start_time = get_simple_input(tree, 'workout_start_time')['value']
    workout_dist_km = get_simple_input(tree, 'workout_dist_km')['value']
    workout_asc_m = get_simple_input(tree, 'workout_asc_m')['value']
    workout_dur_time = get_simple_input(tree, 'workout_dur_time')['value']
    sport_id = get_select_values_value(tree, 'sport_id')
    type_id = get_select_values_value(tree, 'type_id')
    route_id = get_select_values_value(tree, 'route_id')
    workout_dsc_m = get_simple_input(tree, 'workout_dsc_m')['value']
    workout_alt_min_m = get_simple_input(tree, 'workout_alt_min_m')['value']
    workout_alt_max_m = get_simple_input(tree, 'workout_alt_max_m')['value']
    workout_spd_avg_kph = get_simple_input(tree, 'workout_spd_avg_kph')['value']
    workout_spd_max_kph = get_simple_input(tree, 'workout_spd_max_kph')['value']
    workout_hr_avg_bpm = get_simple_input(tree, 'workout_hr_avg_bpm')['value']
    workout_hr_max_bpm = get_simple_input(tree, 'workout_hr_max_bpm')['value']
    workout_comment = get_text_area(tree, 'workout_comment')['value']
    equipment_ids = get_select_values_values(tree, 'equipment_ids')

    log('Actual data', ":")
    log('workout_date', workout_date)
    log('workout_start_time', workout_start_time)
    log('workout_dist_km', workout_dist_km)
    log('workout_asc_m', workout_asc_m)
    log('workout_dur_time', workout_dur_time)
    log('sport_id', sport_id)
    log('type_id', type_id)
    log('route_id', route_id)
    log('workout_dsc_m', workout_dsc_m)
    log('workout_alt_min_m', workout_alt_min_m)
    log('workout_alt_max_m', workout_alt_max_m)
    log('workout_spd_avg_kph', workout_spd_avg_kph)
    log('workout_spd_max_kph', workout_spd_max_kph)
    log('workout_hr_avg_bpm', workout_hr_avg_bpm)
    log('workout_hr_max_bpm', workout_hr_max_bpm)
    log('equipment_ids', equipment_ids)
    log('workout_comment', workout_comment)

    # Options
    sport_id_dict = get_select_values(tree, 'sport_id')
    type_id_dict = get_select_values(tree, 'type_id')
    route_id_dict = get_select_values(tree, 'route_id')
    equipment_ids_dict = get_select_values(tree, 'equipment_ids')

    log('sport_id_dict', sport_id_dict)
    log('type_id_dict', type_id_dict)
    log('route_id_dict', route_id_dict)
    log('equipment_ids_dict', equipment_ids_dict)

    # Update fields by vh-update
    if args is not None:
        if args.workout_date:
            workout_date = args.workout_date
        if args.workout_start_time:
            workout_start_time = args.workout_start_time
        if args.workout_dist_km:
            workout_dist_km = args.workout_dist_km
        if args.workout_asc_m:
            workout_asc_m = args.workout_asc_m
        if args.workout_dur_time:
            workout_dur_time = args.workout_dur_time
        if args.sport_id:
            sport_id = get_selected_id(sport_id_dict, args.sport_id)
        if args.type_id:
            type_id = get_selected_id(type_id_dict, args.type_id)
        if args.route_id:
            route_id = get_selected_id(route_id_dict, args.route_id)
        if args.workout_dsc_m:
            workout_dsc_m = args.workout_dsc_m
        if args.workout_alt_min_m:
            workout_alt_min_m = args.workout_alt_min_m
        if args.workout_alt_max_m:
            workout_alt_max_m = args.workout_alt_max_m
        if args.workout_spd_avg_kph:
            workout_spd_avg_kph = args.workout_spd_avg_kph
        if args.workout_spd_max_kph:
            workout_spd_max_kph = args.workout_spd_max_kph
        if args.workout_hr_avg_bpm:
            workout_hr_avg_bpm = args.workout_hr_avg_bpm
        if args.workout_hr_max_bpm:
            workout_hr_max_bpm = args.workout_hr_max_bpm
        if args.equipment_ids:
            equipment_ids = get_selected_ids(equipment_ids_dict, values=args.equipment_ids)
        if args.workout_comment:
            workout_comment = args.workout_comment

    # Update fields by command transfer
    elif load is not None:
        if load.new_activity_type:
            new_sport_id = map_sport_id(sport_id_dict, load.new_activity_type)
            if new_sport_id:
                sport_id = new_sport_id

        # log('load.training_type', load.training_type)
        if load.training_type is not None:
            if load.training_type == '':
                type_id = '0'
            else:
                type_id = get_selected_id(type_id_dict, load.training_type)

        # Check explicitly for 'not None', otherwise an empty list will be ignored
        if load.equipment_names is not None:
            equipment_ids = get_selected_ids(equipment_ids_dict, value_list=load.equipment_names)

        # Check explicitly for 'not None', otherwise an empty list will be ignored
        if load.route_name is not None:
            route_id = get_selected_id(route_id_dict, load.route_name)

        if load.comment is not None:
            workout_comment = load.comment

    log('New data', ":")
    log('workout_date', workout_date)
    log('workout_start_time', workout_start_time)
    log('workout_dist_km', workout_dist_km)
    log('workout_asc_m', workout_asc_m)
    log('workout_dur_time', workout_dur_time)
    log('sport_id', sport_id)
    log('type_id', type_id)
    log('route_id', route_id)
    log('workout_dsc_m', workout_dsc_m)
    log('workout_alt_min_m', workout_alt_min_m)
    log('workout_alt_max_m', workout_alt_max_m)
    log('workout_spd_avg_kph', workout_spd_avg_kph)
    log('workout_spd_max_kph', workout_spd_max_kph)
    log('workout_hr_avg_bpm', workout_hr_avg_bpm)
    log('workout_hr_max_bpm', workout_hr_max_bpm)
    log('equipment_ids', equipment_ids)
    log('workout_comment', workout_comment)

    url = "https://app.velohero.com/workouts/edit/{}".format(workout_id)
    log("url", str(url))

    # Must contains all workout fields
    r = requests.post(url,
                      headers={
                          'user-agent': my_user_agent,
                      },
                      data={
                          'sso': sso_id,
                          'submit': '1',
                          'workout_date': workout_date,
                          'workout_start_time': workout_start_time,
                          'workout_dist_km': workout_dist_km,
                          'workout_asc_m': workout_asc_m,
                          'workout_dur_time': workout_dur_time,
                          'sport_id': sport_id,
                          'type_id': type_id,
                          'route_id': route_id,
                          'workout_dsc_m': workout_dsc_m,
                          'workout_alt_min_m': workout_alt_min_m,
                          'workout_alt_max_m': workout_alt_max_m,
                          'workout_spd_avg_kph': workout_spd_avg_kph,
                          'workout_spd_max_kph': workout_spd_max_kph,
                          'workout_hr_avg_bpm': workout_hr_avg_bpm,
                          'workout_hr_max_bpm': workout_hr_max_bpm,
                          'workout_comment': workout_comment,
                          'equipment_ids': equipment_ids,
                          # 'equipment_ids': ['17481', '3793'],
                      })

    if r.status_code != 200:
        exit_on_rc_error("HTTP error for {}".format(url), r.status_code)

    # log("response", str(r.text))

    log("do_set", "done")


def velohero_check_sso_login():
    log("check_sso_login", "begin")
    global sso_id

    file_name = path.join(str(pathlib_Path.home()), rc_file)

    if not path.exists(file_name):
        exit_on_login_error("File not found", file_name)

    log("found file", file_name)
    with open(file_name) as file:
        for line in file:
            matcher = re.match('^VELOHERO_SSO_KEY\\s*=\\s*(\\S+)\\s*', line, re.I)
            if matcher:
                sso_id = matcher.group(1)
                break

        if sso_id is None:
            exit_on_rc_error("Missing key=value entry", file_name)

    log("sso_id", sso_id)

    r = requests.post("https://app.velohero.com/sso", data={'sso': sso_id})

    # 200 Created
    if r.status_code == 200:
        log("Authentification successful", r.status_code)
        return

    # 403 Forbidden
    if r.status_code == 403:
        exit_on_error("Login forbidden - {}: ".format(r.status_code))
        return
