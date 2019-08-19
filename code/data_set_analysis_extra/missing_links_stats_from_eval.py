import sys
import re

valid = 0
invalid = 0
mag0 = 0
now_in_mag = 0

with open('missing_links_eval') as f:
    for line in f:
        if not re.search('^\d', line):
            # comments
            continue
        evl = line.strip().split(':')[-1].split('(')[0].strip()
        if len(evl) == 0:
            # not evalutated yet
            continue
        if evl[0] == 'y':
            valid += 1
        elif evl[0] == 'n':
            invalid += 1
        else:
            print('problem with line: "{}"'.format(line))
            sys.exit()
        if len(evl) == 2 and evl[1] == '0':
            mag0 += 1
        if len(evl) == 2 and evl[1] == '*':
            now_in_mag += 1

total = valid + invalid

print('--- unarXive only ---')
print()
print('total: {}'.format(total))
print()
print('general indicator of quality of "not in MAG" subset of links:')
print('  valid: {} ({:.2f})'.format(valid, valid/total))
print('  invalid: {} ({:.2f})'.format(invalid, invalid/total))
print()
print('indicators for "we have X, which is missing in MAG:"')
print('  valid missing Feb 2019: {} verified -> ~{:.2f}'.format(valid, (valid/total)*5964282))
print('  valid missing Aug 2019: {} verified -> ~{:.2f}'.format(valid-now_in_mag, ((valid-now_in_mag)/total)*5964282))
print()
print('misc')
print('  papers w/ 0 references in MAG: {} ({:.2f})'.format(mag0, mag0/total))

mag_valid = 0
mag_invalid = 0

with open('missing_links_unarXive_eval') as f:
    for line in f:
        if not re.search('^\d', line):
            # comments
            continue
        evl = line.strip().split(':')[-1].split('(')[0].strip()
        if len(evl) == 0:
            # not evalutated yet
            continue
        if evl[0] == 'y' or evl == 'n-':
            mag_valid += 1
        elif evl[0] == 'n' and not evl == 'n-':
            mag_invalid += 1
        elif evl[0] not in ['y', 'n']:
            print('problem with line: "{}"'.format(line))
            sys.exit()

mag_total = mag_valid + mag_invalid

print()
print('--- MAG only ---')
print()
print('total: {}'.format(mag_total))
print()
print('general indicator of quality of "not in unarXive" subset of links:')
print('  valid: {} ({:.2f})'.format(mag_valid, mag_valid/mag_total))
print('  invalid: {} ({:.2f})'.format(mag_invalid, mag_invalid/mag_total))
