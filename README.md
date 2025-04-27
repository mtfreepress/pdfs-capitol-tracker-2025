# Capitol Tracker PDF to AWS
## pdfs-capitol-tracker-2025
A free standing repository designed to grab PDFs and deploy them to the web
Designed to run via GHA at regular intervals to ensure the [MTFP](https://montanafreepress.org/)'s [Capitol Tracker](https://github.com/mtfreepress/capitol-tracker-2025) remains up to date

# Purpose
1) To reduce load on our main `legislative-interface` and `capitol-tracker` deployments
2) Allow for incremental updates of PDFs so we aren't uploading 1GB+ to AWS every 20 minutes
3) Reduce the steps taken from: 
```
[grab pdfs & process]->[move to capitol tracker repo]->[next build]->[deploy all PDFs to aws every time]
```
down to 
```
[grab pdfs & process]->[deploy changed PDFs to aws]
```
which will speed up deployment from a best case scenario of around 25 minutes (and can be up to 45 minutes after a new PDF is uploaded before it shows up) to a worst case of less than 5. 

# How to run locally:
## Prerequisites: Amazon Web Servivces CLI, python3
1) Run `chmod +x ./setup.sh` to make the script executable. 
2) Run `./setup.sh` to set up a virtual environment, install dependencies, make other scripts executable etc. 
3) To run the project use `./fetch-and-compress.sh` which will grab PDFs from `legmt.gov` 
4) To deploy changes to AWS, run `./deploy.sh`
    