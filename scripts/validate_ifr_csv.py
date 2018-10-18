#!/usr/bin/python3

import csv

file1 = str('/Users/ewagner/Downloads/' + str(input("File name of csv created by data team: ")))
file2 = str('/Users/ewagner/Downloads/' + str(input("File name of IFR csv exported from UI: ")))


with open(file1, 'r') as csv1, open(file2, 'r') as csv2:
    data_provided = csv1.readlines()
    ifr_export = csv2.readlines()

count = 0

for line in ifr_export:
    if line not in data_provided:
        print(line)
        count += 1

print('\n------------------------------- \n --------------------------------------\n')

for line in data_provided:
    if line not in ifr_export:
        print(line)
        count += 1


print("Total lines found: " + str(count))