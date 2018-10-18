import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import json
import pandas as pd
import os


slug = str(input("Enter organization name: "))
if ' ' in slug:
    slug = slug.replace(' ', '_')

key = str(input("Enter the 20 digit PagerDuty API key: "))
while not (len(key) != 20 or key.isalnum()):
    key = str(input("Format should be 20 characters, alphanumeric only.  Try again: "))


def build_headers():
    """
    Construct the standard request headers for all the requesting functions
    :return headers: Dict - request headers
    """
    global key
    headers = {
        'Accept': 'application/vnd.pagerduty+json;version=2',
        'Authorization': str('Token token=' + key),
    }

    return headers


def requests_retry_session():
    """Create a retry session to handle common errors and rate limits"""

    session = requests.Session()

    retry = Retry(
        total=10,
        read=5,
        connect=5,
        backoff_factor=10,
        status_forcelist=(403, 429, 500, 502, 504),
    )

    adapter = HTTPAdapter(max_retries=retry)
    # session.mount('http://', adapter)
    session.mount('https://', adapter)

    return session


def make_request(url, params):
    """
    Perform a single request with a single set of parameters
    :param url: str - The sub url of the API call
    :param params: Dict of parameters for the request
    :return: response_content - Raw content of the http response,
        more - Boolean value indicating whether there are more records to retrieve with subsequent requests
        limit - The maximum number of records retruned in the response
        offset - The offset value used with the request
    """
    response_content = []
    excluded_response_items = ['limit', 'offset', 'total', 'more']
    more = False

    response = requests_retry_session().get(url, headers=build_headers(), params=params)

    content = json.loads(response.text)
    limit = content['limit']
    offset = content['offset']
    if content['more']:
        more = True

    requested_item = [item for item in content.keys() if item not in excluded_response_items][0]

    for item in content[requested_item]:
        response_content.append(item)

    return response_content, more, limit, offset


def chain_requests(url):
    """
    Chain a series of requests together to retrieve data that is paginated
    :param url: str - The sub url of the API call
    :return: aggregated_response_content - A list of dictionaries containing the requested content
    """

    aggregated_response_content = []

    params = {
        'offset': 0,
        'limit': 100,
    }

    content, more, limit, offset = make_request(url, params)
    for item in content:
        aggregated_response_content.append(item)

    while more:
        offset += 100
        params.update({'offset': str(offset)})
        content, more, limit, offset = make_request(url, params)
        for item in content:
            aggregated_response_content.append(item)

    return aggregated_response_content


def make_dataframe(results):
    """
    Convert a list of dictionaries to a Pandas Dataframe
    :param results: List of dictionaries
    :return: dataframe - A Pandas Dataframe
    """
    dataframe = pd.DataFrame(results)
    return dataframe


def get_abilties():
    """Retrieve the PagerDuty abilities associated with the account"""
    abilities_req = requests.get('https://api.pagerduty.com/abilities', headers=build_headers(), params=None)
    content = json.loads(abilities_req.text)
    abilities = [ability for ability in content['abilities']]
    abilities_df = make_dataframe(abilities)
    return abilities_df


def test_ability(ability):
    """
    Test whether an organization has a particular ability
    :param ability: Str - The name of an ability
    :return: Boolean
    """
    test_result = False
    ability_test_req = requests.get(str('https://api.pagerduty.com/abilities/'+ability),
                                    headers=build_headers(), params=None)
    if ability_test_req.status_code == 204:
        test_result = True
    return test_result


def get_teams():
    """
    Retrieve all teams with complete details
    :return: Pandas Dataframe
    """
    teams = chain_requests(url='https://api.pagerduty.com/teams')
    df = make_dataframe(teams)
    teams_df = df[['name', 'id', 'summary', 'description', 'default_role', 'parent',
                   'type']].sort_values('name', ascending=True)
    return teams_df


def get_users():
    """
    Retrieve all users with complete details
    :return: Pandas Dataframe
    """
    users = chain_requests('https://api.pagerduty.com/users?include%5B%5D=contact_methods'
                           '&include%5B%5D=notification_rules&include%5B%5D=teams')
    df = make_dataframe(users)
    users_df = df[['name', 'id', 'email', 'role', 'job_title', 'summary', 'description', 'type', 'contact_methods',
                   'notification_rules', 'teams', 'time_zone']].sort_values('name', ascending=True)
    return users_df


def get_addons():
    """
    Retrieve all addons with complete details
    :return: Pandas Dataframe or False if no addons are returned
    """
    addons = chain_requests('https://api.pagerduty.com/addons')
    if len(addons) > 0:
        df = make_dataframe(addons)
        addons_df = df[['name', 'summary', 'type', 'src']].sort_values('name', ascending=True)
        return addons_df
    else:
        return False


def get_extensions():
    """
    Retrieve all extensions with complete details
    :return: Pandas Dataframe
    """
    extensions = chain_requests('https://api.pagerduty.com/extensions?include%5B%5D=extension_objects'
                                '&include%5B%5D=extension_schemas')
    df = make_dataframe(extensions)
    extensions_df = df[['name', 'id', 'summary', 'type', 'config', 'extension_schema', 'extension_objects',
                        'endpoint_url']].sort_values('name', ascending=True)
    return extensions_df


def get_priorities():
    """
    Retrieve all priority levels with complete details
    :return: Pandas Dataframe
    """
    priorities = chain_requests('https://api.pagerduty.com/priorities')
    df = make_dataframe(priorities)
    priorities_df = df[['name', 'id', 'summary', 'description', 'type', 'order',
                        'color']].sort_values('name', ascending=True)
    return priorities_df


def get_oncalls():
    """
    Retrieve all current on-call users with complete details
    :return: Pandas Dataframe
    """
    oncalls = chain_requests('https://api.pagerduty.com/oncalls?time_zone=UTC')
    df = make_dataframe(oncalls)
    oncalls_df = df[['escalation_policy', 'schedule', 'escalation_level', 'start', 'end',
                     'user']].sort_values('escalation_level', ascending=True)
    return oncalls_df


def get_schedules():
    """
    Retrieve all schedules with complete details
    :return: Pandas Dataframe
    """
    schedules = chain_requests('https://api.pagerduty.com/schedules')
    df = make_dataframe(schedules)
    schedules_df = df[['name', 'id', 'summary', 'description', 'type', 'escalation_policies', 'teams', 'time_zone',
                       'users']].sort_values('name', ascending=True)
    return schedules_df


def get_services():
    """
    Retrieve all services with complete details
    :return: Pandas Dataframe
    """
    services = chain_requests('https://api.pagerduty.com/services?time_zone=UTC&sort_by=name'
                              '&include%5B%5D=escalation_policies&include%5B%5D=teams&include%5B%5D=integrations')
    df = make_dataframe(services)
    services_df = df[['name', 'id', 'status', 'summary', 'description', 'type', 'created_at', 'integrations',
                      'alert_creation', 'alert_grouping', 'alert_grouping_timeout', 'acknowledgement_timeout',
                      'auto_resolve_timeout', 'addons', 'incident_urgency_rule', 'integrations', 'response_play',
                      'scheduled_actions', 'support_hours', 'escalation_policy',
                      'teams']].sort_values('name', ascending=True)
    return services_df


def get_vendors():
    """
    Retrieve all vendors with complete details
    :return: Pandas Dataframe
    """
    vendors = chain_requests('https://api.pagerduty.com/vendors')
    df = make_dataframe(vendors)
    vendors_df = df[['name', 'long_name', 'id', 'summary', 'description', 'type', 'website_url', 'generic_service_type',
                     'integration_guide_url', 'alert_creation_default', 'alert_creation_editable', 'connectable',
                     'is_pd_cef']].sort_values('name', ascending=True)
    return vendors_df


def get_download_path():
    """
    Get the full directory path for the user's downloads folder
    :return: Str - full directory path
    """
    if os.name == 'nt':
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            location = winreg.QueryValueEx(key, downloads_guid)[0]
        return location
    else:
        return os.path.join(os.path.expanduser('~'), 'Downloads/')


def export_to_xlsx(dataframes):
    """
    Export each dataframe into it's own sheet inside an Excel doc
    :return: Str - File path
    :type dataframes: List of Dataframes
    """
    global slug
    download_path = str(get_download_path())
    file_path = str(download_path + slug + '_all_details_pagerduty_export.xlsx')
    with open(file_path, 'a', encoding='utf8'):
        writer = pd.ExcelWriter(file_path)
        for key, value in dataframes.items():
            value.to_excel(writer,
                           sheet_name=str(key),
                           na_rep='None',
                           float_format=None,
                           columns=None,
                           header=True,
                           index=False,
                           index_label=None,
                           startrow=0,
                           startcol=0,
                           engine=None,
                           merge_cells=False,
                           encoding='utf8',
                           inf_rep='inf',
                           verbose=True,
                           freeze_panes=None)
        writer.save()
    print("All details exported to: " + file_path)
    return file_path


def format_users_df(users_df):
    """
    Consume the users dataframe and return a new dataframe formatted for export to .csv
    :param users_df: Dataframe
    :return formatted_users_df: Dataframe
    """
    users_list = []
    for index, row in users_df.iterrows():
        user_dict = {}
        name = row['name'].split()
        user_dict['lastName'] = str(name[-1])
        if len(name) > 2:
            space = ' '
            user_dict['firstName'] = str(space.join(name[:-1]))
        else:
            user_dict['firstName'] = name[0]

        email_name = (row['email'].split("@"))[0]
        user_dict['username'] = email_name.lower()

        user_dict['email'] = row['email']

        if len(row['contact_methods']) > 0:
            for method in row['contact_methods']:
                if 'phone_contact_method' in method.values():
                    num = method['address']
                    number = str(num[:3] + '-' + num[3:6] + '-' + num[6:10])
                    user_dict['phone'] = str(number)
        else:
            user_dict['phone'] = ''

        if len(row['teams']) > 0:
            for team in row['teams']:
                teams_list = [str(team['summary'] + ":member")]
                team_string = ",".join(teams_list)
                user_dict['teams'] = str(team_string)
        else:
            user_dict['teams'] = ''

        if row['role'] == 'admin':
            user_dict['orgRole'] = 'admin'
        if row['role'] == 'owner':
            user_dict['orgRole'] = 'admin'
        else:
            user_dict['orgRole'] = 'member'

        users_list.append(user_dict)

    df = make_dataframe(users_list)
    formatted_users_df = df[['username', 'email', 'firstName', 'lastName', 'phone', 'teams', 'orgRole']]

    return formatted_users_df


def export_users_to_csv(formatted_users_df):
    """
    Export user deatails from formatted dataframe to a .csv file for uploading to VictorOps
    :param formatted_users_df: Dataframe of users with details
    :return filepath: Str Directory path of exported .csv file
    """
    global slug
    download_path = str(get_download_path())
    file_path = str(download_path + slug + '_formatted_pagerduty_user_export.csv')
    with open(file_path, 'a', encoding='utf8'):
        formatted_users_df.to_csv(file_path,
                                  sep=',',
                                  na_rep='',
                                  float_format=None,
                                  columns=None,
                                  header=True,
                                  index=False,
                                  index_label=None,
                                  mode='w',
                                  encoding=None,
                                  compression=None,
                                  quoting=None,
                                  quotechar='"',
                                  line_terminator='\n',
                                  chunksize=None,
                                  tupleize_cols=None,
                                  date_format=None,
                                  doublequote=True,
                                  escapechar=None,
                                  decimal='.'
                                  )

    print("User details exported to: " + file_path)
    return file_path


def main():
    """
    Build dataframes for the results of each API call and export a .xlsx doc af all details, and a
    .csv file formatted for uploading users into VictorOps
    :return nothing:
    """

    print("Fetching PagerDuty details")
    all_dataframes = {}

    abilities = get_abilties()
    all_dataframes['Abilities'] = abilities

    users = get_users()
    all_dataframes['Users'] = users

    if test_ability('teams'):
        teams = get_teams()
        all_dataframes['Teams'] = teams

    addons = get_addons()
    if addons:
        all_dataframes['Add-ons'] = addons

    extensions = get_extensions()
    if len(extensions) > 0:
        all_dataframes['Extensions'] = extensions

    priorities = get_priorities()
    if len(priorities) > 0:
        all_dataframes['Priorities'] = priorities

    oncalls = get_oncalls()
    if len(oncalls) > 0:
        all_dataframes['On Calls'] = oncalls

    schedules = get_schedules()
    if len(schedules) > 0:
        all_dataframes['Schedules'] = schedules

    services = get_services()
    if len(services) > 0:
        all_dataframes['Services'] = services

    vendors = get_vendors()
    if len(vendors) > 0:
        all_dataframes['Vendors'] = vendors

    export_to_xlsx(all_dataframes)
    export_users_to_csv(format_users_df(users))


if __name__ == '__main__':
    main()
