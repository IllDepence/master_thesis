import pexpect
import re

FACT_PATT = re.compile(r'^(\d\.\d+)\s([^:]+:)?\((.+)\)$')


def get_claims(openie_proc, input_sentence):
    openie_proc.sendline(input_sentence)
    openie_proc.expect(re.escape(input_sentence))
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
test_input.append(
    'The Web is huge, diverse, and dynamic and thus raises the scalability, mu'
    'ltimedia data, and temporal issues respectively. Due to those situations,'
    ' we are currently drowning in information and facing information overload'
    '.'
    )
test_input.append(
    'There is a close relationship between data mining, machine learning and a'
    'dvanced data analysis.'
    )
test_input.append(
    'Recent research focuses on utilizing the Web as a knowledge base for deci'
    'sion making.'
    )

print('starting')
child = pexpect.spawnu(
    'java -jar openie-assembly.jar',
    cwd='/home/saiert/OpenIE-standalone',
    timeout=600)
print('waiting for OpenIE being ready')
child.expect(re.escape('* * * * * * * * * * * * *'))
child.expect(re.escape('* OpenIE 5.0 is ready *'))
child.expect(re.escape('* * * * * * * * * * * * *'))

for sentence in test_input:
    print('Input: {}'.format(sentence))
    claims = get_claims(child, sentence)
    print('Output: {}'.format(claims))
