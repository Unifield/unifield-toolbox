# -*- encoding: utf-8 -*-
import csv

inf = 'nomin.csv'
out = 'nomout.csv'
fo = open(out, 'w')

reader = csv.reader(open(inf, "rb"),delimiter=";",quotechar='"')
writer = csv.writer(open(out, "w"), delimiter=";",quotechar='"')
i=0
writer.writerow(['code','name','type','parent_id.complete_name'])
seen = {}
for row in reader:
    if i == 0:
        i += 1
        continue
    parent = []
    for j in range(1, len(row), 2):
        joinp = '/'.join(parent)
        if (row[j], joinp) not in seen:
            writer.writerow([row[j-1], row[j], 'mandatory',joinp])
            seen[(row[j], joinp)] = True
        parent.append(row[j])
