tron is multi threading sw running at multi CPU cores. Within each core, there are also multi threads. What if we change 
tron's threading model:
- each CPU core runs 1 tron thread, no change here
- each sw thread is truly single thread. It does not launch multi threads. 

The motivation of the change is to reduce the complexcity of thread concurrency, and reduce randomness of execution sequence.

Of course, the overall concurrency stays between threads running at different cores.

Please assess this idea.
