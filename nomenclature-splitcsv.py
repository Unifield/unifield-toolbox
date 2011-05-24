# -*- encoding: utf-8 -*-
import csv

inf = 'nomin.csv'
out = 'nomout.csv'
fo = open(out, 'w')

reader = csv.reader(open(inf, "rb"),delimiter=";",quotechar='"')
writer = csv.writer(open(out, "w"), delimiter=";",quotechar='"')
i=0
writer.writerow(['code','name','type','parent_id.code'])
seen = {}
for row in reader:
    if i == 0:
        i += 1
        continue
    parent = ''
    for j in range(0, len(row), 2):
        if (row[j], parent) not in seen:
            writer.writerow([row[j], row[j+1], 'mandatory',parent])
            seen[(row[j], parent)] = True
        parent = row[j]
