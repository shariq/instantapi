# Instant API

Instant API lets you create an API from a website instantly! You install a Chrome extension, and use that to record a Selenium script. While recording the script, you have the ability to add parameters which change how the script behaves (and added as a param to the API route), and the ability to add selectors which parse the final page visited by your script (and included as part of the result you get back from the route).

API routes take in some params which get passed to the script.

API routes return the final page source, 

A pool of Selenium instances on DigitalOcean droplets handles all requests. This can currently support up to ~500 concurrent droplets.

Download the Chrome extension here: <link>
