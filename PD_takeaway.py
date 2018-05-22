# Export PD users to a .csv file formatted for uploading to VictorOps
# !/usr/bin/env python3

import datetime
import requests
import sys
import csv

users_final = []
user_count = 0
teams_final = []
team_count = 0
teams_ability = True

ORG_NAME = input("What is the name of the org?: ")
for name in range(3):
	while len(ORG_NAME) == 0:
		ORG_NAME = input("Must enter a name: ")

AUTH_TOKEN = input("Enter auth token from PagerDuty: ")

USERNAME_CONVENTION = int(input("\n  1 = first.last \n  2 = Match email address naming convention (for j.doe@company.com, username = \"j.doe\")\n\nChoose an option for user naming convention (1 or 2): "))
while USERNAME_CONVENTION < 1 or USERNAME_CONVENTION > 2:
	input("Must choose an option (1 or 2, then press enter): ")

csvfile1 = ORG_NAME + "-USERS.csv"
csvfile2 = ORG_NAME + "-TEAMS.csv"

BASE_URL1 = 'https://api.pagerduty.com/users?include%5B%5D=contact_methods&include%5B%5D=teams&include%5B%5D=notification_rules&total=true&more=true'
BASE_URL2 = 'https://api.pagerduty.com/teams?total=true&more-true'
BASE_URL3 = 'https://api.pagerduty.com/abilities'

HEADERS = {
	'Authorization': 'Token token={0}'.format(AUTH_TOKEN),
	'Content-type': 'application/json',
}

# -----------------------------------------------------------------------------------------------------
def test_API_abilities():
	"""Test whether this PD customer has the teams ability required to get a list of teams"""
	global teams_ability

	abilities_response = requests.get(
		format(BASE_URL3),
		headers=HEADERS
	)

	abilities = abilities_response.json()

	if 'teams' in abilities['abilities']:
		print("Teams ability confirmed")
	else:
		print("This organization does not have \"teams\" ability in PD, so no teams .csv will be generated")
		teams_ability = False
	return teams_ability


#------------------------------------------------------------------------------------------------------
def get_user_count():
	"""Get total user count form PD API"""
	global user_count

	print("\nGetting user count from PagerDuty...")

	count = requests.get(
		'{0}/users'.format(BASE_URL1),
		headers=HEADERS
	)

	user_count = count.json()['total']

	print("\nGetting user info for " + str(user_count) + " total users...")

	return user_count

#------------------------------------------------------------------------------------------------------
def get_users(offset):
	"""Get all the relevant user info from PD's API and build it into a list of dictionaries"""

	global user_count
	global users_final

	# Deal with the limit on results in the response
	params = {
		'offset': offset
	}
	# Get users response from PD's "List Users" API
	users_response = requests.get(
		'{0}/users'.format(BASE_URL1),
		headers=HEADERS,
		params=params
	)
	all_users = users_response.json()

	for user in all_users['users']:
	# Create dictionary to hold user details
		user_dict = {}
	# Add user's email address
		user_dict['email'] = str(user['email'])

	# Get user's name and reformat it for upload to VictorOps
		# Separate first and last names
		names = user['name'].split()
		# Add last name to user dictionary
		user_dict['lastName'] = str(names[-1])
		#Deal with more than two names
		if len(names) > 2:
			space = ' '
			user_dict['firstName'] = str(space.join(names[:-1]))
		else:
			user_dict['firstName'] = str(names[0])

		# Use user's name to derive username in VictorOps (format = first.last)

		if USERNAME_CONVENTION == 1:
			user_dict['username'] = (str(str(names[0])).lower() + '.' + (str(names[-1]))).lower()

		if USERNAME_CONVENTION == 2:
			email_name = (user['email'].split("@"))[0]
			user_dict['username'] = email_name.lower()

		# Get phone number and reformat for upload to VictorOps.  Use blank string if no phone number is present
		if len(user['contact_methods']) > 0:
			for method in user['contact_methods']:
				if 'phone_contact_method' in method.values():
					num = method['address']
					number = str(num[:3] + '-' + num[3:6] + '-' + num[6:10])
					user_dict['phone'] = str(number)
					break
				else:
					user_dict['phone'] = ''
		else:
			user_dict['phone'] = ''

		# Get teams for the user and reformat for uploading to VictorOps
		teams_list = []
		team_string = ''
		if len(user['teams']) > 0:
			for team in user['teams']:
				teams_list.append(str(team['summary'] + ":member"))
				team_string = ",".join(teams_list)
				user_dict['teams'] = str(team_string)
		else:
			user_dict['teams'] = ''

		# Translate role in PD to role in VictorOps
		if 'admin' in user.values():
			user_dict['orgRole'] = 'admin'
		if 'owner' in user.values():
			user_dict['orgRole'] = 'admin'
		else:
			user_dict['orgRole'] = 'member'

		users_final.append(user_dict)
	return users_final

# ------------------------------------------------------------------------------------------------------------------
def get_team_count():
	"""Get total user count form PD API"""
	global team_count

	print("\nGetting count of teams in PagerDuty...")

	count = requests.get(
		format(BASE_URL2),
		headers=HEADERS
	)

	team_count = count.json()['total']

	print("\nGetting info for " + str(team_count) + " total teams...")

	return team_count


# ------------------------------------------------------------------------------------------------------------------
def get_teams(offset):
	"""Extract a list of the teams configured in PD"""
	global teams
	global team_count

	# Get users response from PD's "List Users" API
	teams_response = requests.get(
		'{0}/users'.format(BASE_URL2),
		headers=HEADERS,
		params=params
	)

	all_teams = teams_response.json()
	for team in all_teams['teams']:
		for each in team:
			teams.append(str(team['name']))

	print(teams)
	return teams
# ------------------------------------------------------------------------------------------------------------------

def write_users_to_csv():
	"""Write the details of the formatted users_final dict to a csv file"""

	global csvfile1
	global users_final

	with open(csvfile1, 'w', encoding='utf-8') as output:
		w = csv.writer(output, lineterminator='\n')
		w.writerow(["username", "email", "firstName", "lastName", "phone", "teams", "orgRole"])
		for user in users_final:
			w.writerow([user['username']] + [user['email']] + [user['firstName']] + [user['lastName']] + [user['phone']] + [user['teams']] + [user['orgRole']])

	print("\n" + str(len(users_final)) + " users written to " + str(csvfile1))

# ------------------------------------------------------------------------------------------------------------------

def write_teams_to_csv():
	"""Write the details of the formatted users_final dict to a csv file"""

	global csvfile2
	global teams_final

	with open(csvfile2, 'w', encoding='utf-8') as output:
		w = csv.writer(output, lineterminator='\n')
		w.writerow(["team"])
		for team in teams_final:
			w.writerow(str(team))

	print("\n" + str(len(users_final)) + " users written to " + str(csvfile1))
# ------------------------------------------------------------------------------------------------------------------

def main(argv=None):
	if argv is None:
		argv = sys.argv

	test_API_abilities()

	get_user_count()

	# Chunks of 25 users at a time
	for offset in range(0, user_count):
		if offset % 25 == 0:
			get_users(offset)

	write_users_to_csv()

	if teams_ability == True:
		get_team_count()
		get_teams()
		write_teams_to_csv()

	print("Suck it PagerDuty!!")


if __name__ == '__main__':
	sys.exit(main())
