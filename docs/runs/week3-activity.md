# Week3 activity questions
## Q1
- **what's lost if the process restarts?** (i.e., what is the `request_counts` dict missing that a real metrics system would provide?)
- In one sentence: under heavy concurrency, would two simultaneous requests to `/health` always result in the counter going from N to N+2? Why or why not?
- **Answer:** request_counts is runtime global variable - thus when process restarts it will be reinitiate to ZERO "0". Simultaneous requests `/health` might not result in counter to increment as it is an async call and the value is not stored & retrived, thus it would override part of the session
- `from GPT: refer to it specifically as a race condition or lost update. The issue isn't that values aren't being stored and retrieved, but rather that two threads/tasks perform the read-modify-write cycle at the exact same time without locking or atomic operations.`