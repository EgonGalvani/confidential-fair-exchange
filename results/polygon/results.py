import json
import csv 

# 0x71B4938f4Bb1Eb764Fc9ac6abdf54cBCC72Bd360

f = open("./methods.json", "r")
methods = json.loads(f.read())
f.close() 

with open('employee_birthday.txt', mode='r') as csv_file:
  csv_reader = csv.DictReader(csv_file)
  line_count = 0
  for row in csv_reader:
    if line_count == 0:
      print(f'Column names are {", ".join(row)}')
      line_count += 1
    print(f'\t{row["name"]} works in the {row["department"]} department, and was born in {row["birthday month"]}.')
    line_count += 1
  print(f'Processed {line_count} lines.')