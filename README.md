# El-Console
A simple terminal/console system that tracks and displays electricity prices in real time (specifically in sweden).

# Overview

I implemented this mainly for myself to monitor electricity prices where I live since I never really had a good overview of the current price in my region. I believe having some real-time awareness of price and consumption may affect my consumer behavious in a good way (or at least that is the hope! ).


# TODO upgrades

- Absolute thresholds are arbitrary and not necessarily meaningful. I have not done any statistical analysis of the regional electricity pricing distribution, which would give more accurate tags for the thresholds of what is considered "CHEAP", "EXPENSIVE" and such... 
    - z-score based rule could be good
    - percentile-based check would also be an improvement