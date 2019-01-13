import datetime
import json
import pexpect
import re

FACT_PATT = re.compile(r'^(\d\.\d+)\s([^:]+:)?\((.+)\)$')


def get_claims(openie_proc, input_sentence):
    openie_proc.sendline(input_sentence)
    # FIXME
    openie_proc.expect(re.escape(input_sentence))  # hung here; investigate!
    more_output = True
    output = []
    min_reads = 2
    reads = 0
    while more_output:
        ret = openie_proc.readline()
        reads += 1
        if len(ret.strip()) > 0:
            output.append(ret.strip())
        elif reads > min_reads:
            more_output = False
    claims = []
    if len(output) > 0:
        for claim in output:
            m = FACT_PATT.match(claim)
            if not m:
                continue
            confidence = float(m.group(1))
            extra = m.group(2)
            claim_parts = [p.strip() for p in m.group(3).split(';')]
            s = None
            p = None
            o = None
            time = None
            location = None
            spo_idx = 0
            for cp in claim_parts:
                if re.search(r'^T:', cp):
                    time = re.sub(r'^T:', '', cp)
                elif re.search(r'^L:', cp):
                    location = re.sub(r'^L:', '', cp)
                else:
                    if spo_idx == 0:
                        s = cp
                    elif spo_idx == 1:
                        p = cp
                    elif spo_idx == 2:
                        o = cp
                    spo_idx += 1
            claim = {
                's': s,
                'p': p,
                'o': o,
                'time': time,
                'location': location,
                'confidence': confidence
                }
            claims.append(claim)
    return claims


test_input = []
with open('items.csv') as f:
    lines = f.readlines()
for line in lines:
    mid, adjacent, in_doc, text = line.split('\u241E')
    test_input.append(text)

print('starting OpenIE')
child = pexpect.spawnu(
    'java -jar openie-assembly.jar',
    cwd='/home/saiert/OpenIE-standalone',
    timeout=600)
print('waiting for OpenIE being ready')
child.expect(re.escape('* * * * * * * * * * * * *'))
child.expect(re.escape('* OpenIE 5.0 is ready *'))
child.expect(re.escape('* * * * * * * * * * * * *'))

claims_total = 0
openie_total_time = 0
all_claims = []
for idx, sentence in enumerate(test_input):
    # print('Input: {}'.format(sentence))
    t1 = datetime.datetime.now()
    claims = get_claims(child, sentence)
    all_claims.append(claims)
    claims_total += len(claims)
    t2 = datetime.datetime.now()
    d = t2 - t1
    if idx >= 1:
        openie_total_time += d.total_seconds()
    if idx%100 == 0 or idx == len(test_input)-1:
        print('avg #claims/context: {}'.format(claims_total/(idx+1)))
        print('avg time/context: {}s'.format(openie_total_time/idx))
    # print('Output: {}'.format(claims))
print('claims_total: {}'.format(claims_total))
print('openie_total_time: {}s'.format(openie_total_time))
with open('claims.json', 'w') as f:
    f.write(json.dumps(all_claims))
