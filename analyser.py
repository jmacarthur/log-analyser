#!/usr/bin/env python

import datetime
import re
import sys

"""This is a very experimental program which attempts to locate
interesting log lines in general log output. The only assumptions it
makes about the log output is that lines start with a timestamp, and
can be broken up into meaningful tokens separated by spaces. There are
two formats known for timestamps, and more can be added. At the
moment, the text indicating a crash is hardcoded.

"""

crash_text = ["FATAL EXCEPTION IN SYSTEM PROCESS"]

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

# Setings
""" report_correlation_threshold is the point at which lines are reported:
    If this is at 0.7, then lines with correlation at or above 70% of the
    range between minimum and maximum correlation are reported. """
report_correlation_threshold = 0.5

# Global variables
known_tokens = []
token_counts = {}
token_correlate_hit = {}
token_correlate_miss = {}


def strip_date(l, format_name=None):
    if format_name is None:
        return (None, l)
    g = re.match(regex_timedate_formats[format_name], l)
    if g:
        format = strptime_timedate_formats[format_name]
        datetime_object = datetime.datetime.strptime(g.group(1), format)
        return (datetime_object, l[len(g.group(1)):])
    else:
        return (None, l)


def lookup_tokens(token_list):
    global known_tokens
    token_numbers = []
    for t in token_list:
        if t not in known_tokens:
            known_tokens.append(t)
        token_numbers.append(known_tokens.index(t))
    return token_numbers


def vivify(key, val, list_of_dicts):
    for d in list_of_dicts:
        if key in d:
            return
        d[key] = val


def detect_time_format(f):
    """Read through the file and try to match all the date/time formats
        we know.  The first one to match ten times wins; that's what
        we'll take as the time format for the whole log. The file
        pointer is rewound at the end.

    """
    scores = {}
    format = None
    for k in regex_timedate_formats.keys():
        scores[k] = 0
    while True:
        l = f.readline()
        if l == "":
            break
        for k in regex_timedate_formats.keys():
            g = re.match(regex_timedate_formats[k], l)
            if g:
                scores[k] += 1
                if scores[k] >= 10:
                    format = k
        if format:
            break
    f.seek(0)
    return format


def is_crash_line(line, crash_labels):
    return any(c in line for c in crash_labels)


def find_crash_events(f, text_labels, timedate_format):
    """ Run through f and search for lines which contain one of the labels.
        Return a list of times when crashes are detected. """

    # If we have no timedate format, we can't determine when crashes happen.
    if timedate_format is None:
        return []

    crash_events = []
    while True:
        l = f.readline()
        if l == "":
            break
        l = l.strip()
        (date, l) = strip_date(l, timedate_format)
        if is_crash_line(l, text_labels):
            crash_events.append(date)
    f.seek(0)
    print("Crash events were detected at these times: " +
          ", ".join(map(str, crash_events)))
    return crash_events


def score_line(tokens):
    global token_counts, token_correlate_hit, token_correlate_miss
    score = 0
    line_correlation = 0
    for tn in tokens:
        score += 1.0/token_counts[tn]
        total_correlations = token_correlate_hit[tn]+token_correlate_miss[tn]
        if total_correlations > 0:
            correlation = (float(token_correlate_hit[tn]) / total_correlations)
        else:
            correlation = 0
        # Adding up ratios like this feels wrong, but it will do for now
        line_correlation += correlation
    return (score, line_correlation)


def update_token_stats(token, date, crash_events):
    global token_counts, token_correlate_hit, token_correlate_miss
    vivify(token, 0, [token_counts, token_correlate_miss, token_correlate_hit])
    token_counts[token] += 1
    if date:
        matches = (((c - date).total_seconds() < 20 and
                    ((c-date).total_seconds()>=0))
                   for c in crash_events)
        if any(matches):
            token_correlate_hit[token] += 1
        else:
            token_correlate_miss[token] +=1


def main():
    if len(sys.argv) < 2:
        print("Usage: analyser.py <logfile>")
        sys.exit(0)
    filename = sys.argv[1]
    lines_with_numbers = []
    
    with open(filename, "rt") as f:
        timedate_format = detect_time_format(f)
        print("Time and date format detected as %s"%(timedate_format))
        crash_events = find_crash_events(f, crash_text, timedate_format)
        while True:
            l = f.readline()
            if l == "":
                break
            l = l.strip()
            (date, l) = strip_date(l, timedate_format)
            tokens = l.split(" ")
            while '' in tokens:
                tokens.remove('')
            token_numbers = lookup_tokens(tokens)
            lines_with_numbers.append(token_numbers)
            for tn in token_numbers:
                update_token_stats(tn, date, crash_events)

    most_unusual = 0
    least_unusual = 999
    max_correlation = 0
    min_correlation = 999

    for line in lines_with_numbers:
        (score, line_correlation) = score_line(line)
        if score > most_unusual: most_unusual = score
        if score < least_unusual: least_unusual = score
        if line_correlation > max_correlation: max_correlation = line_correlation
        if line_correlation < min_correlation: min_correlation = line_correlation
        
    print("Unusualness ranges from %f to %f."%(least_unusual, most_unusual))
    print("Correlation ranges from %f to %f."%(min_correlation, max_correlation))
    absolute_correlation_threshold = ((1-report_correlation_threshold)*min_correlation +
                                      report_correlation_threshold*max_correlation)

    print("Reporting lines with correlation above %2.2f%% (%2.2f)" %
          (report_correlation_threshold*100, absolute_correlation_threshold))
    for line in lines_with_numbers:
        (score, line_correlation) = score_line(line)
        original_line = " ".join(known_tokens[x] for x in line)
        if (line_correlation > absolute_correlation_threshold
            and not is_crash_line(original_line, crash_text)):
            print("[%2.2f/%2.2f] %s"%(score, line_correlation, original_line))

if __name__=="__main__": main()
