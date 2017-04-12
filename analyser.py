import datetime
import re
import sys

def strip_date(l):
    g = re.match("^(\d\d\.\d\d\.\d\d\d\d \d\d:\d\d:\d\d\.\d+)",l)
    if g:
        datetime_object = datetime.datetime.strptime(g.group(1), '%d.%m.%Y %H:%M:%S.%f')
        
        return (datetime_object, l[len(g.group(1)):])
    else:
        return (None, l)

known_tokens = []
def lookup_tokens(token_list):
    global known_tokens
    token_numbers = []
    for t in token_list:
        if t not in known_tokens: known_tokens.append(t)
        token_numbers.append(known_tokens.index(t))
    return token_numbers

def vivify(key, val, list_of_dicts):
    for d in list_of_dicts:
        if key in d: return
        d[key] = val

def main():
    if len(sys.argv)<2:
        print("Usage: analyser.py <logfile>")
        sys.exit(0)
    filename = sys.argv[1]
    token_counts = {}
    token_correlate_hit = {}
    token_correlate_miss = {}
    lines_with_numbers = []
    crash_events = [ datetime.datetime(2017, 2, 23, 12,11,43, 623300) ]
    
    with open(filename, "rt") as f:
        while True:
            l = f.readline()
            if l == "": break
            l = l.strip()
            (date, l) = strip_date(l)
            tokens = l.split(" ")
            while '' in tokens:
                tokens.remove('')
            token_numbers = lookup_tokens(tokens)
            #print("Tokenized line: %r"%token_numbers)
            lines_with_numbers.append(token_numbers)
            for tn in token_numbers:
                vivify(tn, 0, [token_counts, token_correlate_miss, token_correlate_hit])
                token_counts[tn] += 1
                if date:
                    matches = (((c - date).total_seconds() < 10 and ((c-date).total_seconds()>=0)) for c in crash_events)
                    if any(matches):
                        token_correlate_hit[tn] += 1
                    else:
                        token_correlate_miss[tn] +=1

    most_unusual = 0
    least_unusual = 999
    for line in lines_with_numbers:
        score = 0
        for tn in line:
            score += 1.0/token_counts[tn]
        if score > most_unusual: most_unusual = score
        if score < least_unusual: least_unusual = score
        correlation = None
        total_correlations = token_correlate_hit[tn]+token_correlate_miss[tn]
        if total_correlations > 0:
            print("Unusualness of line: %f. Correlation with crash: %f"%(score, token_correlate_hit[tn] / total_correlations))
        else:
            print("Unusualness of line: %f."%score)
    print("Unusualness ranges from %f to %f."%(least_unusual, most_unusual))
        
if __name__=="__main__": main()
