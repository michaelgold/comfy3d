import sys

def print_progress_bar(job_title, progress, length, start_percent=0, end_percent=100):
    if length != 0:        
        progress = int((progress * 100) / length)
    else:
        progress = 100
    # optional remap
    progress = start_percent + progress/(100 / (end_percent-start_percent))
    
    sys.stdout.write("\r  " + job_title + " %d%%" % progress)
    try:# unknown compatibility breakage with flush() in a rare case reported by a user
        sys.stdout.flush()
    except: pass