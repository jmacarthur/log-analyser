# Proposal for a logfile analyser

At Codethink we're often called in to help with projects that are running late or have difficult bugs in. In a lot of cases, we don't have access to the source code for a system, at least in the early stages of a project.

In these cases we often have log files produced by the system under test, and this is the only information we have to diagnose faults and suggest cures for the development team.

    Input --> [ UNKNOWN SYSTEM ] --> Output and logs

Log files can be in any format. We attach directly to the serial port of a development board, so we get the usual output from the Linux kernel, and other proprietary messages. For example, this is an anonymised example from a recent project:

    07.04.2017 11:29:15.0414 <serial> [error] startAudio()@AudioPlaybackSystem.cpp(601) (AudioPlayer) : shmat failed. Error 8. shm is [/tmp/shm/audiosink]

This is in a proprietary format, but a developer would probably spot that this was a problem, particularly if accompanied by a bug report which said that the system rebooted unexpectedly at around 11:30am. The problem is that this message is in a log file which could have hundreds of thousands of other lines in it, none of which may be helpful.

If the 'shmat failed' message occurred every second, and there were no obvious problems with the system under test, you might well determine that this was not the most important problem. So, to speed up the process of diagnosing faults, what I really want is a process that can automatically pick out unusual messages and filter out ones that occur regularly. Logfile analysers already exist, but are all for the logs of known software, such as Linux or Apache.

It would also be useful to attempt to correlate messages and an event (usually an error) that happened at a particular time. Assuming we can extract a timestamp, and we have multiple instances of an event, we may be able to show that some messages correlate with the event within a certain window, say 0-60 seconds before the event. 

So, briefly, the requirements are:

* Highlight log lines which are unusual, and hide ones which occur regularly.
* Correlate messages with events at known times.

# Potential problems:

* Data from serial lines is occasionally corrupted by race conditions in people trying to write to it, so you end up with half of a log message from one process and another half from another process. We'd like to identify smaller sections of messages than whole lines.
* Some parts of log messages will change without making any difference to the meaning; for example, memory addresses.
* Finding training data to test the algorithm on may be difficult.

# Compression

One potential way to approach this is to run the data through a data compression algorithm and look for the compression ratio. Commonly occurring data should compress very well, so adding a common line to a compressed file should not increase its size by much; a distinct line should increase it by more.

# Example data

The projects this tool was envisaged for were confidential software projects, and as such I can't provide any substantial portions of logs for them. Instead, there is a section of logfile for an old version of Android running in an emulator, in which I've caused Launcher to crash three times and also included another event which is intended to signal the impending reset. The indicator of the crash is this line:

     04-12 17:37:17.233  1513  2319 E AndroidRuntime: *** FATAL EXCEPTION IN SYSTEM PROCESS: PowerManagerService.crash()

# Example results

This is the output from `make test` at the time of writing:

    $ python analyser.py android-log-example
    Time and date format detected as Android
    Crash events were detected at these times: 1900-04-12 17:53:51.590000, 1900-04-12 17:55:40.578000, 1900-04-12 18:00:54.990000
    Unusualness ranges from 0.013433 to 43.807267.
    Correlation ranges from 0.000000 to 6.130336.
    Reporting lines with correlation above 50.00% (3.07)
    [1.03/3.08] 2404 2404 E BadBehaviorActivity: Apps Behaving Badly
    [1.02/3.09] 1513 2426 E AndroidRuntime: java.lang.RuntimeException: Crashed by BadBehaviorActivity
    [1.02/3.07] 3619 3619 E BadBehaviorActivity: Apps Behaving Badly
    [1.02/3.09] 2629 3633 E AndroidRuntime: java.lang.RuntimeException: Crashed by BadBehaviorActivity
    [1.03/3.12] 2302 2302 E BadBehaviorActivity: Apps Behaving Badly
    [1.02/3.09] 1513 2316 E AndroidRuntime: java.lang.RuntimeException: Crashed by BadBehaviorActivity

The two numbers on the left are the 'unusualness' score, which is higher for more unusual log entries, and the correlation score, which is higher for entries which appear up to 20 seconds before a known crash. The 'Crashed by BadBehaviourActivity' line actually occurs after the line we've identified as a crash, so in a future version these should be filtered out. 'Apps Behaving Badly', however, is the actual problem we're looking for, so we've filtered the 13000-line log file into 6 entries to look into. Of course, in this example, I knew that message was the target and so may have set the display threshold accordingly. It's not a very good test yet. More example data is needed.