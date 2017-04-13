import datetime
import re
import sys

# Two forms of specifying the format for timestamps. Ideally, we'd just
# use one, but the regex for is better for determining the length of
# the timestamp.
regex_timedate_formats = {
    "Generic 1": r'^(\d\d\.\d\d\.\d\d\d\d \d\d:\d\d:\d\d\.\d+)',
    "Android": r'^(\d\d-\d\d \d\d:\d\d:\d\d\.\d+)',
}

strptime_timedate_formats = {
    "Generic 1": '%d.%m.%Y %H:%M:%S.%f',
    "Android": '%m-%d %H:%M:%S.%f',
}

def strip_date(l, format_name = None):
    if format_name == None: return (None, l)
    g = re.match(regex_timedate_formats[format_name], l)
    if g:
        format = strptime_timedate_formats[format_name]
        datetime_object = datetime.datetime.strptime(g.group(1), format)
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

def detect_time_format(f):
    """ Read through the file and try to match all the date/time formats we know.
        The first one to match ten times wins; that's what we'll take as the time
        format for the whole log. The file pointer is rewound at the end. """
    scores = {}
    format = None
    for k in regex_timedate_formats.keys(): scores[k] = 0
    while True:
        l = f.readline()
        if l == "": break
        for k in regex_timedate_formats.keys():
            g = re.match(regex_timedate_formats[k], l)
            if g:
                scores[k] += 1
                if scores[k] >= 10:
                    format = k
        if format: break
    f.seek(0)
    return format

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
        timedate_format = detect_time_format(f)
        print("Time and date format detected as %s"%(timedate_format))
        while True:
            l = f.readline()
            if l == "": break
            l = l.strip()
            (date, l) = strip_date(l, timedate_format)
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
